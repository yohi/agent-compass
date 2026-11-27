"""Owner-selected proposal adoption; update the same draft PR, never master or merge."""
import base64
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit

import compass
import generator
import maintenance

ROOT = Path(__file__).resolve().parent
REPO = maintenance.REPO
MAX_PROPOSAL = 40000
MAX_DECISIONS = 20000
ACTIVE = generator.ACTIVE
RETIRE = {"deprecate": "deprecated", "supersede": "superseded"}
FIELDS = {"schema_version", "adoption_status", "base_commit", "chunk_cursor", "identity",
          "model", "origin", "partial_source", "prior_source_text", "proposals",
          "snapshot_identity", "source_id", "source_sha256", "source_url"}
DATA_PATHS = ("registry/sources.json", "registry/practices.json", "registry/generation.json",
              "registry/audit.json", "docs/BEST_PRACTICES.md")


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(value):
    return isinstance(value, str) and bool(maintenance.SHA.fullmatch(value))


def commit_sha(value):
    return isinstance(value, str) and bool(maintenance.COMMIT.fullmatch(value))


def encode(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def parse_json(raw, limit):
    require(isinstance(raw, (str, bytes)) and len(raw if isinstance(raw, bytes) else raw.encode()) <= limit,
            "input_size")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique)


def proposal_path(report):
    require(isinstance(report, dict) and set(report) == FIELDS, "proposal_shape")
    sid, identity = report["source_id"], report["identity"]
    require(isinstance(sid, str) and compass.ID.fullmatch(sid) and sha(identity), "proposal_identity")
    return f"proposals/{sid}/{identity}.json"


def validate_report(report, source, practices, content):
    """Verify exact normalized source and stored quote locator, not semantic entailment."""
    proposal_path(report)
    require(report["schema_version"] == 1 and report["adoption_status"] == "UNADOPTED"
            and report["prior_source_text"] == "NOT_AVAILABLE" and report["origin"] in {"initial", "changed"}
            and type(report["partial_source"]) is bool and report["model"] in maintenance.CAPS
            and commit_sha(report["base_commit"]), "proposal_metadata")
    require(source["id"] == report["source_id"] and source["url"] == report["source_url"],
            "source_registration_changed")
    require(sha(report["source_sha256"]) and compass.digest(content) == report["source_sha256"],
            "source_snapshot_changed")
    expected = maintenance.identity(source, report["source_sha256"])
    cursor = report["chunk_cursor"]
    require(type(cursor) is int and 0 <= cursor < len(content)
            and report["snapshot_identity"] == expected, "source_identity")
    row = {"identity": expected, "fingerprint": report["source_sha256"],
           "cursor": cursor, "origin": report["origin"]}
    require(report["identity"] == maintenance.chunk_identity(row), "chunk_identity")
    items = report["proposals"]
    require(isinstance(items, list) and 1 <= len(items) <= 3, "proposal_count")
    raw_items = []
    excerpt = content[cursor:]
    for item in items:
        require(isinstance(item, dict) and set(item) == {"action", "practice_id", "proposed",
                "existing_record_sha256", "evidence_locator"}, "proposal_item")
        p = item["proposed"]
        loc = item["evidence_locator"]
        require(isinstance(p, dict) and set(p) == {"target", "category", "status", "en", "ja", "scope",
                "reason", "evidence", "local_eval"}, "proposal_fields")
        require(isinstance(loc, dict) and set(loc) == {"chunk_normalized_line", "chunk_char_offset",
                "quote_length", "quote_sha256"}, "evidence_locator")
        start, length = loc["chunk_char_offset"], loc["quote_length"]
        require(type(start) is int and type(length) is int and 0 <= start
                and 8 <= length <= 150 and start + length <= len(excerpt), "evidence_bounds")
        quote = excerpt[start:start+length]
        require(sha(loc["quote_sha256"]) and compass.digest(quote) == loc["quote_sha256"]
                and type(loc["chunk_normalized_line"]) is int
                and loc["chunk_normalized_line"] == excerpt[:start].count("\n") + 1,
                "evidence_mismatch")
        raw_items.append({"action": item["action"], "practice_id": item["practice_id"],
                          **{k: p[k] for k in ("target", "category", "status", "en", "ja", "scope", "reason")},
                          "evidence_quote": quote})
    # Reuse the same strict proposal validator, including exact current-record digest.
    # A stale amended record requires a fresh proposal; never overwrite a concurrent edit.
    checked = maintenance.validate_proposals({"proposals": raw_items}, source, row, practices,
                    excerpt, maintenance.config(), report["model"], report["partial_source"])
    require(checked["proposals"] == items, "proposal_or_existing_record_changed")
    return items


