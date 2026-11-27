"""Policy-bounded, owner-opt-in adoption of public, candidate-only PRs."""
import base64
import hashlib
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


def read_pr(endpoint, number, head, draft=None, sleep=time.sleep):
    for attempt in range(6):
        pr = gh(f"{endpoint}/pulls/{number}")
        require(pr["state"] == "open"
                and pr["head"]["repo"]["full_name"] == REPO
                and pr["base"]["repo"]["full_name"] == REPO
                and pr["base"]["ref"] == "master" and pr["user"]["login"] == BOT
                and re.fullmatch(r"compass-proposals/[a-f0-9]{64}", pr["head"]["ref"]),
                "prepared_pr_scope_changed")
        if pr["head"]["sha"] == head and (draft is None or pr["draft"] is draft):
            return pr
        # Only tolerate API propagation lag when the branch ref is already exact.
        require(adoption.current_ref(endpoint, pr["head"]["ref"]) == head, "prepared_ref_changed")
        if attempt < 5:
            sleep(2)
    raise ValueError("prepared_pr_state_timeout")


def blob_id(text):
    raw = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def read_data(endpoint, path, ref, limit=4000000):
    entry = gh(f"{endpoint}/contents/{path}?ref={ref}")
    require(entry["type"] == "file" and entry["encoding"] == "base64"
            and type(entry["size"]) is int and 0 < entry["size"] <= limit, "prepared_data_shape")
    raw = base64.b64decode("".join(entry["content"].split()), validate=True)
    require(len(raw) == entry["size"], "prepared_data_size")
    text = raw.decode("utf-8")
    require(blob_id(text) == entry["sha"], "prepared_blob_identity")
    return text


def tree_files(endpoint, commit):
    obj = gh(f"{endpoint}/git/commits/{commit}")
    tree = gh(f"{endpoint}/git/trees/{obj['tree']['sha']}?recursive=1")
    require(tree.get("truncated") is False, "tree_truncated")
    rows = {x["path"]: (x["mode"], x["type"], x["sha"]) for x in tree["tree"]
            if x["type"] != "tree"}
    require(len(rows) == sum(x["type"] != "tree" for x in tree["tree"]), "tree_duplicate")
    return rows


def receipt_for(receipt, report, advice, raw, p, number, head, master, mode):
    receipt.update(state="AUTO_POLICY_SELECTED_PENDING_MERGE",
                   semantic_evidence="MODEL_ADVISORY_OWNER_POLICY_AUTHORIZED",
                   pr=number, approved_head=head, master_base=master,
                   actor=BOT, proposal_file_sha256=compass.digest(raw),
                   auto_adoption={"mode": mode, "policy_sha256": compass.digest(
                       json.dumps(p, sort_keys=True, ensure_ascii=True)), **advice})
    return receipt


