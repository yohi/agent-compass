import json
import unittest
from unittest.mock import patch

import compass
import discovery
import signals


class TopicTests(unittest.TestCase):
    def test_topic_change_and_legacy_baseline(self):
        old = signals.topic_signals("Use AGENTS.md\nRun tests")
        new = signals.topic_signals("Use AGENTS.md only where needed\nRun tests\nRemove old prompts")
        self.assertTrue(signals.validate_signals(new))
        self.assertIsNone(signals.signal_changes(None, new))
        topics = {t["topic"] for t in signals.signal_changes(old, new)}
        self.assertIn("instructions", topics)
        self.assertIn("migration", topics)
        self.assertNotIn("verification", topics)
        self.assertNotIn("Run tests", json.dumps(new))

    def test_monitor_proposal_and_legacy_migration(self):
        source = {"s": {"url": "https://example.org/docs", "target": "codex"}}
        old = compass.fingerprint("old prompts")
        new = {**compass.fingerprint("new prompts"), "topics": signals.topic_signals("new prompts")}
        state, _ = compass.monitor(source, {}, lambda s, h: old)
        after, events = compass.monitor(source, state, lambda s, h: new)
        self.assertIsNone(events[0]["topic_changes"])
        practices = {"BP-1": {"id": "BP-1", "evidence": ["s"]}}
        report = compass.summary(source, after, events, practices)
        self.assertIn("BP-1", report)
        self.assertIn("classification unknown", report)
        self.assertIn("Candidate only", report)
        same, ev = compass.monitor(source, after, lambda s, h: new)
        self.assertEqual(same, after)
        self.assertEqual(ev, [])

    def test_same_content_enrichment_is_not_change(self):
        sources = {"s": {"url": "https://example.org/docs"}}
        fp = compass.fingerprint("Use tests")
        state, _ = compass.monitor(sources, {}, lambda s, h: fp)
        enhanced = {**fp, "topics": signals.topic_signals("Use tests")}
        _, events = compass.monitor(sources, state, lambda s, h: enhanced)
        self.assertEqual(events, [])

    def test_no_topic_change_not_proven_irrelevant(self):
        event = {"id": "s", "before": "a", "after": "b", "topic_changes": []}
        report = "\n".join(signals.proposal_lines(event, {}, {"target": "codex"}))
        self.assertIn("relevance remains unknown", report)


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.index = {"id": "x", "target": "codex", "url": "https://example.org/models",
                      "format": "html", "prefixes": ["/models/"], "model_prefixes": ["gpt-"]}
        self.indexes = {"x": self.index}
        self.raw = ("<html><body><main>" + "Official model catalog. " * 10
                    + '<a href="/models/gpt-7?tracking=x">GPT-7</a>'
                    + '<a href="https://evil.test/models/gpt-8">external</a>'
                    + '<a href="/models/gpt-7#section">duplicate</a>'
                    + "</main></body></html>")

    def fetch(self, row, hosts):
        return self.raw, "html", row["url"]

    def test_safe_candidates_and_dedup(self):
        state, events = discovery.scan(self.indexes, {}, set(), self.fetch)
        self.assertEqual(events[0]["event"], "initial_inventory")
        self.assertEqual(events[0]["count"], 2)
        self.assertIn(("link", "https://example.org/models/gpt-7"), events[0]["candidates"])
        self.assertIn(("model-mention", "gpt-7"), events[0]["candidates"])
        self.assertNotIn("externalduplicate", json.dumps(events))
        self.assertNotIn("evil.test", json.dumps(events))
        self.assertNotIn("gpt-7", json.dumps(state))
        unchanged, events = discovery.scan(self.indexes, state, set(), self.fetch)
        self.assertEqual(unchanged, state)
        self.assertEqual(events, [])

    def test_new_candidate_and_recovery(self):
        state, _ = discovery.scan(self.indexes, {}, set(), self.fetch)

        def fail(row, hosts):
            raise OSError("remote body")
        failed, events = discovery.scan(self.indexes, state, set(), fail)
        self.assertEqual(failed["x"]["seen"], state["x"]["seen"])
        self.assertEqual(events[0]["event"], "fetch_error")
        self.raw = self.raw.replace("gpt-7", "gpt-9").replace("GPT-7", "GPT-9")
        _, events = discovery.scan(self.indexes, failed, set(), self.fetch)
        self.assertEqual(events[0]["event"], "discovered")
        self.assertEqual(events[0]["count"], 2)

    def test_reject_url_escapes(self):
        for url in ("https://evil.test/models/gpt-7", "https://u@example.org/models/gpt-7",
                    "/models/%2e%2e/gpt-7", "/models-other/gpt-7", "javascript:alert(1)"):
            self.assertIsNone(discovery.candidate_url(url, self.index["url"], self.index))

    def test_known_source_excluded(self):
        result = discovery.extract(self.raw, "html", self.index["url"], self.index,
                                   {"https://example.org/models/gpt-7"})
        self.assertEqual(list(result.values()), [("model-mention", "gpt-7")])

    def test_capacity_fails_closed(self):
        with patch.object(discovery, "MAX_SEEN", 1):
            with self.assertRaises(ValueError):
                discovery.scan(self.indexes, {}, set(), self.fetch)

    def test_read_state_and_no_write_on_repeat(self):
        state, _ = discovery.scan(self.indexes, {}, set(), self.fetch)
        issue = {"title": discovery.TITLE, "user": {"login": "github-actions[bot]"},
                 "number": 2, "body": discovery.MARKER + json.dumps(state) + "\n-->"}
        self.assertEqual(discovery.read_state(issue["body"]), state)
        with patch.object(compass, "gh", return_value=[[issue]]) as gh, \
                patch.object(discovery, "scan", return_value=(state, [])):
            self.assertEqual(discovery.github("owner/repo", self.indexes, set()), 0)
            self.assertEqual(gh.call_count, 1)

    def test_github_navigation_excluded(self):
        index = {**self.index, "url": "https://github.com/MoonshotAI",
                 "prefixes": ["/MoonshotAI/"]}
        self.assertEqual(discovery.candidate_url("/MoonshotAI/Kimi-K3", index["url"], index),
                         "https://github.com/MoonshotAI/Kimi-K3")
        for tail in ("forks", "issues", "pulls", "stargazers", "graphs/commit-activity"):
            self.assertIsNone(discovery.candidate_url("/MoonshotAI/Kimi-K3/" + tail,
                                                      index["url"], index))

    def test_legacy_migration_rearchives_current_and_preserves_missing(self):
        state, _ = discovery.scan(self.indexes, {}, set(), self.fetch)
        del state["x"]["archive_version"]
        state["x"]["seen"].append("a" * 24)
        migrated, events = discovery.scan(self.indexes, state, set(), self.fetch)
        self.assertEqual(events[0]["event"], "archive_migration")
        self.assertEqual(events[0]["count"], 2)
        self.assertEqual(events[0]["legacy_unrecovered"], 1)
        self.assertIn("a" * 24, migrated["x"]["seen"])
        _, repeated = discovery.scan(self.indexes, migrated, set(), self.fetch)
        self.assertEqual(repeated, [])

    def test_archive_all_candidates_beyond_summary_limit(self):
        candidates = [("link", f"https://example.org/models/gpt-{i}") for i in range(40)]
        event = {"id": "x", "event": "initial_inventory", "count": len(candidates),
                 "candidates": candidates}
        with patch.object(discovery, "COMMENT_LIMIT", 1000):
            comments = discovery.archive_comments(self.indexes, [event])
        self.assertGreater(len(comments), 1)
        self.assertTrue(all(len(c) <= 1000 for c in comments))
        for kind, value in candidates:
            self.assertEqual(sum(discovery.identity(kind, value) in c for c in comments), 1)

    def test_archive_failure_does_not_advance_issue_state(self):
        state, events = discovery.scan(self.indexes, {}, set(), self.fetch)
        issue = {"title": discovery.TITLE, "user": {"login": "github-actions[bot]"},
                 "number": 2, "body": discovery.MARKER + "{}\n-->"}
        with patch.object(compass, "gh", side_effect=[[[issue]], OSError("archive failed")]) as gh, \
                patch.object(discovery, "scan", return_value=(state, events)):
            with self.assertRaises(OSError):
                discovery.github("owner/repo", self.indexes, set())
            self.assertEqual(gh.call_count, 2)
            self.assertNotIn("PATCH", str(gh.call_args_list))

    def test_safe_error_reasons(self):
        self.assertEqual(compass.error_reason(ValueError("unapproved HTTPS endpoint")),
                         "endpoint_not_allowed")
        self.assertEqual(compass.error_reason(ValueError("remote secret")), "invalid_response")
        self.assertEqual(compass.error_reason(TimeoutError()), "timeout")

    def test_text_index(self):
        raw = "Official reference " * 10 + "\n[guide](https://example.org/models/gpt-8)"
        result = discovery.extract(raw, "text", self.index["url"], self.index, set())
        self.assertIn(("link", "https://example.org/models/gpt-8"), result.values())


if __name__ == "__main__":
    unittest.main()