def decisions(raw, count):
    value = parse_json(raw, MAX_DECISIONS)
    require(isinstance(value, list) and 1 <= len(value) <= count, "decision_count")
    seen = set()
    for d in value:
        require(isinstance(d, dict) and {"index", "status", "placement"} <= set(d)
                and set(d) <= {"index", "status", "placement", "configuration_kind", "instruction"},
                "decision_shape")
        i = d["index"]
        require(type(i) is int and 1 <= i <= count and i not in seen, "decision_index")
        seen.add(i)
        require(isinstance(d["status"], str) and d["status"] in compass.STATUSES, "decision_status")
        place = d["placement"]
        require(isinstance(place, str) and place in generator.PLACEMENTS | {"none"}, "decision_placement")
        require((d["status"] in ACTIVE and place != "none") or
                (d["status"] not in ACTIVE and place == "none"), "status_placement_mismatch")
        if place == "configuration":
            require(set(d) == {"index", "status", "placement", "configuration_kind"}
                    and d["configuration_kind"] in {"api-or-runtime", "permissions", "integration"},
                    "configuration_kind")
        elif place == "instruction":
            ins = d.get("instruction")
            require(set(d) == {"index", "status", "placement", "instruction"}
                    and isinstance(ins, dict) and set(ins) == {"en", "ja"}
                    and all(isinstance(v, str) and 0 < len(v.strip()) <= 1200
                            and "\n" not in v and "\r" not in v and "\x00" not in v
                            for v in ins.values()), "owner_instruction")
        else:
            require(set(d) == {"index", "status", "placement"}, "unexpected_decision_field")
    return sorted(value, key=lambda x: x["index"])


def plan(report, selected, sources, targets, practices, generation, audit, content, reviewed):
    """Pure, deterministic transformation. No changes to input structures."""
    require(re.fullmatch(r"\d{4}-\d{2}-\d{2}", reviewed), "review_date")
    require(report["source_id"] in sources, "unknown_source")
    source = sources[report["source_id"]]
    items = validate_report(report, source, practices, content)
    selected = decisions(encode(selected), len(items))
    s, p, g, a = copy.deepcopy((sources, practices, generation, audit))
    next_id = max((int(k[3:]) for k in p), default=0) + 1
    assigned = []
    touched = set()
    for d in selected:
        item = items[d["index"] - 1]
        action, proposed = item["action"], item["proposed"]
        if action in RETIRE:
            require(d["status"] == RETIRE[action], "retirement_status_required")
        else:
            require(d["status"] not in RETIRE.values(), "retirement_action_required")
        if action == "add":
            pid = f"BP-{next_id:03d}"
            next_id += 1
            require(not any(old["target"] == proposed["target"] and
                            (old["en"] == proposed["en"] or old["ja"] == proposed["ja"])
                            for old in p.values()), "duplicate_practice_text")
        else:
            pid = item["practice_id"]
        require(pid not in touched and proposed["target"] in targets, "duplicate_or_unknown_target")
        touched.add(pid)
        # Retirement preserves the original guidance and evidence; the reason/locator of
        # retirement remains in the immutable proposal and adoption receipt.
        if action in RETIRE:
            new = {**p[pid], "status": d["status"], "reviewed": reviewed}
        else:
            new = {"id": pid, **{k: proposed[k] for k in ("target", "category", "en", "ja", "scope", "evidence")},
                   "status": d["status"], "local_eval": "not_verified", "reviewed": reviewed}
        # Any changed text has no inherited local evaluation. Retirement is excluded by status.
        p[pid] = new
        g["placements"] = [r for r in g["placements"] if r["id"] != pid]
        if d["placement"] != "none":
            placement = {"id": pid, "placement": d["placement"]}
            if d["placement"] == "configuration":
                placement["configuration_kind"] = d["configuration_kind"]
            elif d["placement"] == "instruction":
                require(new["category"] not in {"reasoning", "tools", "integration", "migration"},
                        "runtime_as_instruction")
                placement["instruction"] = d["instruction"]
            g["placements"].append(placement)
        # Detach outdated lexical-auditor evidence on changed records, never infer a new mapping.
        detached = []
        if action != "add":
            for rule in a["rules"]:
                if pid in rule["evidence"]:
                    rule["evidence"] = [v for v in rule["evidence"] if v != pid]
                    detached.append(rule["id"])
        assigned.append({"index": d["index"], "action": action, "practice_id": pid,
                         "status": new["status"], "placement": d["placement"],
                         "detached_audit_rules": detached})
    s[source["id"]]["checked"] = reviewed
    receipt = {"schema_version": 1, "state": "OWNER_SELECTED_PENDING_MERGE",
               "source_id": source["id"], "source_sha256": report["source_sha256"],
               "proposal_identity": report["identity"], "source_checked": reviewed,
               "selected": assigned, "decisions": selected,
               "unselected": sorted(set(range(1, len(items) + 1)) - {d["index"] for d in selected}),
               "semantic_evidence": "OWNER_REVIEW_DECLARED",
               "literal_source_locator": "VERIFIED"}
    files = {"registry/sources.json": encode(list(s.values())),
             "registry/practices.json": encode(list(p.values())),
             "registry/generation.json": encode(g),
             "registry/audit.json": encode(a),
             "docs/BEST_PRACTICES.md": compass.render(s, targets, p)}
    return files, receipt


