"""Owner-selected discovery registration; no automatic adoption or new model API calls."""
import base64
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlencode, urlsplit

import adoption
import compass
import discovery
import maintenance

ROOT = Path(__file__).resolve().parent
REPO = maintenance.REPO
LIFECYCLE = {"unknown", "preview", "generally-available", "deprecated", "retired"}
KINDS = {"official-docs", "official-guide", "official-index", "upstream-model-card",
         "upstream-release", "upstream-docs", "official-blog"}
PATHS = {"registry/targets.json", "registry/sources.json", "docs/BEST_PRACTICES.md"}
FIELDS = {"index", "candidate_kind", "candidate_value", "target_id", "target_name",
          "source_id", "source_url", "source_kind", "source_format", "lifecycle", "evidence_quote"}


def require(ok, code):
    if not ok:
        raise ValueError(code)


def literal_model(content, model):
    return bool(re.search(r"(?<![A-Za-z0-9_.-])" + re.escape(model)
                          + r"(?![A-Za-z0-9_.-])", content, re.IGNORECASE))


def plain(value, limit):
    return (isinstance(value, str) and value == value.strip() and 0 < len(value) <= limit
            and all(ord(c) >= 32 and c not in "<>" for c in value))


def parse_request(raw):
    d = adoption.parse_json(raw, 12000)
    require(isinstance(d, dict) and set(d) == FIELDS, "registration_fields")
    require(all(isinstance(v, str) for v in d.values()), "registration_types")
    for k in ("index", "target_id", "source_id"):
        require(bool(compass.ID.fullmatch(d[k])), "registration_id")
    require(d["candidate_kind"] in {"link", "model-mention"}, "candidate_kind")
    require(plain(d["candidate_value"], 512) and plain(d["source_url"], 512)
            and plain(d["target_name"], 120), "registration_text")
    require(d["source_kind"] in KINDS and d["source_format"] in {"html", "text"}
            and d["lifecycle"] in LIFECYCLE, "registration_metadata")
    require(plain(d["evidence_quote"], 150) and len(d["evidence_quote"]) >= 8
            and len(d["evidence_quote"].split()) <= 20, "evidence_quote_bounds")
    return d


def scope_request(d, index, targets, candidates):
    require(d["index"] == index["id"], "unknown_index")
    ident = discovery.identity(d["candidate_kind"], d["candidate_value"])
    require(candidates.get(ident) == (d["candidate_kind"], d["candidate_value"]),
            "candidate_not_currently_observed")
    existing = targets.get(d["target_id"])
    if d["candidate_kind"] == "model-mention":
        require(d["target_id"] == d["candidate_value"] and bool(compass.ID.fullmatch(d["target_id"]))
                and any(d["target_id"].startswith(p) for p in index["model_prefixes"]),
                "model_identity")
        require(existing is None or (existing["kind"] == "model" and existing["name"] == d["target_name"]),
                "target_conflict")
        require(d["source_url"] == index["url"] or
                candidates.get(discovery.identity("link", d["source_url"])) == ("link", d["source_url"]),
                "source_not_observed")
    else:
        require(d["source_url"] == d["candidate_value"] and existing is not None
                and existing["name"] == d["target_name"], "link_target_scope")
        require(d["target_id"] == index["target"] or
                (existing["kind"] == "model" and
                 any(d["target_id"].startswith(p) for p in index["model_prefixes"])),
                "link_target_scope")
    is_model = existing is None or existing["kind"] == "model"
    require(is_model or d["lifecycle"] == "unknown", "non_model_lifecycle")
    compass.safe_url(d["source_url"], {urlsplit(index["url"]).hostname})
    return ident, is_model