def verify_prepared(endpoint, master, pr, registries, p):
    """Reconstruct expected data only; never check out or execute candidate code."""
    number, head = pr["number"], pr["head"]["sha"]
    pr = read_pr(endpoint, number, head)
    identity = pr["head"]["ref"].removeprefix("compass-proposals/")
    receipt_path = f"adoptions/{identity}.json"
    receipt = adoption.parse_json(read_data(endpoint, receipt_path, head, 40000), 40000)
    old, origin = receipt["master_base"], receipt["approved_head"]
    require(adoption.commit_sha(old) and adoption.commit_sha(origin)
            and receipt["state"] == "AUTO_POLICY_SELECTED_PENDING_MERGE"
            and receipt["auto_adoption"]["mode"] == "conservative"
            and receipt["pr"] == number, "prepared_receipt_scope")
    obj = gh(f"{endpoint}/git/commits/{head}")
    require([v["sha"] for v in obj["parents"]] == [origin, old], "prepared_parents")
    require(same_registry(endpoint, old, master), "prepared_registry_changed")
    source_id = receipt["source_id"]
    require(compass.ID.fullmatch(source_id), "prepared_source_id")
    path = f"proposals/{source_id}/{identity}.json"
    raw = read_data(endpoint, path, origin, adoption.MAX_PROPOSAL)
    report = adoption.parse_json(raw, adoption.MAX_PROPOSAL)
    require(adoption.proposal_path(report) == path, "prepared_proposal_identity")
    original = gh(f"{endpoint}/git/commits/{origin}")
    require([v["sha"] for v in original["parents"]] == [report["base_commit"]], "candidate_parent")
    original_base = tree_files(endpoint, report["base_commit"])
    require(path not in original_base, "candidate_already_present")
    expected_origin = {**original_base, path: ("100644", "blob", blob_id(raw))}
    require(tree_files(endpoint, origin) == expected_origin, "candidate_commit_scope")
    advice = selected_advice(comments_for(endpoint, number), report, origin)
    require(advice is not None and same_registry(endpoint, advice["registry_base"], master),
            "prepared_advice_changed")
    s, t, practices, g, audit = registries
    source = s.get(source_id)
    require(source and source["url"] == report["source_url"], "source_registration_changed")
    body, fmt, _ = compass.fetch_document(source, {urlsplit(source["url"]).hostname})
    content = compass.normalize(body, fmt)
    adoption.validate_report(report, source, practices, content)
    require(eligible(report, advice["decisions"], t, source, content, p), "prepared_policy_changed")
    files, expected = adoption.plan(report, advice["decisions"], *registries, content,
                                    receipt["source_checked"])
    expected = receipt_for(expected, report, advice, raw, p, number, origin, old, "conservative")
    require(receipt == expected, "prepared_receipt_mismatch")
    old_tree = tree_files(endpoint, old)
    current_tree = tree_files(endpoint, master)
    require(all(old_tree.get(k) == current_tree.get(k) for k in adoption.DATA_PATHS)
            and path not in old_tree and receipt_path not in old_tree
            and path not in current_tree and receipt_path not in current_tree, "prepared_data_base_changed")
    additions = {**files, path: raw, receipt_path: adoption.encode(expected)}
    # Unchanged files retain their existing bytes. The preparation wrote only
    # files whose generated text differed from the original trusted checkout.
    expected_delta = {k: v for k, v in additions.items()
                      if old_tree.get(k) != ("100644", "blob", blob_id(v))}
    require("registry/practices.json" in expected_delta
            and "registry/audit.json" not in expected_delta, "auto_write_scope")
    expected_old_tree = {**old_tree, **{k: ("100644", "blob", blob_id(v))
                                       for k, v in expected_delta.items()}}
    require(tree_files(endpoint, head) == expected_old_tree, "prepared_tree_mismatch")
    expected_merge_tree = {**current_tree, **{k: ("100644", "blob", blob_id(v))
                                            for k, v in expected_delta.items()}}
    return files, expected_merge_tree, receipt_path


def registries_now():
    s, t, practices = compass.load_registry()
    return (s, t, practices, generator.load_generation(t, practices),
            compass.read_json(ROOT / "registry/audit.json"))


def validation_title(number, head, master, nonce):
    return f"Adoption validation PR {number} {head} {master} {nonce}"