def gh(*args, payload=None):
    return compass.gh(*args, payload=payload)


def get_pr(endpoint, number, head):
    require(type(number) is int and number > 0 and commit_sha(head), "pr_identity")
    pr = gh(f"{endpoint}/pulls/{number}")
    require(pr["state"] == "open" and pr["draft"] is True and pr["head"]["sha"] == head
            and pr["head"]["repo"]["full_name"] == REPO and pr["base"]["repo"]["full_name"] == REPO
            and pr["base"]["ref"] == "master", "pr_head_or_scope_changed")
    return pr


def current_ref(endpoint, branch):
    return gh(f"{endpoint}/git/ref/heads/{branch}")["object"]["sha"]


def get_candidate(endpoint, number, head, pr):
    pages = gh("--paginate", "--slurp", f"{endpoint}/pulls/{number}/files?per_page=100")
    files = [r for page in pages for r in page]
    require(len(files) == 1 and files[0]["status"] == "added", "not_candidate_only_pr")
    path = files[0]["filename"]
    require(isinstance(path, str) and re.fullmatch(r"proposals/[a-z0-9][a-z0-9.-]{0,79}/[0-9a-f]{64}\.json",
                                                path), "candidate_path")
    entry = gh(f"{endpoint}/contents/{path}?ref={head}")
    require(entry["type"] == "file" and entry["encoding"] == "base64"
            and entry["sha"] == files[0]["sha"] and type(entry["size"]) is int
            and 0 < entry["size"] <= MAX_PROPOSAL, "candidate_blob")
    raw = base64.b64decode("".join(entry["content"].split()), validate=True)
    require(len(raw) == entry["size"], "candidate_size")
    report = parse_json(raw, MAX_PROPOSAL)
    require(proposal_path(report) == path
            and pr["head"]["ref"] == "compass-proposals/" + report["identity"]
            and commit_sha(report["base_commit"]), "candidate_branch")
    # The generated candidate commit has exactly one parent, the declared trusted base.
    obj = gh(f"{endpoint}/git/commits/{head}")
    require([p["sha"] for p in obj["parents"]] == [report["base_commit"]], "candidate_parent")
    comparison = gh(f"{endpoint}/compare/{report['base_commit']}...{head}")
    require(comparison["ahead_by"] == 1 and comparison["behind_by"] == 0
            and len(comparison["files"]) == 1 and comparison["files"][0]["filename"] == path
            and comparison["files"][0]["status"] == "added"
            and comparison["files"][0]["sha"] == entry["sha"], "candidate_commit_scope")
    return report, path, raw.decode("utf-8")


def validate_build(files):
    """Only in the disposable, trusted master checkout of the owner workflow."""
    require(set(files) == set(DATA_PATHS), "write_scope")
    for path, content in files.items():
        (ROOT / path).write_text(content, encoding="utf-8")
    for args in (["compass.py", "validate"], ["compass.py", "render", "--check"],
                 ["-m", "unittest", "discover", "-s", "tests", "-v"]):
        subprocess.run([sys.executable, *args], cwd=ROOT, check=True, timeout=180)
    subprocess.run(["node", "--check", "web/app.js"], cwd=ROOT, check=True, timeout=60)
    subprocess.run(["node", "--test", "tests/test_web.cjs"], cwd=ROOT, check=True, timeout=60)


