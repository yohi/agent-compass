"""Policy-bounded, owner-opt-in adoption of public, candidate-only PRs."""
import base64
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit

import adoption
import advisory
import compass
import generator

ROOT = Path(__file__).resolve().parent
REPO = adoption.REPO
POLICY_PATH = "registry/adoption-policy.json"
REGISTRY_PATHS = ("registry/sources.json", "registry/targets.json", "registry/practices.json",
                  "registry/generation.json", "registry/audit.json")
MODES = {"manual", "assisted", "conservative"}
BOT = "github-actions[bot]"
# Conservative lexical exclusion, not proof that advice is safe.
SENSITIVE = re.compile(
    r"\b(?:secur(?:ity|e)|permission|credential|password|secret|sandbox|auth(?:entication|orization)?|"
    r"privilege|bypass|disable|network access|tool execution|system prompt|approval|"
    r"system instruction|agent[s]?\.md|delete|destructive|production|billing|paid)\b"
    r"|セキュリティ|権限|認証|認可|秘密|パスワード|サンドボックス|承認|課金|削除|無効化|本番",
    re.IGNORECASE)
# The source proposal may contain 'disable thinking' as legitimate runtime guidance;
# do not exempt other security-related matches. Exact model-scope and placement are mandatory.
SENSITIVE_EXCEPT = re.compile(r"\bdisable\s+(?:the\s+)?thinking(?:\s+mode)?\b|思考(?:モード)?を無効化",
                              re.IGNORECASE)


def require(ok, code):
    if not ok:
        raise ValueError(code)


def gh(*args, payload=None):
    return compass.gh(*args, payload=payload)


def mode_value(env):
    mode = env.get("KNOWLEDGE_ADOPTION_MODE", "") or "manual"
    require(mode in MODES, "unsupported_adoption_mode")
    return mode


def policy():
    p = compass.read_json(ROOT / POLICY_PATH)
    # Registry policy can narrow defaults, not expand authority without code change.
    require(set(p) == {"schema_version", "allowed_targets", "allowed_categories", "allowed_statuses",
                       "allowed_placements", "configuration_kind", "max_items", "max_merges_per_run",
                       "require_complete_source"} and p["schema_version"] == 1, "policy_shape")
    for key, maximum in (("allowed_targets", {"family", "model"}),
                         ("allowed_categories", {"reasoning", "prompting", "context"}),
                         ("allowed_statuses", {"conditional", "recommended"}),
                         ("allowed_placements", {"configuration", "author-guidance"})):
        require(isinstance(p[key], list) and bool(p[key]) and set(p[key]) <= maximum, "policy_scope")
    require(p["configuration_kind"] == "api-or-runtime" and type(p["max_items"]) is int
            and 1 <= p["max_items"] <= 3 and p["max_merges_per_run"] == 1
            and p["require_complete_source"] is True, "policy_limits")
    return p


def selected_advice(comments, report, head):
    """Read the exact existing bot ADOPT comment; never execute model-authored text."""
    marker = f"<!-- {advisory.COMMENT_MARKER}:{head} -->"
    found = [c for c in comments if c.get("user", {}).get("login") == BOT
             and isinstance(c.get("body"), str) and c["body"].startswith(marker)]
    if len(found) != 1:
        return None
    c = found[0]
    body = c["body"]
    require(len(body.encode()) <= 30000 and type(c.get("id")) is int and c["id"] > 0, "advice_shape")
    # Reject altered/ambiguous evidence when update metadata is available.
    require(c.get("created_at") == c.get("updated_at") and c.get("created_at") is not None,
            "advice_edited")
    lines = body.splitlines()
    if len(lines) < 15 or lines[1] != "## Independent adoption advisory — ADOPT":
        return None
    def field(prefix):
        vals = [s[len(prefix):] for s in lines if s.startswith(prefix)]
        require(len(vals) == 1, "advice_field")
        return vals[0]
    require(field("- Proposal HEAD: ") == head
            and field("- Source snapshot SHA-256: ") == report["source_sha256"], "advice_identity")
    master = field("- Registry base: ")
    reviewer = field("- Reviewer: ").split(" / ")
    require(adoption.commit_sha(master) and len(reviewer) == 2
            and advisory.valid_model(*reviewer), "advice_provenance")
    require("Exact source/record validation passed; semantic judgment is unverified model advice." in lines,
            "advice_validation")
    require(all(any(line.startswith(f"- {i}. **ADOPT** — ") for line in lines)
                for i in range(1, len(report["proposals"]) + 1)), "advice_incomplete")
    # Only the exact structured decisions block is consumed.
    fence = chr(96) * 3
    pattern = r"(?m)^" + fence + r"json\n([\s\S]*?)\n" + fence + r"$"
    blocks = re.findall(pattern, body)
    require(len(blocks) == 1, "advice_decisions")
    selected = adoption.decisions(blocks[0], len(report["proposals"]))
    require(len(selected) == len(report["proposals"]), "advice_partial")
    return {"comment_id": c["id"], "comment_sha256": compass.digest(body),
            "registry_base": master, "provider": reviewer[0], "model": reviewer[1],
            "decisions": selected}


