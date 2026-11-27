import copy
import json
import unittest
from unittest.mock import patch

import compass
import discovery
import registration as r


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.s, self.t, self.p = compass.load_registry()
        self.idx = discovery.load_indexes(self.t)["google-models"]
        self.model = "gemini-fixture-999"
        self.url = "https://aistudio.google.com/docs/models/gemini-fixture-999"
        self.quote = self.model + " is available in preview"
        self.content = self.quote + ". Synthetic official source fixture for a bounded discovery registration test."
        self.candidates = {discovery.identity("model-mention", self.model): ("model-mention", self.model),
                           discovery.identity("link", self.url): ("link", self.url)}
        self.d = {"index": self.idx["id"], "candidate_kind": "model-mention", "candidate_value": self.model,
                  "target_id": self.model, "target_name": "Gemini Fixture 999", "source_id": "gemini-fixture-card",
                  "source_url": self.url, "source_kind": "official-docs", "source_format": "text",
                  "lifecycle": "preview", "evidence_quote": self.quote}

    def plan(self, d=None, content=None):
        return r.plan(r.parse_request(json.dumps(self.d if d is None else d)), self.idx, self.candidates,
                      self.content if content is None else content, self.s, self.t, self.p, "2026-11-27")

    def test_model_source_registration_preserves_registry_and_practices(self):
        before = copy.deepcopy((self.s, self.t, self.p))
        files, receipt = self.plan()
        self.assertEqual((files, receipt), self.plan())
        self.assertEqual((self.s, self.t, self.p), before)
        self.assertEqual(set(files), r.PATHS)
        t = compass.index(json.loads(files["registry/targets.json"]))
        s = compass.index(json.loads(files["registry/sources.json"]))
        self.assertEqual(t[self.model]["lifecycle"]["status"], "preview")
        self.assertEqual(t[self.model]["lifecycle"]["source_id"], self.d["source_id"])
        self.assertEqual(s[self.d["source_id"]]["target"], self.model)
        self.assertNotIn(self.quote, json.dumps(receipt))
        self.assertEqual(receipt["practice_extraction"], "AFTER_MERGE_EXISTING_MAINTENANCE")
        self.assertIn("Lifecycle (owner-reviewed snapshot): preview", files["docs/BEST_PRACTICES.md"])

    def test_reject_unobserved_or_mismatched_source(self):
        for update in ({"candidate_value": "gemini-other-999"}, {"source_url": "https://evil.invalid/model"},
                       {"source_url": "https://aistudio.google.com/docs/unobserved"},
                       {"target_id": "gemini-other-999"}, {"evidence_quote": "invented quote"}):
            with self.subTest(update=update), self.assertRaises(ValueError):
                self.plan({**self.d, **update})
        with self.assertRaises(ValueError):
            self.plan(content="Other model only. " + self.quote.replace(self.model, "different-model"))
        with self.assertRaises(ValueError):
            self.plan({**self.d, "evidence_quote": "Synthetic official source fixture"})

    def test_existing_scope_and_source_conflict(self):
        d = {**self.d, "candidate_kind": "link", "candidate_value": self.url,
             "target_id": "gemini", "target_name": self.t["gemini"]["name"], "lifecycle": "unknown"}
        files, _ = self.plan(d)
        self.assertEqual(json.loads(files["registry/targets.json"]), list(self.t.values()))
        with self.assertRaises(ValueError):
            self.plan({**d, "target_id": "common", "target_name": self.t["common"]["name"]})
        with self.assertRaises(ValueError):
            self.plan({**d, "source_id": "agents-md"})
        self.s["duplicate-fixture"] = {"id": "duplicate-fixture", "url": self.url, "target": "gemini"}
        with self.assertRaises(ValueError):
            self.plan(d)

    def test_no_fetch_for_unobserved_source(self):
        index_text = self.model + " " + self.url + " " + "sample " * 30
        with patch.object(compass, "fetch_document", return_value=(index_text, "text", self.idx["url"])) as fetch:
            with self.assertRaises(ValueError):
                r.fetch_current(self.idx, {**self.d, "source_url": "https://evil.invalid/x"}, self.t)
            self.assertEqual(fetch.call_count, 1)

    def test_owner_guard_and_existing_pr(self):
        with patch.object(compass, "gh") as gh:
            with self.assertRaises(ValueError):
                r.run(r.REPO, "a"*40, json.dumps(self.d), "yohi", "other", "yohi", True)
            gh.assert_not_called()
        _, receipt = self.plan()
        with patch.object(compass, "gh", return_value=[{"number": 123}]) as gh:
            self.assertEqual(r.publish("repos/"+r.REPO, "a"*40, {}, receipt), 123)
            self.assertEqual(gh.call_count, 1)

    def test_lifecycle_not_erased_by_unknown(self):
        files, _ = self.plan()
        self.s = compass.index(json.loads(files["registry/sources.json"]))
        self.t = compass.index(json.loads(files["registry/targets.json"]))
        old = self.t[self.model]["lifecycle"]
        files, _ = self.plan({**self.d, "lifecycle": "unknown"})
        self.assertEqual(compass.index(json.loads(files["registry/targets.json"]))[self.model]["lifecycle"], old)


if __name__ == "__main__":
    unittest.main()