def plan(d, index, candidates, content, sources, targets, practices, checked):
    ident, is_model = scope_request(d, index, targets, candidates)
    quote = d["evidence_quote"]
    require(quote in content, "evidence_quote_not_found")
    if is_model:
        require(literal_model(content, d["target_id"]), "model_not_in_source")
        if d["lifecycle"] != "unknown":
            require(literal_model(quote, d["target_id"]), "lifecycle_quote_model_missing")
    s, t = copy.deepcopy((sources, targets))
    source = {"id": d["source_id"], "publisher": index["publisher"], "url": d["source_url"],
              "target": d["target_id"], "kind": d["source_kind"], "checked": checked,
              "format": d["source_format"]}
    previous = s.get(source["id"])
    if previous:
        require({k: v for k, v in previous.items() if k != "checked"} ==
                {k: v for k, v in source.items() if k != "checked"}, "source_id_conflict")
    require(not any(v["id"] != source["id"] and v["url"].rstrip("/") == source["url"].rstrip("/")
                    and v["target"] == source["target"] for v in s.values()), "duplicate_scoped_source")
    s[source["id"]] = source
    target = t.get(d["target_id"])
    if target is None:
        target = {"id": d["target_id"], "kind": "model", "name": d["target_name"]}
        t[target["id"]] = target
    offset = content.index(quote)
    evidence = {"source_id": source["id"], "source_sha256": compass.digest(content),
                "quote_sha256": compass.digest(quote), "quote_length": len(quote),
                "char_offset": offset, "normalized_line": content[:offset].count("\n") + 1}
    if is_model and (d["lifecycle"] != "unknown" or not target.get("lifecycle")):
        target["lifecycle"] = {"status": d["lifecycle"], "checked": checked, **evidence}
    request = {k: v for k, v in d.items() if k != "evidence_quote"}
    identity = compass.digest(json.dumps([request, evidence], sort_keys=True, ensure_ascii=False))
    receipt = {"schema_version": 1, "state": "OWNER_SELECTED_PENDING_MERGE",
               "identity": identity, "index_id": index["id"], "index_url": index["url"],
               "candidate_id": ident, "candidate_kind": d["candidate_kind"],
               "candidate_value": d["candidate_value"], "source": source,
               "target": target, "evidence": evidence, "semantic_evidence": "OWNER_REVIEW_DECLARED",
               "literal_evidence": "VERIFIED", "practice_extraction": "AFTER_MERGE_EXISTING_MAINTENANCE"}
    return {"registry/sources.json": adoption.encode(list(s.values())),
            "registry/targets.json": adoption.encode(list(t.values())),
            "docs/BEST_PRACTICES.md": compass.render(s, t, practices)}, receipt


def fetch_current(index, d, targets):
    host = urlsplit(index["url"]).hostname
    raw, fmt, final = compass.fetch_document(index, {host})
    candidates = discovery.extract(raw, fmt, final, index, set())
    scope_request(d, index, targets, candidates)
    source = {"url": d["source_url"], "format": d["source_format"]}
    if source["url"] == index["url"]:
        require(source["format"] == index["format"], "index_format")
    else:
        raw, fmt, final = compass.fetch_document(source, {host})
        require(discovery.candidate_url(final, index["url"], index) == d["source_url"],
                "source_redirect_outside_candidate")
    return candidates, compass.normalize(raw, fmt)


def validate_build(files):
    require(set(files) == PATHS, "write_scope")
    for path, content in files.items():
        (ROOT / path).write_text(content, encoding="utf-8")
    for args in (["compass.py", "validate"], ["compass.py", "render", "--check"],
                 ["-m", "unittest", "discover", "-s", "tests", "-v"]):
        subprocess.run([sys.executable, *args], cwd=ROOT, check=True, timeout=180)
    subprocess.run(["node", "--test", "tests/test_web.cjs"], cwd=ROOT, check=True, timeout=60)