def eligible(report, selected, targets, source, content, p):
    items = report["proposals"]
    if report["partial_source"] or len(content.encode()) > 30000 or not (1 <= len(items) <= p["max_items"]):
        return False
    if len(selected) != len(items):
        return False
    for item, d in zip(items, selected):
        proposed = item["proposed"]
        if (item["action"] != "add" or item["practice_id"] != ""
                or proposed["target"] != source["target"]
                or targets.get(proposed["target"], {}).get("kind") not in p["allowed_targets"]
                or proposed["category"] not in p["allowed_categories"]
                or proposed["local_eval"] != "not_verified"
                or d["status"] not in p["allowed_statuses"]
                or d["placement"] not in p["allowed_placements"]):
            return False
        if d["placement"] == "configuration" and d.get("configuration_kind") != p["configuration_kind"]:
            return False
        text = " ".join(proposed[k] for k in ("en", "ja", "scope", "reason"))
        if SENSITIVE.search(SENSITIVE_EXCEPT.sub("", text)):
            return False
    return True


def same_registry(endpoint, old, master):
    """Allow intervening code-only commits, not a changed registry review context."""
    if old == master:
        return True
    # Compare exact immutable file blobs rather than trusting a truncated diff.
    comparison = gh(f"{endpoint}/compare/{old}...{master}")
    if comparison.get("behind_by") != 0 or comparison.get("status") not in {"ahead", "identical"}:
        return False
    for path in REGISTRY_PATHS:
        a = gh(f"{endpoint}/contents/{path}?ref={old}")
        b = gh(f"{endpoint}/contents/{path}?ref={master}")
        if a.get("type") != "file" or b.get("type") != "file" or a.get("sha") != b.get("sha"):
            return False
    return True


def comments_for(endpoint, number):
    pages = gh("--paginate", "--slurp", f"{endpoint}/issues/{number}/comments?per_page=100")
    return [c for page in pages for c in page]


def check_candidate(endpoint, pr, master, registries, p):
    number, head = pr["number"], pr["head"]["sha"]
    current = adoption.get_pr(endpoint, number, head)
    require(current["user"]["login"] == BOT, "candidate_author")
    report, path, raw = adoption.get_candidate(endpoint, number, head, current)
    advice = selected_advice(comments_for(endpoint, number), report, head)
    if advice is None or not same_registry(endpoint, advice["registry_base"], master):
        return None
    s, t, practices, g, audit = registries
    source = s.get(report["source_id"])
    require(source and source["url"] == report["source_url"], "source_registration_changed")
    body, fmt, _ = compass.fetch_document(source, {urlsplit(source["url"]).hostname})
    content = compass.normalize(body, fmt)
    adoption.validate_report(report, source, practices, content)
    if not eligible(report, advice["decisions"], t, source, content, p):
        return None
    return current, report, path, raw, advice, content


def read_pr(endpoint, number, head, draft=None):
    pr = gh(f"{endpoint}/pulls/{number}")
    require(pr["state"] == "open" and pr["head"]["sha"] == head
            and pr["head"]["repo"]["full_name"] == REPO
            and pr["base"]["repo"]["full_name"] == REPO
            and pr["base"]["ref"] == "master" and pr["user"]["login"] == BOT
            and (draft is None or pr["draft"] is draft), "prepared_pr_changed")
    return pr


