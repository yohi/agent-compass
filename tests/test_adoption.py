import copy
import json
import unittest
from unittest.mock import patch

import adoption as a
import compass
import generator
import maintenance


class AdoptionTests(unittest.TestCase):
    def setUp(self):
        self.s, self.t, self.p = compass.load_registry()
        self.g = generator.load_generation(self.t, self.p)
        self.audit = compass.read_json(compass.ROOT / "registry/audit.json")
        self.source = self.s["agents-md"]
        self.content = "The official document provides project setup guidance and test commands."
        row = maintenance.observe(maintenance.empty_state(), self.source, self.content, "2026-11-27")
        self.item = {"action": "add", "practice_id": "", "target": "common",
                     "category": "persistent-instructions", "status": "candidate",
                     "en": "Fixture guidance for adoption.", "ja": "採択検証用の指針。",
                     "scope": "Test fixture only.", "reason": "Fixture reason.",
                     "evidence_quote": "project setup guidance"}
        self.report = self.make_report(row, [self.item])
        self.row = row
        self.selected = [{"index": 1, "status": "recommended", "placement": "author-guidance"}]

    def make_report(self, row, items):
        r = maintenance.validate_proposals({"proposals": items}, self.source, row, self.p,
                    self.content, maintenance.config(), "gemini-3.8-flash", False)
        r["base_commit"] = "a"*40
        return r

    def plan(self, report=None, selected=None, content=None):
        return a.plan(self.report if report is None else report,
                      self.selected if selected is None else selected,
                      self.s, self.t, self.p, self.g, self.audit,
                      self.content if content is None else content, "2026-11-27")

    def test_add_deterministic_selection_and_no_mutation(self):
        report = self.make_report(self.row, [self.item, {**self.item, "en": "Second fixture.", "ja": "別の指針。"}])
        before = copy.deepcopy((self.s, self.p, self.g, self.audit))
        files, receipt = self.plan(report)
        self.assertEqual((files, receipt), self.plan(report))
        self.assertEqual((self.s, self.p, self.g, self.audit), before)
        new_id = f"BP-{max(int(k[3:]) for k in self.p)+1:03d}"
        records = compass.index(json.loads(files["registry/practices.json"]))
        self.assertEqual(set(records) - set(self.p), {new_id})
        self.assertEqual(records[new_id]["local_eval"], "not_verified")
        self.assertEqual(records[new_id]["status"], "recommended")
        self.assertEqual(receipt["unselected"], [2])
        self.assertEqual(receipt["state"], "OWNER_SELECTED_PENDING_MERGE")
        self.assertNotIn("Second fixture.", files["docs/BEST_PRACTICES.md"])
        placement = json.loads(files["registry/generation.json"])["placements"][-1]
        self.assertEqual(placement, {"id": new_id, "placement": "author-guidance"})

    def test_source_and_existing_record_conflicts(self):
        with self.assertRaisesRegex(ValueError, "source_snapshot_changed"):
            self.plan(content=self.content + " Changed.")
        r = copy.deepcopy(self.report)
        r["proposals"][0]["evidence_locator"]["quote_sha256"] = "0"*64
        with self.assertRaisesRegex(ValueError, "evidence_mismatch"):
            self.plan(r)
        r = self.make_report(self.row, [{**self.item, "action": "amend", "practice_id": "BP-001",
                                         "status": "recommended"}])
        self.p["BP-001"]["en"] += " Concurrent edit."
        with self.assertRaisesRegex(ValueError, "proposal_or_existing_record_changed"):
            self.plan(r)

    def test_retirement_preserves_prior_text_and_drops_placement(self):
        r = self.make_report(self.row, [{**self.item, "action": "deprecate", "practice_id": "BP-001",
                                         "status": "deprecated"}])
        files, receipt = self.plan(r, [{"index": 1, "status": "deprecated", "placement": "none"}])
        records = compass.index(json.loads(files["registry/practices.json"]))
        self.assertEqual(records["BP-001"]["en"], self.p["BP-001"]["en"])
        self.assertEqual(records["BP-001"]["evidence"], self.p["BP-001"]["evidence"])
        self.assertEqual(records["BP-001"]["status"], "deprecated")
        self.assertFalse(any(x["id"] == "BP-001" for x in json.loads(files["registry/generation.json"])["placements"]))
        self.assertEqual(receipt["selected"][0]["action"], "deprecate")
        with self.assertRaises(ValueError):
            self.plan(r, self.selected)

    def test_invalid_decisions_and_runtime_placement(self):
        for d in ([self.selected[0], self.selected[0]], [{"index": True, "status": "recommended", "placement": "none"}],
                  [{"index": 1, "status": "candidate", "placement": "instruction"}],
                  [{"index": 1, "status": "recommended", "placement": "configuration"}],
                  [{"index": 1, "status": "recommended", "placement": "author-guidance", "extra": "x"}]):
            with self.subTest(d=d), self.assertRaises(ValueError):
                a.decisions(json.dumps(d), 2)
        with self.assertRaises(ValueError):
            a.decisions('[{"index":1,"index":2,"status":"recommended","placement":"author-guidance"}]', 2)
        r = self.make_report(self.row, [{**self.item, "category": "reasoning"}])
        with self.assertRaisesRegex(ValueError, "runtime_as_instruction"):
            self.plan(r, [{"index": 1, "status": "recommended", "placement": "instruction",
                           "instruction": {"en": "Fixture", "ja": "指針"}}])

    def test_owner_and_head_guards(self):
        with patch.object(a, "gh") as gh:
            for actor, trigger, reviewed in [("other", "yohi", True), ("yohi", "other", True),
                                               ("yohi", "yohi", False)]:
                with self.assertRaises(ValueError):
                    a.run(a.REPO, "a"*40, 4, "b"*40, "[]", "yohi", actor, trigger, reviewed)
            gh.assert_not_called()
        with patch.object(a, "gh", return_value={"state": "open", "draft": True,
                "head": {"sha": "c"*40, "repo": {"full_name": a.REPO}},
                "base": {"ref": "master", "repo": {"full_name": a.REPO}}}):
            with self.assertRaisesRegex(ValueError, "pr_head_or_scope_changed"):
                a.get_pr("repos/"+a.REPO, 4, "b"*40)

    def test_no_write_when_validation_fails(self):
        with patch.object(a, "current_ref", return_value="a"*40), \
                patch.object(a, "get_pr", return_value={}), \
                patch.object(a, "get_candidate", return_value=(self.report, a.proposal_path(self.report),
                                                               json.dumps(self.report))), \
                patch.object(compass, "fetch_document", return_value=(self.content, "text", self.source["url"])), \
                patch.object(a, "validate_build", side_effect=ValueError("fixture_failure")), \
                patch.object(a, "gh") as gh:
            with self.assertRaisesRegex(ValueError, "fixture_failure"):
                a.run(a.REPO, "a"*40, 4, "b"*40, json.dumps(self.selected), "yohi", "yohi", "yohi", True)
            gh.assert_not_called()


if __name__ == "__main__":
    unittest.main()