def dispatch_validation(endpoint, master, number, head, env, sleep=time.sleep):
    nonce = env.get("GITHUB_RUN_ID", "") + "-" + env.get("GITHUB_RUN_ATTEMPT", "")
    require(re.fullmatch(r"[0-9]+-[0-9]+", nonce), "validation_nonce")
    title = validation_title(number, head, master, nonce)
    require(adoption.current_ref(endpoint, "master") == master, "master_changed_before_ci")
    result = gh("--method", "POST", "-H", "X-GitHub-Api-Version: 2026-03-10",
                f"{endpoint}/actions/workflows/validate-adoption.yml/dispatches",
                payload={"ref": "master", "inputs": {"proposal_pr": str(number),
                         "prepared_head": head, "expected_master": master, "nonce": nonce}})
    run_id = result.get("workflow_run_id") if isinstance(result, dict) else None
    # Older API behavior may return 204. Bind to a unique run-name, never
    # accept the latest arbitrary successful run.
    for attempt in range(48):
        if run_id is None:
            runs = gh(f"{endpoint}/actions/workflows/validate-adoption.yml/runs?event=workflow_dispatch&branch=master&head_sha={master}&per_page=100")
            matched = [r for r in runs["workflow_runs"] if r.get("display_title") == title]
            require(len(matched) <= 1, "validation_run_ambiguous")
            if matched:
                run_id = matched[0]["id"]
        if run_id is not None:
            require(type(run_id) is int and run_id > 0, "validation_run_id")
            run = gh(f"{endpoint}/actions/runs/{run_id}")
            require(run["head_sha"] == master and run["head_branch"] == "master"
                    and run["event"] == "workflow_dispatch" and run["path"] == ".github/workflows/validate-adoption.yml"
                    and run["display_title"] == title and run["actor"]["login"] == BOT, "validation_run_identity")
            if run["status"] == "completed":
                require(run["conclusion"] == "success", "validation_ci_failed")
                jobs = gh(f"{endpoint}/actions/runs/{run_id}/jobs?per_page=100")
                require(jobs["total_count"] == 1 and jobs["jobs"][0]["name"] == "validate"
                        and jobs["jobs"][0]["conclusion"] == "success"
                        and any(x["name"] == "Validate exact prepared adoption" and x["conclusion"] == "success"
                                for x in jobs["jobs"][0]["steps"]), "validation_job_missing")
                print("AUTO_ADOPTION_CI_VERIFIED", run_id, head, flush=True)
                return
        if attempt < 47:
            sleep(10)
    raise ValueError("validation_ci_timeout")


def validate_dispatched(repo, master, env):
    require(repo == REPO and adoption.commit_sha(master)
            and env.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
            and env.get("GITHUB_ACTOR") == BOT and env.get("TRIGGERING_ACTOR") == BOT
            and env.get("EXPECTED_MASTER") == master, "validation_execution_context")
    number, head = env.get("PROPOSAL_PR", ""), env.get("PREPARED_HEAD", "")
    require(re.fullmatch(r"[1-9][0-9]{0,9}", number) and adoption.commit_sha(head),
            "validation_inputs")
    endpoint = f"repos/{repo}"
    require(adoption.current_ref(endpoint, "master") == master, "master_changed")
    pr = read_pr(endpoint, int(number), head)
    files, _, _ = verify_prepared(endpoint, master, pr, registries_now(), policy())
    adoption.validate_build(files)
    require(adoption.current_ref(endpoint, "master") == master, "master_changed_during_validation")
    read_pr(endpoint, int(number), head)
    print("EXACT_PREPARED_ADOPTION_VALIDATED", head, flush=True)
    return 0


def only_optional_bot_ci_pending(endpoint, head):
    """Do not approve pending PR runs. A successful trusted dispatch replaces
    the local validation evidence only; GitHub's merge rules remain authoritative."""
    branch = gh(f"{endpoint}/branches/master")
    if branch.get("protected") is not False:
        return False
    checks = gh(f"{endpoint}/commits/{head}/check-runs?per_page=100")
    if checks["total_count"] != len(checks["check_runs"]) or any(
            c["status"] != "completed" or c["conclusion"] not in {"success", "neutral", "skipped"}
            for c in checks["check_runs"]):
        return False
    status = gh(f"{endpoint}/commits/{head}/status?per_page=100")
    if status["total_count"] != len(status["statuses"]) or any(
            x["state"] != "success" for x in status["statuses"]):
        return False
    runs = gh(f"{endpoint}/actions/runs?head_sha={head}&per_page=100")
    if runs["total_count"] != len(runs["workflow_runs"]):
        return False
    pending = [r for r in runs["workflow_runs"] if r["status"] != "completed"
               or r["conclusion"] != "success"]
    return bool(pending) and all(r["head_sha"] == head and r["event"] == "pull_request"
              and r["path"] == ".github/workflows/validate.yml"
              and r["actor"]["login"] == BOT and r["status"] == "completed"
              and r["conclusion"] == "action_required" for r in pending)