def prepare(endpoint, master, candidate, registries, p, mode):
    pr, report, path, raw, advice, content = candidate
    number, head, branch = pr["number"], pr["head"]["sha"], pr["head"]["ref"]
    files, receipt = adoption.plan(report, advice["decisions"], *registries, content,
                                    datetime.now(timezone.utc).date().isoformat())
    # Do not misrepresent model advice as a per-candidate human review.
    receipt.update(state="AUTO_POLICY_SELECTED_PENDING_MERGE",
                   semantic_evidence="MODEL_ADVISORY_OWNER_POLICY_AUTHORIZED",
                   pr=number, approved_head=head, master_base=master,
                   actor=BOT, proposal_file_sha256=compass.digest(raw),
                   auto_adoption={"mode": mode, "policy_sha256": compass.digest(
                       json.dumps(p, sort_keys=True, ensure_ascii=True)), **advice})
    receipt_path = f"adoptions/{report['identity']}.json"
    require(not (ROOT / receipt_path).exists() and not (ROOT / path).exists(), "already_adopted_or_merged")
    changed = {k: v for k, v in files.items() if (ROOT / k).read_text(encoding="utf-8") != v}
    require("registry/practices.json" in changed and "registry/audit.json" not in changed, "auto_write_scope")
    adoption.validate_build(files)
    require(adoption.current_ref(endpoint, "master") == master, "master_changed_during_validation")
    adoption.get_pr(endpoint, number, head)
    require(adoption.current_ref(endpoint, branch) == head, "candidate_ref_changed")
    # Re-read exact advisory before writing; edits/deletion are fail-closed.
    require(selected_advice(comments_for(endpoint, number), report, head) == advice, "advice_changed")
    tree = gh(f"{endpoint}/git/commits/{master}")["tree"]["sha"]
    additions = {**changed, path: raw, receipt_path: adoption.encode(receipt)}
    result = gh("--method", "POST", f"{endpoint}/git/trees", payload={"base_tree": tree, "tree": [
        {"path": k, "mode": "100644", "type": "blob", "content": v} for k, v in sorted(additions.items())]})
    new = gh("--method", "POST", f"{endpoint}/git/commits", payload={
        "message": f"Prepare policy-selected knowledge adoption for PR #{number}",
        "tree": result["sha"], "parents": [head, master]})
    require(adoption.current_ref(endpoint, "master") == master
            and adoption.current_ref(endpoint, branch) == head, "ref_changed_before_update")
    gh("--method", "PATCH", f"{endpoint}/git/refs/heads/{branch}",
       payload={"sha": new["sha"], "force": False})
    require(adoption.current_ref(endpoint, branch) == new["sha"], "ref_readback_failed")
    print("AUTO_ADOPTION_PREPARED", number, new["sha"], flush=True)
    return number, new["sha"], result["sha"], receipt_path


def merge_and_publish(endpoint, master, prepared, sleep=time.sleep):
    number, head, expected_tree, receipt_path = prepared
    require(adoption.current_ref(endpoint, "master") == master, "master_changed_before_merge")
    pr = read_pr(endpoint, number, head, draft=True)
    # Drafts cannot merge. Mark ready, never approve or bypass checks.
    query = ("mutation($id:ID!){markPullRequestReadyForReview(input:{pullRequestId:$id})"
             "{pullRequest{isDraft headRefOid}}}")
    result = gh("graphql", payload={"query": query, "variables": {"id": pr["node_id"]}})
    require(not result.get("errors") and result["data"]["markPullRequestReadyForReview"]["pullRequest"]
            == {"isDraft": False, "headRefOid": head}, "ready_for_review_failed")
    for attempt in range(4):
        pr = read_pr(endpoint, number, head, draft=False)
        if pr.get("mergeable") is not None and pr.get("mergeable_state") != "unknown":
            break
        if attempt < 3:
            sleep(3)
    # Existing branch rules and checks are authoritative. No --admin, approval or
    # invented check status. If checks are pending/blocked, leave prepared PR for Owner.
    if pr.get("mergeable") is not True or pr.get("mergeable_state") != "clean":
        print("AUTO_ADOPTION_PENDING_GITHUB_CHECKS", number, flush=True)
        return "PENDING"
    require(pr["base"]["sha"] == master and adoption.current_ref(endpoint, "master") == master,
            "master_changed_before_merge")
    # GitHub's REST merge SHA guards the HEAD, not an atomic expected-base SHA.
    # Check the resulting commit/tree before requesting deployment.
    merged = gh("--method", "PUT", f"{endpoint}/pulls/{number}/merge",
                payload={"sha": head, "merge_method": "merge",
                         "commit_title": f"Adopt policy-selected knowledge (#{number})"})
    require(merged.get("merged") is True and adoption.commit_sha(merged.get("sha")), "merge_rejected")
    sha = merged["sha"]
    print("AUTO_ADOPTION_MERGED", number, sha, flush=True)
    actual = gh(f"{endpoint}/git/commits/{sha}")
    require(actual["tree"]["sha"] == expected_tree
            and [v["sha"] for v in actual["parents"]] == [master, head], "merged_tree_or_base_changed")
    require(adoption.current_ref(endpoint, "master") == sha, "master_advanced_after_merge")
    # GITHUB_TOKEN merges do not trigger ordinary push workflows. Explicit dispatch
    # is supported; existing portal-health workflow verifies the published snapshot.
    gh("--method", "POST", f"{endpoint}/actions/workflows/pages.yml/dispatches", payload={"ref": "master"})
    print("AUTO_ADOPTION_PAGES_DISPATCHED", sha, flush=True)
    return "MERGED"


