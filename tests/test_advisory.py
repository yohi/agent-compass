import copy
from contextlib import redirect_stdout
import io
import subprocess
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

import adoption
import advisory as a
import compass
import generator
import maintenance


class AdvisoryTests(unittest.TestCase):
    def setUp(self):
        self.c = a.config()
        self.head = "a"*40
        self.master = "b"*40
        self.day = lambda: "2026-11-27"
        self.ledger = SimpleNamespace(state=a.empty_state(self.day()), save=lambda: None)
        self.s, self.t, self.p = compass.load_registry()
        self.g = generator.load_generation(self.t, self.p)
        self.audit = compass.read_json(compass.ROOT / "registry/audit.json")
        self.registries = (self.s, self.t, self.p, self.g, self.audit)
        source = self.s["agents-md"]
        self.content = "The official document provides project setup guidance and test commands."
        row = maintenance.observe(maintenance.empty_state(), source, self.content, self.day())
        item = {"action": "add", "practice_id": "", "target": "common",
                "category": "persistent-instructions", "status": "candidate",
                "en": "Fixture guidance.", "ja": "検証用の指針。", "scope": "Fixture only.",
                "reason": "Fixture reason.", "evidence_quote": "project setup guidance"}
        self.report = maintenance.validate_proposals({"proposals": [item]}, source, row,
            self.p, self.content, maintenance.config(), "gemini-3.8-flash", False)
        self.report["base_commit"] = self.master
        self.decision = {"index": 1, "status": "recommended", "placement": "author-guidance"}
        self.answer = {"items": [{"index": 1, "verdict": "ADOPT", "reason": "根拠が一致。",
                                  "decision": self.decision}]}

    def test_provider_gates_and_price_guard(self):
        env = {"NVIDIA_API_KEY": "fake", "NVIDIA_FREE_TIER_CONFIRMED": "true",
               "NVIDIA_PROTOTYPE_USE_CONFIRMED": "true", "OPENROUTER_API_KEY": "fake",
               "OPENROUTER_FREE_TIER_CONFIRMED": "true", "GROQ_API_KEY": "fake"}
        self.assertEqual([r["provider"] for r in a.enabled_providers(self.c, env, "schedule")], ["openrouter"])
        self.assertEqual([r["provider"] for r in a.enabled_providers(self.c, env, "workflow_dispatch")],
                         ["nvidia", "nvidia", "openrouter"])
        row = self.c["providers"][2]
        payload = a.payload_for(row, "fixture")
        self.assertTrue(row["model"].endswith(":free"))
        self.assertFalse(payload["provider"]["allow_fallbacks"])
        self.assertTrue(all(v == 0 for v in payload["provider"]["max_price"].values()))
        with patch.object(a, "http_json", return_value={"data": [{"id": row["model"],
                          "pricing": {"prompt": "0", "completion": "0"}}]}):
            self.assertTrue(a.openrouter_free(row["model"], "fake"))
        with patch.object(a, "http_json", return_value={"data": [{"id": row["model"],
                          "pricing": {"prompt": "0", "completion": "0.01"}}]}):
            self.assertFalse(a.openrouter_free(row["model"], "fake"))

    def test_reserve_and_reset(self):
        c = {**self.c, "daily_limit": 2, "monthly_limit": 3}
        self.assertTrue(a.reserve(self.ledger, self.head, "nvidia", c, self.day, lambda: 100, lambda _: None))
        self.assertTrue(a.reserve(self.ledger, self.head, "groq", c, self.day, lambda: 120, lambda _: None))
        self.assertFalse(a.reserve(self.ledger, self.head, "groq", c, self.day, lambda: 140, lambda _: None))
        self.assertEqual(self.ledger.state["attempted"], [self.head])
        a.roll(self.ledger.state, "2026-11-28")
        self.assertEqual((self.ledger.state["daily"], self.ledger.state["monthly"]), (0, 2))
        self.assertTrue(a.reserve(self.ledger, self.head, "groq", c, lambda: "2026-11-28",
                                  lambda: 140, lambda _: None))
        self.assertFalse(a.reserve(self.ledger, self.head, "groq", c, lambda: "2026-11-29",
                                   lambda: 160, lambda _: None))
        a.roll(self.ledger.state, "2026-12-01")
        self.assertEqual(self.ledger.state["monthly"], 0)

    def test_durable_reservation_failure(self):
        def fail():
            raise RuntimeError("save failed")
        self.ledger.save = fail
        with self.assertRaises(RuntimeError):
            a.reserve(self.ledger, self.head, "groq", self.c, self.day, lambda: 100, lambda _: None)

    def validate(self, answer):
        return a.validate_answer(answer, self.report, *self.registries, self.content)

    def test_valid_answer_and_no_mutation(self):
        before = copy.deepcopy(self.registries)
        result = self.validate(self.answer)
        self.assertEqual(result["verdict"], "ADOPT")
        self.assertEqual(result["decisions"], [self.decision])
        self.assertEqual(self.registries, before)
        for verdict in ("REJECT", "DEFER"):
            result = self.validate({"items": [{"index": 1, "verdict": verdict, "reason": "fixture", "decision": None}]})
            self.assertEqual(result["verdict"], verdict)
            self.assertEqual(result["decisions"], [])

    def test_invalid_answer_rejected(self):
        for item in ({**self.answer["items"][0], "index": True},
                     {**self.answer["items"][0], "verdict": "REJECT"},
                     {**self.answer["items"][0], "decision": {**self.decision, "status": "candidate"}},
                     {**self.answer["items"][0], "decision": {**self.decision, "placement": "none"}}):
            with self.subTest(item=item), self.assertRaises(ValueError):
                self.validate({"items": [item]})
        with self.assertRaises(ValueError):
            self.validate({"items": []})

    def test_prepare_rejects_changed_source(self):
        with patch.object(compass, "fetch_document", return_value=(self.content + " changed", "text", "unused")):
            with self.assertRaises(ValueError):
                a.prepare(self.report, self.s, self.t, self.p, self.g, self.c)

    def test_model_identity_and_incomplete_response(self):
        row = self.c["providers"][0]
        value = {"model": row["model"], "choices": [{"finish_reason": "stop", "message":
                 {"content": json.dumps(self.answer)}}]}
        with patch.object(a, "http_json", return_value=value):
            self.assertEqual(a.call_model(row, "fake", "fixture"), self.answer)
        for changed in ({**value, "model": "other"}, {**value, "choices": [{"finish_reason": "length"}]}):
            with patch.object(a, "http_json", return_value=changed), self.assertRaises(a.InvalidAnswer):
                a.call_model(row, "fake", "fixture")

    def test_safe_comment(self):
        result = self.validate(self.answer)
        result["items"][0]["reason"] = "<script> @all [x](https://evil.invalid) " + chr(96)*3
        body = a.comment_body(self.head, self.master, self.report, result, self.c["providers"][0])
        self.assertNotIn("<script>", body)
        self.assertNotIn("@all", body)
        self.assertNotIn("[x](", body)
        self.assertIn("Advisory only", body)
        self.assertIn("agent-compass-advisory-result-v1:" + self.head, body)

    def test_ambiguous_comment_write_stops(self):
        result = self.validate(self.answer)
        with patch.object(adoption, "current_ref", return_value=self.master), \
                patch.object(adoption, "get_pr"), \
                patch.object(a, "already_commented", return_value=False), \
                patch.object(compass, "gh", side_effect=ValueError("bad github reply")):
            with self.assertRaises(a.PersistenceError):
                a.post_result("repos/"+a.REPO, 4, self.head, self.master,
                              self.report, result, self.c["providers"][0])

    def test_safe_diagnostics_never_emit_exception_payload(self):
        secret = "SENSITIVE-API-KEY-AND-RESPONSE"
        cases = [
            (ValueError(secret), "validation_error"),
            (a.InvalidAnswer("model_identity_mismatch"), "model_identity_mismatch"),
            (a.InvalidAnswer(secret), "invalid_answer"),
            (a.PersistenceError("comment_write_failed"), "comment_write_failed"),
            (subprocess.CalledProcessError(1, ["gh", secret], stderr=secret + " (HTTP 403)"), "github_http_403"),
            (subprocess.CalledProcessError(1, ["gh", secret], stderr=secret), "github_command_failed"),
            (subprocess.TimeoutExpired(["gh", secret], 60), "github_timeout"),
            (HTTPError("https://example.invalid/" + secret, 503, secret, None, None), "http_503"),
            (RuntimeError(secret), "unexpected_error"),
        ]
        for exc, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(a.diagnostic(exc), expected)
                output = io.StringIO()
                with redirect_stdout(output), self.assertRaises(type(exc)):
                    with a.stage("test_stage", 4, self.c["providers"][0]):
                        raise exc
                log = output.getvalue()
                self.assertIn("stage=test_stage pr=4 provider=nvidia", log)
                self.assertIn("code=" + expected, log)
                self.assertNotIn(secret, log)

    def test_response_json_diagnostic_preserved(self):
        row = self.c["providers"][0]
        value = {"model": row["model"], "choices": [{"finish_reason": "stop", "message":
                 {"content": "private invalid response"}}]}
        with patch.object(a, "http_json", return_value=value), self.assertRaises(a.InvalidAnswer) as cm:
            a.call_model(row, "fake", "fixture")
        self.assertEqual(a.diagnostic(cm.exception), "response_json")

    def test_publish_stage_distinguishes_github_failure(self):
        result = self.validate(self.answer)
        err = subprocess.CalledProcessError(1, ["gh", "SECRET"], stderr="private detail (HTTP 403)")
        output = io.StringIO()
        with redirect_stdout(output), patch.object(adoption, "current_ref", return_value=self.master), \
                patch.object(adoption, "get_pr"), \
                patch.object(a, "already_commented", return_value=False), \
                patch.object(compass, "gh", side_effect=err):
            with self.assertRaises(a.PersistenceError):
                a.post_result("repos/"+a.REPO, 4, self.head, self.master,
                              self.report, result, self.c["providers"][0])
        log = output.getvalue()
        self.assertIn("ok stage=publish_master_check", log)
        self.assertIn("ok stage=publish_pr_head_check", log)
        self.assertIn("failed stage=publish_comment_write", log)
        self.assertIn("code=github_http_403", log)
        self.assertNotIn("private detail", log)
        self.assertNotIn("SECRET", log)

    def test_retry_authorization_requires_owner_dispatch_and_single_pr(self):
        env = {"ADVISORY_RETRY_FAILED": "true", "ADVISORY_PR": "4",
               "REPOSITORY_OWNER": "yohi", "GITHUB_ACTOR": "yohi", "TRIGGERING_ACTOR": "yohi"}
        self.assertTrue(a.retry_requested(env, "workflow_dispatch"))
        self.assertFalse(a.retry_requested({}, "schedule"))
        self.assertFalse(a.retry_requested({**env, "ADVISORY_RETRY_FAILED": "false"}, "schedule"))
        for overrides, event in (({}, "schedule"), ({"ADVISORY_PR": ""}, "workflow_dispatch"),
                                 ({"ADVISORY_PR": "4,5"}, "workflow_dispatch"),
                                 ({"GITHUB_ACTOR": "other"}, "workflow_dispatch"),
                                 ({"TRIGGERING_ACTOR": "other"}, "workflow_dispatch"),
                                 ({"REPOSITORY_OWNER": "other"}, "workflow_dispatch"),
                                 ({"ADVISORY_RETRY_FAILED": "yes"}, "workflow_dispatch")):
            with self.subTest(overrides=overrides, event=event), patch.object(compass, "gh") as gh:
                with self.assertRaises(ValueError):
                    a.run(a.REPO, self.master, {**env, **overrides}, event)
                gh.assert_not_called()

    def test_same_day_retry_preserves_reservations_and_checks_result(self):
        pr = {"number": 4, "head": {"sha": self.head}}
        rows = self.c["providers"][:1]
        env = {"NVIDIA_API_KEY": "fake"}
        def execute(retry, comments, daily=1, monthly=1, blocked=()):
            self.ledger.state = a.empty_state(self.day())
            self.ledger.state.update(attempted=[self.head], daily=daily, monthly=monthly,
                                     blocked=list(blocked))
            saved = []
            self.ledger.save = lambda: saved.append(copy.deepcopy(self.ledger.state))
            with patch.object(a, "utc_day", self.day), \
                    patch.object(a, "already_commented", side_effect=comments) as lookup, \
                    patch.object(adoption, "get_pr", return_value=pr), \
                    patch.object(adoption, "get_candidate", return_value=(self.report, "p", "raw")), \
                    patch.object(a, "prepare", return_value=(self.content, "fixture")), \
                    patch.object(adoption, "current_ref", return_value=self.master), \
                    patch.object(a, "call_model", return_value=self.answer) as call, \
                    patch.object(compass, "gh") as gh:
                result = a.review_one("repos/"+a.REPO, pr, self.master, self.ledger,
                                      self.c, rows, env, self.registries, retry_failed=retry)
                return result, call.call_count, lookup.call_count, gh.call_count, saved
        self.assertEqual(execute(False, []), ("SKIPPED", 0, 0, 0, []))
        self.assertEqual(execute(True, [True]), ("SKIPPED", 0, 1, 0, []))
        self.assertEqual(execute(True, [False, True]), ("SKIPPED", 0, 2, 0, []))
        result, calls, lookups, writes, saved = execute(True, [False, False, False])
        self.assertEqual((result, calls, lookups, writes), ("ADOPT", 1, 3, 1))
        self.assertEqual(len(saved), 1)
        self.assertEqual((saved[0]["daily"], saved[0]["monthly"]), (2, 2))
        self.assertEqual(saved[0]["attempted"], [self.head])
        for daily, monthly, blocked in ((10, 10, ()), (1, 300, ()), (1, 1, ("nvidia",))):
            self.assertEqual(execute(True, [False, False], daily, monthly, blocked),
                             ("DEFER", 0, 2, 0, []))

    def test_retry_comment_lookup_failure_prevents_inference(self):
        pr = {"number": 4, "head": {"sha": self.head}}
        self.ledger.state.update(attempted=[self.head], daily=1, monthly=1)
        with patch.object(a, "utc_day", self.day), \
                patch.object(a, "already_commented", side_effect=ValueError("invalid lookup")), \
                patch.object(a, "call_model") as call, patch.object(a, "reserve") as reserve:
            with self.assertRaises(ValueError):
                a.review_one("repos/"+a.REPO, pr, self.master, self.ledger, self.c,
                             self.c["providers"][:1], {"NVIDIA_API_KEY": "fake"},
                             self.registries, retry_failed=True)
            call.assert_not_called()
            reserve.assert_not_called()

    def test_disabled_no_io(self):
        with patch.object(compass, "gh") as gh:
            self.assertEqual(a.run(a.REPO, self.master, {}, "schedule"), 0)
            gh.assert_not_called()

    def test_fallback_only_transport_and_no_second_verdict(self):
        pr = {"number": 4, "head": {"sha": self.head}}
        rows = self.c["providers"][:2]
        env = {"NVIDIA_API_KEY": "fake"}
        fault = HTTPError("https://example.invalid", 503, "unavailable", None, None)
        def execute(effects):
            self.ledger.state = a.empty_state(self.day())
            with patch.object(a, "utc_day", self.day), \
                    patch.object(a, "already_commented", return_value=False), \
                    patch.object(adoption, "get_pr", return_value=pr), \
                    patch.object(adoption, "get_candidate", return_value=(self.report, "p", "raw")), \
                    patch.object(a, "prepare", return_value=(self.content, "fixture")), \
                    patch.object(a, "reserve", return_value=True), \
                    patch.object(adoption, "current_ref", return_value=self.master), \
                    patch.object(a, "call_model", side_effect=effects) as call, \
                    patch.object(compass, "gh") as gh:
                result = a.review_one("repos/"+a.REPO, pr, self.master, self.ledger,
                                      self.c, rows, env, self.registries)
                return result, call.call_count, gh.call_count
        self.assertEqual(execute([fault, self.answer]), ("ADOPT", 2, 1))
        self.assertEqual(execute([a.InvalidAnswer("bad"), self.answer]), ("DEFER", 1, 1))
        self.assertEqual(execute([{"items": [{"index": 1, "verdict": "REJECT", "reason": "fixture",
                                            "decision": None}]}, self.answer]), ("REJECT", 1, 1))


if __name__ == "__main__":
    unittest.main()