def prepare(endpoint, master, candidate, registries, p, mode):
    pr, report, path, raw, advice, content = candidate
    number, head, branch = pr["number"], pr["head"]["sha"], pr["head"]["ref"]
    files, receipt = adoption.plan(report, advice["decisions"], *registries, content,
                                    datetime.now(timezone.utc).date().isoformat())
    receipt = receipt_for(receipt, report, advice, raw, p, number, head, master, mode)
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


def merge_and_publish(endpoint, master, prepared, env, sleep=time.sleep):
    number, head, expected_tree, receipt_path = prepared
    require(adoption.current_ref(endpoint, "master") == master, "master_changed_before_merge")
    dispatch_validation(endpoint, master, number, head, env, sleep)
    pr = read_pr(endpoint, number, head)
    # Drafts cannot merge. Mark ready only if still draft.
    if pr["draft"]:
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
    state = pr.get("mergeable_state")
    acceptable = state == "clean" or (state == "unstable" and only_optional_bot_ci_pending(endpoint, head))
    if pr.get("mergeable") is not True or not acceptable:
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
    tree_matches = (tree_files(endpoint, sha) == expected_tree if isinstance(expected_tree, dict)
                    else actual["tree"]["sha"] == expected_tree)
    require(tree_matches and [v["sha"] for v in actual["parents"]] == [master, head],
            "merged_tree_or_base_changed")
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
    registries = registries_now()
    pages = gh("--paginate", "--slurp", f"{endpoint}/pulls?state=open&base=master&per_page=100")
    candidates = [pr for page in pages for pr in page if pr["user"]["login"] == BOT and pr["head"]["repo"]
                  and pr["head"]["repo"]["full_name"] == REPO
                  and re.fullmatch(r"compass-proposals/[a-f0-9]{64}", pr["head"]["ref"])]
    for pr in sorted(candidates, key=lambda v: v["number"]):
        # Resume only bot-policy conservative receipts; never touch an owner
        # selection or assisted draft. No new candidate commit or LLM call.
        if mode == "conservative":
            identity = pr["head"]["ref"].removeprefix("compass-proposals/")
            changed = gh("--paginate", "--slurp", f"{endpoint}/pulls/{pr['number']}/files?per_page=100")
            if any(x["filename"] == f"adoptions/{identity}.json" for page in changed for x in page):
                try:
                    _, expected_tree, receipt_path = verify_prepared(endpoint, master, pr, registries, p)
                except (ValueError, KeyError, TypeError, IndexError, OSError):
                    print("AUTO_ADOPTION_OWNER_REVIEW_REQUIRED", pr["number"], flush=True)
                    continue
                print("AUTO_ADOPTION_RESUMED", pr["number"], pr["head"]["sha"], flush=True)
                merge_and_publish(endpoint, master, (pr["number"], pr["head"]["sha"],
                                  expected_tree, receipt_path), env)
                return 0
        if pr["draft"] is not True:
            continue
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
            merge_and_publish(endpoint, master, prepared, env)
        return 0
    print("AUTO_ADOPTION_NO_ELIGIBLE_CANDIDATE")
    return 0


if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["--validate-prepared"]:
            sys.exit(validate_dispatched(os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_SHA"), os.environ))
        require(not sys.argv[1:], "unknown_arguments")
        sys.exit(run(os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_SHA"),
                     os.environ, os.environ.get("GITHUB_EVENT_NAME")))
    except Exception as exc:
        # Fixed reason codes only, never external response or model text.
        code = exc.args[0] if type(exc) is ValueError and len(exc.args) == 1 and isinstance(exc.args[0], str) \
            and re.fullmatch(r"[a-z_]{1,80}", exc.args[0]) else advisory.diagnostic(exc)
        print("AUTO_ADOPTION_STOPPED:", code, file=sys.stderr, flush=True)
        sys.exit(1)