def run(repo, master, env, event):
    require(repo == REPO and adoption.commit_sha(master)
            and event in {"schedule", "workflow_dispatch", "workflow_run"}, "auto_execution_context")
    mode = mode_value(env)
    if mode == "manual":
        print("AUTO_ADOPTION_DISABLED")
        return 0
    if event == "workflow_dispatch":
        require(env.get("REPOSITORY_OWNER") == env.get("GITHUB_ACTOR")
                == env.get("TRIGGERING_ACTOR") == "yohi", "owner_authorization")
    if event == "workflow_run":
        require(env.get("UPSTREAM_BRANCH") == "master" and env.get("UPSTREAM_REPO") == REPO
                and env.get("UPSTREAM_CONCLUSION") == "success", "upstream_scope")
    p = policy()
    endpoint = f"repos/{repo}"
    require(adoption.current_ref(endpoint, "master") == master, "master_changed")
    s, t, practices = compass.load_registry()
    registries = (s, t, practices, generator.load_generation(t, practices),
                  compass.read_json(ROOT / "registry/audit.json"))
    pages = gh("--paginate", "--slurp", f"{endpoint}/pulls?state=open&base=master&per_page=100")
    candidates = [pr for page in pages for pr in page if pr["draft"] is True
                  and pr["user"]["login"] == BOT and pr["head"]["repo"]
                  and pr["head"]["repo"]["full_name"] == REPO
                  and re.fullmatch(r"compass-proposals/[a-f0-9]{64}", pr["head"]["ref"])]
    for pr in sorted(candidates, key=lambda v: v["number"]):
        try:
            candidate = check_candidate(endpoint, pr, master, registries, p)
        except (ValueError, KeyError, TypeError, IndexError, OSError):
            print("AUTO_ADOPTION_OWNER_REVIEW_REQUIRED", pr["number"], flush=True)
            continue
        if candidate is None:
            print("AUTO_ADOPTION_OWNER_REVIEW_REQUIRED", pr["number"], flush=True)
            continue
        # At most one preparation per run: validated local registry is then modified.
        prepared = prepare(endpoint, master, candidate, registries, p, mode)
        if mode == "conservative":
            merge_and_publish(endpoint, master, prepared)
        return 0
    print("AUTO_ADOPTION_NO_ELIGIBLE_CANDIDATE")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(run(os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_SHA"),
                     os.environ, os.environ.get("GITHUB_EVENT_NAME")))
    except Exception as exc:
        # Fixed reason codes only, never external response or model text.
        code = exc.args[0] if type(exc) is ValueError and len(exc.args) == 1 and isinstance(exc.args[0], str) \
            and re.fullmatch(r"[a-z_]{1,80}", exc.args[0]) else advisory.diagnostic(exc)
        print("AUTO_ADOPTION_STOPPED:", code, file=sys.stderr, flush=True)
        sys.exit(1)