def run(repo, master, number, head, raw_decisions, owner, actor, triggering_actor, reviewed):
    require(repo == REPO and owner == "yohi" and actor == owner and triggering_actor == owner,
            "owner_authorization")
    require(reviewed is True and commit_sha(master), "explicit_evidence_review_required")
    endpoint = f"repos/{repo}"
    require(current_ref(endpoint, "master") == master, "master_changed")
    pr = get_pr(endpoint, number, head)
    report, path, raw = get_candidate(endpoint, number, head, pr)
    selected = decisions(raw_decisions, len(report["proposals"]))
    sources, targets, practices = compass.load_registry()
    g = generator.load_generation(targets, practices)
    a = compass.read_json(ROOT / "registry/audit.json")
    source = sources.get(report["source_id"])
    require(source is not None and source["url"] == report["source_url"], "source_registration_changed")
    body, fmt, _ = compass.fetch_document(source, {urlsplit(source["url"]).hostname})
    content = compass.normalize(body, fmt)
    files, receipt = plan(report, selected, sources, targets, practices, g, a, content,
                          datetime.now(timezone.utc).date().isoformat())
    receipt.update(pr=number, approved_head=head, master_base=master, actor=actor,
                   proposal_file_sha256=compass.digest(raw))
    receipt_path = f"adoptions/{report['identity']}.json"
    require(not (ROOT / receipt_path).exists() and not (ROOT / path).exists(), "already_adopted_or_merged")
    changed = {k: v for k, v in files.items() if (ROOT / k).read_text(encoding="utf-8") != v}
    require("registry/practices.json" in changed, "no_registry_change")
    validate_build(files)
    # A fresh exact-head check before any Git writes. No force push, no master update.
    require(current_ref(endpoint, "master") == master, "master_changed_during_validation")
    pr = get_pr(endpoint, number, head)
    branch = pr["head"]["ref"]
    require(branch == "compass-proposals/" + report["identity"], "candidate_branch")
    require(current_ref(endpoint, branch) == head, "candidate_ref_changed")
    tree = gh(f"{endpoint}/git/commits/{master}")["tree"]["sha"]
    additions = {**changed, path: raw, receipt_path: encode(receipt)}
    result = gh("--method", "POST", f"{endpoint}/git/trees", payload={"base_tree": tree, "tree": [
        {"path": k, "mode": "100644", "type": "blob", "content": v} for k, v in sorted(additions.items())]})
    new = gh("--method", "POST", f"{endpoint}/git/commits", payload={
        "message": f"Prepare owner-selected knowledge adoption for PR #{number}",
        "tree": result["sha"], "parents": [head, master]})
    require(current_ref(endpoint, "master") == master and current_ref(endpoint, branch) == head,
            "ref_changed_before_update")
    gh("--method", "PATCH", f"{endpoint}/git/refs/heads/{branch}",
       payload={"sha": new["sha"], "force": False})
    require(current_ref(endpoint, branch) == new["sha"], "ref_readback_failed")
    print("ADOPTION_PREPARED_PENDING_MERGE", number, new["sha"])
    print("Selected:", json.dumps(receipt["selected"], ensure_ascii=True))
    return 0


def main():
    # Workflow inputs are environment data, never interpolated in shell commands.
    number = os.environ.get("ADOPTION_PR", "")
    require(bool(re.fullmatch(r"[1-9][0-9]{0,9}", number)), "pr_number")
    return run(os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_SHA"),
               int(number), os.environ.get("ADOPTION_HEAD", ""),
               os.environ.get("ADOPTION_DECISIONS", ""), os.environ.get("REPOSITORY_OWNER"),
               os.environ.get("GITHUB_ACTOR"), os.environ.get("TRIGGERING_ACTOR"),
               os.environ.get("EVIDENCE_REVIEWED") == "true")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, TypeError, IndexError, OSError, subprocess.SubprocessError) as exc:
        # Only fixed local reason strings; never log external payloads, quotes, or GitHub stderr.
        code = str(exc) if type(exc) is ValueError and re.fullmatch(r"[a-z_]{1,80}", str(exc)) else maintenance.diagnostic(exc)
        print("ADOPTION_BLOCKED:", code, file=sys.stderr)
        sys.exit(1)
