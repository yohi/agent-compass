import copy
import hashlib
import json
import unittest
from unittest.mock import patch

import compass
import maintenance as m
import check_portal as health


class MaintenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = m.config()
        cls.sources, _, cls.practices = compass.load_registry()
        cls.source = cls.sources["agents-md"]

    def test_observe_latest_and_pending(self):
        s = m.empty_state()
        a = m.observe(s, self.source, "initial", "2026-11-27")
        self.assertEqual(a["origin"], "initial")
        self.assertIs(m.observe(s, self.source, "initial", "2026-11-28"), a)
        b = m.observe(s, self.source, "next", "2026-11-28")
        self.assertEqual(b["superseded"], 1)
        self.assertEqual(b["origin"], "changed")
        b["stage"], b["comment"] = "ready", 12
        b["proposal_identity"], b["next_cursor"], b["document_end"] = m.chunk_identity(b), 4, True
        self.assertIs(m.observe(s, self.source, "later", "2026-11-28"), b)
        self.assertEqual(m.read_state(m.state_body(s)), s)

    def test_durable_budget_and_daily_reset(self):
        s = m.empty_state()
        c = copy.deepcopy(self.c)
        c["models"]["analyze"]["daily_limit"] = 1
        saved = []
        with patch.object(m, "pacific_day", return_value="2026-11-27"):
            self.assertEqual(m.reserve(s, "analyze", c, lambda: saved.append(copy.deepcopy(s)),
                                       now=lambda: 1000, sleep=lambda _: None), "gemini-3.8-flash")
            self.assertEqual(saved[0]["usage"]["gemini-3.8-flash"], 1)
            self.assertIsNone(m.reserve(s, "analyze", c, lambda: None, now=lambda: 1020))
        with patch.object(m, "pacific_day", return_value="2026-11-28"):
            self.assertEqual(m.reserve(s, "analyze", c, lambda: None, now=lambda: 2000),
                             "gemini-3.8-flash")
            self.assertEqual(s["usage"]["gemini-3.8-flash"], 1)

    def test_persistent_block_and_reset(self):
        s = m.empty_state()
        with patch.object(m, "pacific_day", return_value="2026-11-27"):
            m.reserve(s, "analyze", self.c, lambda: None, now=lambda: 1000)
            s["blocked"] = ["gemini-3.8-flash"]
            self.assertIsNone(m.reserve(s, "analyze", self.c, lambda: None, now=lambda: 1020))
        with patch.object(m, "pacific_day", return_value="2026-11-28"):
            self.assertEqual(m.reserve(s, "analyze", self.c, lambda: None, now=lambda: 2000),
                             "gemini-3.8-flash")
            self.assertEqual(s["blocked"], [])

    def test_reservation_failure_prevents_call(self):
        with patch.object(m, "pacific_day", return_value="2026-11-27"):
            with self.assertRaises(OSError):
                m.reserve(m.empty_state(), "classify", self.c,
                          lambda: (_ for _ in ()).throw(OSError("failed")), now=lambda: 1000)

    def test_validate_proposal_and_evidence(self):
        text = "A source sentence provides project setup guidance."
        row = m.observe(m.empty_state(), self.source, text, "2026-11-27")
        p = {"action": "amend", "practice_id": "BP-001", "target": "common",
             "category": "persistent-instructions", "status": "recommended", "en": "Use setup guidance.",
             "ja": "設定を記載する。", "scope": "Project instructions only.", "reason": "Clarify scope.",
             "evidence_quote": "project setup guidance"}
        value = {"proposals": [p]}
        result = m.validate_proposals(value, self.source, row, self.practices, text,
                                      self.c, "gemini-3.8-flash", False)
        self.assertEqual(result["adoption_status"], "UNADOPTED")
        self.assertNotIn("evidence_quote", json.dumps(result))
        self.assertEqual(result["proposals"][0]["proposed"]["local_eval"], "not_verified")
        for mutation in ({"evidence_quote": "fabricated quote"}, {"practice_id": "BP-025"},
                         {"target": "codex"}, {"action": "deprecate"}, {"local_eval": "supported"}):
            with self.assertRaises(ValueError):
                m.validate_proposals({"proposals": [{**p, **mutation}]}, self.source, row,
                                     self.practices, text, self.c, "gemini-3.8-flash", False)

    def test_partial_input_and_schema(self):
        text = "public guidance " * 20000
        row = m.observe(m.empty_state(), self.source, text, "2026-11-27")
        prompt, excerpt, truncated, end = m.make_prompt(self.source, text, row, self.practices, self.c, False)
        self.assertTrue(truncated)
        self.assertLess(len(prompt.encode()), 20000)
        self.assertTrue(text.startswith(excerpt))
        self.assertEqual(text[:end], excerpt)
        self.assertEqual(m.make_prompt(self.source, text, row, self.practices, self.c, True)[1], excerpt)
        first_identity = m.chunk_identity(row)
        m.finish_chunk(row, "no_proposal", end, False)
        self.assertEqual(row["stage"], "classify")
        self.assertNotEqual(first_identity, m.chunk_identity(row))
        _, excerpt2, partial2, end2 = m.make_prompt(self.source, text, row, self.practices, self.c, False)
        self.assertTrue(partial2)
        self.assertEqual(text[end:end2], excerpt2)
        self.assertGreater(end2, end)
        with self.assertRaises(ValueError):
            m.classify({"decision": "invented", "reason": "test"})
        raw = json.dumps({"candidates": [{"finishReason": "STOP", "content": {"parts": [
            {"thought": True, "text": "hidden"}, {"text": '{"proposals":[]}'}]}}]})
        self.assertEqual(m.parse_response(raw), {"proposals": []})
        with self.assertRaises(ValueError):
            m.parse_response(raw.replace("STOP", "MAX_TOKENS"))

    def test_missing_enablement_no_writes(self):
        with patch.object(m, "Ledger") as ledger, patch.object(m, "call_model") as api:
            self.assertEqual(m.run(m.REPO, "a"*40, "fake", False), 0)
            self.assertEqual(m.run(m.REPO, "a"*40, "", True), 0)
            ledger.assert_not_called()
            api.assert_not_called()

    def test_existing_pr_is_not_overwritten(self):
        report = {"source_id": "agents-md", "identity": "a"*64}
        with patch.object(compass, "gh", return_value=[{"number": 5}]) as gh:
            self.assertEqual(m.publish(m.REPO, report, "b"*40), 5)
            self.assertEqual(gh.call_count, 1)
        with self.assertRaises(ValueError):
            m.publish("other/repo", report, "b"*40)

    def test_portal_health(self):
        paths = ("llms.txt", "llms.ja.txt", "api/v1/targets.json", "knowledge/common.md",
                 "knowledge/harnesses/opencode.md", "knowledge/models/kimi-k3.md",
                 "skills/agent-compass/SKILL.md")
        files = {p: p.encode() for p in paths}
        manifest = {"schema_version": 1, "base_url": health.BASE, "registry_sha256": "a"*64,
                    "files": {p: {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
                              for p, raw in files.items()}}
        files["api/v1/manifest.json"] = json.dumps(manifest).encode()
        files[""] = b"Agent Compass ./app.js"
        self.assertEqual(health.verify(files.__getitem__), manifest)
        files["llms.txt"] = b"bad"
        with self.assertRaises(ValueError):
            health.verify(files.__getitem__)


if __name__ == "__main__":
    unittest.main()
