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

    def test_merge_dispatch_only_verified_tree(self):
        head, master, merged = self.head, self.master, "c"*40
        prepared = (4, head, "tree", "receipt")
        ready = {"data": {"markPullRequestReadyForReview": {"pullRequest":
                         {"isDraft": False, "headRefOid": head}}}}
        pr = {"node_id": "id", "mergeable": True, "mergeable_state": "clean", "base": {"sha": master}}
        actual = {"tree": {"sha": "tree"}, "parents": [{"sha": master}, {"sha": head}]}
        with patch.object(adoption, "current_ref", side_effect=[master, master, merged]), \
                patch.object(a, "read_pr", return_value=pr), \
                patch.object(a, "gh", side_effect=[ready, {"merged": True, "sha": merged}, actual, None]) as gh:
            self.assertEqual(a.merge_and_publish(self.endpoint, master, prepared), "MERGED")
            self.assertEqual(gh.call_args_list[1].kwargs["payload"]["sha"], head)
            self.assertIn("/actions/workflows/pages.yml/dispatches", gh.call_args_list[-1].args[-1])
        with patch.object(adoption, "current_ref", return_value=master), \
                patch.object(a, "read_pr", return_value={**pr, "mergeable_state": "blocked"}), \
                patch.object(a, "gh", return_value=ready) as gh:
            self.assertEqual(a.merge_and_publish(self.endpoint, master, prepared), "PENDING")
            self.assertEqual(gh.call_count, 1)
        with patch.object(adoption, "current_ref", return_value=master), \
                patch.object(a, "read_pr", return_value=pr), \
                patch.object(a, "gh", side_effect=[ready, {"merged": True, "sha": merged},
                    {**actual, "tree": {"sha": "wrong"}}]) as gh:
            with self.assertRaisesRegex(ValueError, "merged_tree_or_base_changed"):
                a.merge_and_publish(self.endpoint, master, prepared)
            self.assertEqual(gh.call_count, 3)


if __name__ == "__main__":
    unittest.main()
