import copy
import json
import unittest
from unittest.mock import patch

import adoption
import advisory
import auto_adoption as a
import compass
import generator
import maintenance


class AutoAdoptionTests(unittest.TestCase):
    def setUp(self):
        self.s, self.t, self.p = compass.load_registry()
        self.g = generator.load_generation(self.t, self.p)
        self.audit = compass.read_json(compass.ROOT / "registry/audit.json")
        self.policy = a.policy()
        self.source = next(s for s in self.s.values()
                           if self.t[s["target"]]["kind"] in {"model", "family"})
        self.content = "Recommended sampling guidance: temperature 0.6 for reasoning mode."
        row = maintenance.observe(maintenance.empty_state(), self.source, self.content, "2026-11-27")
        item = {"action": "add", "practice_id": "", "target": self.source["target"],
                "category": "reasoning", "status": "candidate", "en": "Use temperature 0.6 for reasoning.",
                "ja": "推論時はtemperatureを0.6に設定する。", "scope": "Exact target only.",
                "reason": "Sampling guidance.", "evidence_quote": "temperature 0.6"}
        self.report = maintenance.validate_proposals({"proposals": [item]}, self.source, row, self.p,
                         self.content, maintenance.config(), "gemini-3.8-flash", False)
        self.head, self.master = "a"*40, "b"*40
        self.report["base_commit"] = self.master
        self.selected = [{"index": 1, "status": "conditional", "placement": "configuration",
                          "configuration_kind": "api-or-runtime"}]
        result = {"verdict": "ADOPT", "items": [{"index": 1, "verdict": "ADOPT", "reason": "一致"}],
                  "decisions": self.selected}
        self.comment = {"id": 1, "user": {"login": a.BOT}, "created_at": "t", "updated_at": "t",
                        "body": advisory.comment_body(self.head, self.master, self.report, result,
                                                      advisory.config()["providers"][0])}
        self.endpoint = "repos/" + a.REPO

    def test_advice_and_policy(self):
        advice = a.selected_advice([self.comment], self.report, self.head)
        self.assertEqual(advice["decisions"], self.selected)
        self.assertTrue(a.eligible(self.report, self.selected, self.t, self.source, self.content, self.policy))
        self.assertIsNone(a.selected_advice([self.comment, self.comment], self.report, self.head))
        self.assertIsNone(a.selected_advice([{**self.comment, "user": {"login": "other"}}], self.report, self.head))
        with self.assertRaises(ValueError):
            a.selected_advice([{**self.comment, "updated_at": "other"}], self.report, self.head)
        for action, category, en in (("amend", "reasoning", "Sample"), ("add", "security", "Sample"),
                                     ("add", "reasoning", "Disable sandbox permissions")):
            report = copy.deepcopy(self.report)
            report["proposals"][0]["action"] = action
            report["proposals"][0]["proposed"].update(category=category, en=en)
            self.assertFalse(a.eligible(report, self.selected, self.t, self.source, self.content, self.policy))
        self.assertFalse(a.eligible({**self.report, "partial_source": True}, self.selected, self.t,
                                    self.source, self.content, self.policy))
        self.assertFalse(a.eligible(self.report, [], self.t, self.source, self.content, self.policy))

    def test_manual_and_authorization(self):
        with patch.object(a, "gh") as gh:
            self.assertEqual(a.run(a.REPO, self.master, {}, "schedule"), 0)
            with self.assertRaises(ValueError):
                a.run(a.REPO, self.master, {"KNOWLEDGE_ADOPTION_MODE": "conservative"}, "workflow_dispatch")
            with self.assertRaises(ValueError):
                a.run(a.REPO, self.master, {"KNOWLEDGE_ADOPTION_MODE": "conservative"}, "workflow_run")
            gh.assert_not_called()

    def test_registry_base_identity(self):
        with patch.object(a, "gh", side_effect=[{"behind_by": 0, "status": "ahead"}] +
                          [{"type": "file", "sha": "same"}]*10):
            self.assertTrue(a.same_registry(self.endpoint, self.head, self.master))
        with patch.object(a, "gh", side_effect=[{"behind_by": 0, "status": "ahead"},
                          {"type": "file", "sha": "old"}, {"type": "file", "sha": "new"}]):
            self.assertFalse(a.same_registry(self.endpoint, self.head, self.master))

    def test_resume_reconstructs_exact_tree_without_new_commit(self):
        old, origin, head, current = "b"*40, "a"*40, "c"*40, "d"*40
        identity = self.report["identity"]
        pr = {"number": 4, "head": {"sha": head, "ref": "compass-proposals/" + identity}}
        path = adoption.proposal_path(self.report)
        receipt_path = f"adoptions/{identity}.json"
        raw = adoption.encode(self.report)
        advice = a.selected_advice([self.comment], self.report, origin)
        registries = (self.s, self.t, self.p, self.g, self.audit)
        files, receipt = adoption.plan(self.report, self.selected, *registries, self.content, "2026-11-27")
        receipt = a.receipt_for(receipt, self.report, advice, raw, self.policy,
                                4, origin, old, "conservative")
        def entry(text):
            return ("100644", "blob", a.blob_id(text))
        base = {k: entry(v) for k, v in files.items() if k not in {"registry/practices.json",
                                                                  "registry/generation.json",
                                                                  "docs/BEST_PRACTICES.md"}}
        base.update({"registry/practices.json": entry("old practices"),
                     "registry/generation.json": entry("old generation"),
                     "docs/BEST_PRACTICES.md": entry("old docs"),
                     "auto_adoption.py": entry("old code")})
        expected_delta = {k: entry(v) for k, v in {**files, path: raw,
                            receipt_path: adoption.encode(receipt)}.items()}
        prepared = {**base, **expected_delta}
        current_tree = {**base, "auto_adoption.py": entry("new trusted code")}
        trees = {old: base, origin: {**base, path: entry(raw)}, head: prepared, current: current_tree}
        def fake_gh(url):
            if url.endswith("/" + head):
                return {"parents": [{"sha": origin}, {"sha": old}]}
            if url.endswith("/" + origin):
                return {"parents": [{"sha": old}]}
            self.fail("unexpected GitHub operation")
        with patch.object(a, "read_pr", return_value=pr), \
                patch.object(a, "read_data", side_effect=[adoption.encode(receipt), raw]), \
                patch.object(a, "gh", side_effect=fake_gh), \
                patch.object(a, "same_registry", return_value=True), \
                patch.object(a, "tree_files", side_effect=lambda endpoint, ref: trees[ref]), \
                patch.object(a, "comments_for", return_value=[self.comment]), \
                patch.object(compass, "fetch_document", return_value=(self.content, "text", "unused")), \
                patch.object(compass, "normalize", return_value=self.content):
            generated, merged_tree, actual_receipt_path = a.verify_prepared(
                self.endpoint, current, pr, registries, self.policy)
            self.assertEqual(generated, files)
            self.assertEqual(actual_receipt_path, receipt_path)
            self.assertEqual(merged_tree, {**current_tree, **expected_delta})
        trees[head] = {**prepared, "evil.py": entry("unexpected code")}
        with patch.object(a, "read_pr", return_value=pr), \
                patch.object(a, "read_data", side_effect=[adoption.encode(receipt), raw]), \
                patch.object(a, "gh", side_effect=fake_gh), \
                patch.object(a, "same_registry", return_value=True), \
                patch.object(a, "tree_files", side_effect=lambda endpoint, ref: trees[ref]), \
                patch.object(a, "comments_for", return_value=[self.comment]), \
                patch.object(compass, "fetch_document", return_value=(self.content, "text", "unused")), \
                patch.object(compass, "normalize", return_value=self.content):
            with self.assertRaisesRegex(ValueError, "prepared_tree_mismatch"):
                a.verify_prepared(self.endpoint, current, pr, registries, self.policy)

    def test_read_pr_bounded_propagation(self):
        branch = "compass-proposals/" + "c"*64
        pr = {"state": "open", "draft": True, "user": {"login": a.BOT},
              "head": {"sha": self.head, "ref": branch, "repo": {"full_name": a.REPO}},
              "base": {"ref": "master", "repo": {"full_name": a.REPO}}}
        lag = {**pr, "head": {**pr["head"], "sha": "d"*40}}
        with patch.object(a, "gh", side_effect=[lag, pr]), \
                patch.object(adoption, "current_ref", return_value=self.head):
            self.assertEqual(a.read_pr(self.endpoint, 4, self.head, sleep=lambda _: None), pr)
        with patch.object(a, "gh", return_value=lag), \
                patch.object(adoption, "current_ref", return_value="e"*40):
            with self.assertRaisesRegex(ValueError, "prepared_ref_changed"):
                a.read_pr(self.endpoint, 4, self.head, sleep=lambda _: None)

    def validation_fixture(self, nonce="42-1"):
        run = {"id": 5, "head_sha": self.master, "head_branch": "master", "event": "workflow_dispatch",
               "path": ".github/workflows/validate-adoption.yml",
               "display_title": a.validation_title(4, self.head, self.master, nonce),
               "actor": {"login": a.BOT}, "triggering_actor": {"login": a.BOT},
               "repository": {"full_name": a.REPO}, "head_repository": {"full_name": a.REPO},
               "status": "completed", "conclusion": "success", "run_attempt": 1}
        jobs = {"total_count": 1, "jobs": [{"name": "validate", "conclusion": "success",
                "steps": [{"name": "Validate exact prepared adoption", "conclusion": "success"}]}]}
        return run, jobs

    def test_validation_dispatch_requires_exact_successful_job(self):
        env = {"GITHUB_RUN_ID": "42", "GITHUB_RUN_ATTEMPT": "1"}
        run, jobs = self.validation_fixture()
        with patch.object(adoption, "current_ref", return_value=self.master), \
                patch.object(a, "gh", side_effect=[{"workflow_runs": []}, {"workflow_run_id": 5}, run, jobs]) as gh:
            a.dispatch_validation(self.endpoint, self.master, 4, self.head, env, sleep=lambda _: None)
            self.assertIn("/attempts/1/jobs", gh.call_args_list[-1].args[0])
        with patch.object(adoption, "current_ref", return_value=self.master), \
                patch.object(a, "gh", side_effect=[{"workflow_runs": []}, {"workflow_run_id": 5}, run,
                                                  {"total_count": 0, "jobs": []}]):
            with self.assertRaisesRegex(ValueError, "validation_job_missing"):
                a.dispatch_validation(self.endpoint, self.master, 4, self.head, env, sleep=lambda _: None)

    def test_validation_waits_for_identity_propagation(self):
        run, jobs = self.validation_fixture()
        lag = {**run, "display_title": "", "actor": None, "triggering_actor": None}
        env = {"GITHUB_RUN_ID": "42", "GITHUB_RUN_ATTEMPT": "1"}
        with patch.object(adoption, "current_ref", return_value=self.master), \
                patch.object(a, "gh", side_effect=[{"workflow_runs": []}, {"workflow_run_id": 5},
                                                  lag, run, jobs]):
            a.dispatch_validation(self.endpoint, self.master, 4, self.head, env, sleep=lambda _: None)
        with patch.object(adoption, "current_ref", return_value=self.master), \
                patch.object(a, "gh", side_effect=[{"workflow_runs": []}, {"workflow_run_id": 5}]
                             + [{**run, "head_sha": "f"*40}]*6) as gh:
            with self.assertRaisesRegex(ValueError, "validation_run_identity"):
                a.dispatch_validation(self.endpoint, self.master, 4, self.head, env, sleep=lambda _: None)
            self.assertEqual(gh.call_count, 8)

    def test_validation_reuses_exact_success_without_dispatch(self):
        run, jobs = self.validation_fixture("41-1")
        env = {"GITHUB_RUN_ID": "42", "GITHUB_RUN_ATTEMPT": "1"}
        with patch.object(adoption, "current_ref", return_value=self.master), \
                patch.object(a, "gh", side_effect=[{"workflow_runs": [run]}, run, jobs]) as gh:
            a.dispatch_validation(self.endpoint, self.master, 4, self.head, env, sleep=lambda _: None)
            self.assertEqual(gh.call_count, 3)
            self.assertFalse(any(call.args[0] == "--method" for call in gh.call_args_list))
        # A stale base or wrong actor is not reusable, even with a matching title.
        new_run, new_jobs = self.validation_fixture()
        for stale in ({**run, "head_sha": "f"*40}, {**run, "triggering_actor": {"login": "other"}}):
            with patch.object(adoption, "current_ref", return_value=self.master), \
                    patch.object(a, "gh", side_effect=[{"workflow_runs": [stale]},
                                                      {"workflow_run_id": 5}, new_run, new_jobs]) as gh:
                a.dispatch_validation(self.endpoint, self.master, 4, self.head, env, sleep=lambda _: None)
                self.assertEqual(gh.call_args_list[1].args[0], "--method")

    def test_optional_pending_only(self):
        pending = {"head_sha": self.head, "event": "pull_request", "path": ".github/workflows/validate.yml",
                   "actor": {"login": a.BOT}, "status": "completed", "conclusion": "action_required"}
        responses = [{"protected": False}, {"total_count": 0, "check_runs": []},
                     {"total_count": 0, "statuses": []},
                     {"total_count": 1, "workflow_runs": [pending]}]
        with patch.object(a, "gh", side_effect=responses):
            self.assertTrue(a.only_optional_bot_ci_pending(self.endpoint, self.head))
        with patch.object(a, "gh", return_value={"protected": True}):
            self.assertFalse(a.only_optional_bot_ci_pending(self.endpoint, self.head))
        with patch.object(a, "gh", side_effect=responses[:-1] + [
                {"total_count": 1, "workflow_runs": [{**pending, "conclusion": "failure"}]}]):
            self.assertFalse(a.only_optional_bot_ci_pending(self.endpoint, self.head))

    def test_merge_inputs_use_live_refs_and_immutable_trees(self):
        old, master, head = "b"*40, "d"*40, "a"*40
        branch = "compass-proposals/" + "e"*64
        def entry(value):
            return ("100644", "blob", a.blob_id(value))
        base = {"registry/practices.json": entry("old"), "auto_adoption.py": entry("v1")}
        current = {**base, "auto_adoption.py": entry("v2")}
        prepared = {**base, "registry/practices.json": entry("new")}
        expected = {**current, "registry/practices.json": entry("new")}
        commit = {"parents": [{"sha": "c"*40}, {"sha": old}], "tree": {"sha": "tree"}}
        comparison = {"merge_base_commit": {"sha": old}}
        trees = {old: base, master: current, head: prepared}
        with patch.object(adoption, "current_ref", side_effect=[master, head, master, head]), \
                patch.object(a, "gh", side_effect=[commit, comparison]), \
                patch.object(a, "tree_files", side_effect=lambda endpoint, ref: trees[ref]):
            a.verify_merge_inputs(self.endpoint, master, head, branch, expected)
        with patch.object(adoption, "current_ref", side_effect=[master, "f"*40]), \
                patch.object(a, "gh") as gh:
            with self.assertRaisesRegex(ValueError, "prepared_ref_changed_before_merge"):
                a.verify_merge_inputs(self.endpoint, master, head, branch, expected)
            gh.assert_not_called()
        with patch.object(adoption, "current_ref", side_effect=[master, head, "f"*40]), \
                patch.object(a, "gh", side_effect=[commit, comparison]), \
                patch.object(a, "tree_files", side_effect=lambda endpoint, ref: trees[ref]):
            with self.assertRaisesRegex(ValueError, "master_changed_before_merge"):
                a.verify_merge_inputs(self.endpoint, master, head, branch, expected)
        with patch.object(adoption, "current_ref", side_effect=[master, head]), \
                patch.object(a, "gh", side_effect=[commit, {"merge_base_commit": {"sha": "f"*40}}]):
            with self.assertRaisesRegex(ValueError, "unexpected_merge_base"):
                a.verify_merge_inputs(self.endpoint, master, head, branch, expected)
        with patch.object(adoption, "current_ref", side_effect=[master, head]), \
                patch.object(a, "gh", side_effect=[commit, comparison]), \
                patch.object(a, "tree_files", side_effect=lambda endpoint, ref: trees[ref]):
            with self.assertRaisesRegex(ValueError, "projected_merge_tree_mismatch"):
                a.verify_merge_inputs(self.endpoint, master, head, branch, current)
        trees[master] = {**current, "registry/practices.json": entry("conflicting")}
        with patch.object(adoption, "current_ref", side_effect=[master, head]), \
                patch.object(a, "gh", side_effect=[commit, comparison]), \
                patch.object(a, "tree_files", side_effect=lambda endpoint, ref: trees[ref]):
            with self.assertRaisesRegex(ValueError, "overlapping_merge_change"):
                a.verify_merge_inputs(self.endpoint, master, head, branch, expected)

    def test_merge_inputs_fresh_preparation(self):
        master, head = self.master, self.head
        branch = "compass-proposals/" + "e"*64
        base = {"file": ("100644", "blob", a.blob_id("old"))}
        prepared = {"file": ("100644", "blob", a.blob_id("new"))}
        commit = {"parents": [{"sha": "c"*40}, {"sha": master}], "tree": {"sha": "tree"}}
        with patch.object(adoption, "current_ref", side_effect=[master, head, master, head]), \
                patch.object(a, "gh", side_effect=[commit, {"merge_base_commit": {"sha": master}}]), \
                patch.object(a, "tree_files", side_effect=[base, prepared]):
            a.verify_merge_inputs(self.endpoint, master, head, branch, "tree")

    def test_merge_dispatch_only_verified_tree(self):
        head, master, merged = self.head, self.master, "c"*40
        prepared = (4, head, "tree", "receipt")
        ready = {"data": {"markPullRequestReadyForReview": {"pullRequest":
                         {"isDraft": False, "headRefOid": head}}}}
        # Cached PR base SHA is stale, but immutable merge verification is authoritative.
        pr = {"node_id": "id", "draft": True, "mergeable": True, "mergeable_state": "clean",
              "base": {"sha": "f"*40}, "head": {"ref": "compass-proposals/" + "e"*64}}
        actual = {"tree": {"sha": "tree"}, "parents": [{"sha": master}, {"sha": head}]}
        with patch.object(adoption, "current_ref", side_effect=[master, merged]), \
                patch.object(a, "dispatch_validation"), \
                patch.object(a, "verify_merge_inputs") as verify, \
                patch.object(a, "read_pr", return_value=pr), \
                patch.object(a, "gh", side_effect=[ready, {"merged": True, "sha": merged}, actual, None]) as gh:
            self.assertEqual(a.merge_and_publish(self.endpoint, master, prepared, {}), "MERGED")
            verify.assert_called_once_with(self.endpoint, master, head, pr["head"]["ref"], "tree")
            self.assertEqual(gh.call_args_list[1].kwargs["payload"]["sha"], head)
            self.assertIn("/actions/workflows/pages.yml/dispatches", gh.call_args_list[-1].args[-1])
        with patch.object(adoption, "current_ref", return_value=master), \
                patch.object(a, "dispatch_validation"), \
                patch.object(a, "read_pr", return_value={**pr, "mergeable_state": "blocked"}), \
                patch.object(a, "gh", return_value=ready) as gh:
            self.assertEqual(a.merge_and_publish(self.endpoint, master, prepared, {}), "PENDING")
            self.assertEqual(gh.call_count, 1)
        with patch.object(adoption, "current_ref", return_value=master), \
                patch.object(a, "dispatch_validation"), \
                patch.object(a, "read_pr", return_value=pr), \
                patch.object(a, "verify_merge_inputs"), \
                patch.object(a, "gh", side_effect=[ready, {"merged": True, "sha": merged},
                    {**actual, "tree": {"sha": "wrong"}}]) as gh:
            with self.assertRaisesRegex(ValueError, "merged_tree_or_base_changed"):
                a.merge_and_publish(self.endpoint, master, prepared, {})
            self.assertEqual(gh.call_count, 3)


if __name__ == "__main__":
    unittest.main()