def publish(endpoint, master, files, receipt):
    ident = receipt["identity"]
    require(maintenance.SHA.fullmatch(ident) and set(files) <= PATHS, "publish_scope")
    branch = "compass-discovery/" + ident
    path = "registrations/" + ident + ".json"
    query = urlencode({"state": "all", "head": "yohi:" + branch, "base": "master"})
    prs = compass.gh(f"{endpoint}/pulls?{query}")
    require(len(prs) <= 1, "ambiguous_registration_pr")
    if prs:
        print("REGISTRATION_ALREADY_PROPOSED", prs[0]["number"])
        return prs[0]["number"]
    require(adoption.current_ref(endpoint, "master") == master, "master_changed")
    additions = {**files, path: adoption.encode(receipt)}
    ref = maintenance.gh_optional(f"{endpoint}/git/ref/heads/{branch}")
    if ref:
        head = ref["object"]["sha"]
        obj = compass.gh(f"{endpoint}/git/commits/{head}")
        require([x["sha"] for x in obj["parents"]] == [master], "registration_branch_changed")
        diff = compass.gh(f"{endpoint}/compare/{master}...{head}")
        require(diff["ahead_by"] == 1 and diff["behind_by"] == 0
                and {r["filename"] for r in diff["files"]} == set(additions), "registration_branch_scope")
        for key, content in additions.items():
            entry = compass.gh(f"{endpoint}/contents/{key}?ref={head}")
            require(entry["encoding"] == "base64" and base64.b64decode(entry["content"]) == content.encode(),
                    "registration_branch_content")
    else:
        tree = compass.gh(f"{endpoint}/git/commits/{master}")["tree"]["sha"]
        new_tree = compass.gh("--method", "POST", f"{endpoint}/git/trees", payload={
            "base_tree": tree, "tree": [{"path": k, "mode": "100644", "type": "blob", "content": v}
                                      for k, v in sorted(additions.items())]})
        commit = compass.gh("--method", "POST", f"{endpoint}/git/commits", payload={
            "message": "Prepare owner-selected discovery registration",
            "tree": new_tree["sha"], "parents": [master]})
        require(adoption.current_ref(endpoint, "master") == master, "master_changed")
        compass.gh("--method", "POST", f"{endpoint}/git/refs",
                   payload={"ref": "refs/heads/" + branch, "sha": commit["sha"]})
    require(adoption.current_ref(endpoint, "master") == master, "master_changed")
    pr = compass.gh("--method", "POST", f"{endpoint}/pulls", payload={
        "title": "Register discovered source: " + receipt["source"]["id"],
        "head": branch, "base": "master", "draft": True,
        "body": "Owner-selected source/target registration; literal evidence verified. "
                "Lifecycle is owner-reviewed, not inferred by a model. No practices adopted. "
                "After manual merge, existing monitoring and maintenance process the source. Receipt: " + path})
    print("REGISTRATION_PREPARED_PENDING_MERGE", pr["number"])
    return pr["number"]


def run(repo, master, raw, owner, actor, trigger, reviewed):
    require(repo == REPO and owner == actor == trigger == "yohi" and reviewed is True
            and adoption.commit_sha(master), "owner_authorization")
    endpoint = f"repos/{repo}"
    require(adoption.current_ref(endpoint, "master") == master, "master_changed")
    d = parse_request(raw)
    sources, targets, practices = compass.load_registry()
    indexes = discovery.load_indexes(targets)
    require(d["index"] in indexes, "unknown_index")
    index = indexes[d["index"]]
    candidates, content = fetch_current(index, d, targets)
    files, receipt = plan(d, index, candidates, content, sources, targets, practices,
                          datetime.now(timezone.utc).date().isoformat())
    receipt.update(actor=actor, master_base=master)
    changed = {k: v for k, v in files.items() if (ROOT / k).read_text(encoding="utf-8") != v}
    require(bool(changed) and not (ROOT / ("registrations/" + receipt["identity"] + ".json")).exists(),
            "already_registered")
    validate_build(files)
    return publish(endpoint, master, changed, receipt)


def main():
    run(os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_SHA"),
        os.environ.get("REGISTRATION_REQUEST", ""), os.environ.get("REPOSITORY_OWNER"),
        os.environ.get("GITHUB_ACTOR"), os.environ.get("TRIGGERING_ACTOR"),
        os.environ.get("EVIDENCE_REVIEWED") == "true")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, TypeError, IndexError, OSError, subprocess.SubprocessError) as exc:
        code = str(exc) if type(exc) is ValueError and re.fullmatch(r"[a-z_]{1,80}", str(exc)) else maintenance.diagnostic(exc)
        print("REGISTRATION_BLOCKED:", code, file=sys.stderr)
        sys.exit(1)
