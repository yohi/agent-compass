import json
import unittest
from unittest.mock import patch

import compass


class RegistryTests(unittest.TestCase):
    def test_registry_and_generated_doc(self):
        sources, targets, practices = compass.load_registry()
        self.assertGreaterEqual(len(sources), 20)
        self.assertEqual(compass.render(sources, targets, practices),
                         (compass.ROOT / "docs/BEST_PRACTICES.md").read_text(encoding="utf-8"))

    def test_duplicate_id(self):
        with self.assertRaises(ValueError):
            compass.index([{"id": "a"}, {"id": "a"}])

    def test_model_unknown(self):
        with self.assertRaises(ValueError):
            compass.main(["show", "--target", "unknown"])


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.sources = {"s": {"url": "https://example.org/docs"}}
        self.fp = compass.fingerprint("original content\n" * 10)

    def test_first_baseline_then_unchanged(self):
        state, events = compass.monitor(self.sources, {}, lambda s, h: self.fp)
        self.assertEqual(events, [{"id": "s", "event": "baseline"}])
        after, events = compass.monitor(self.sources, state, lambda s, h: self.fp)
        self.assertEqual(after, state)
        self.assertEqual(events, [])

    def test_change(self):
        before, _ = compass.monitor(self.sources, {}, lambda s, h: self.fp)
        after, events = compass.monitor(self.sources, before,
                                        lambda s, h: compass.fingerprint("new content\n" * 10))
        self.assertEqual(events[0]["event"], "changed")
        self.assertNotEqual(before, after)

    def test_error_preserves_baseline_and_recovers(self):
        before, _ = compass.monitor(self.sources, {}, lambda s, h: self.fp)

        def failure(s, h):
            raise OSError("untrusted content must not be persisted")
        state, events = compass.monitor(self.sources, before, failure)
        self.assertEqual(state["s"]["fingerprint"], self.fp)
        self.assertEqual(events[0]["event"], "fetch_error")
        self.assertNotIn("untrusted", json.dumps(state))
        _, repeated = compass.monitor(self.sources, state, failure)
        self.assertEqual(repeated, [])
        _, recovered = compass.monitor(self.sources, state, lambda s, h: self.fp)
        self.assertEqual(recovered[0]["event"], "recovered")

    def test_changed_url_resets_baseline(self):
        before, _ = compass.monitor(self.sources, {}, lambda s, h: self.fp)
        new = {"s": {"url": "https://example.org/other"}}
        _, events = compass.monitor(new, before, lambda s, h: self.fp)
        self.assertEqual(events[0]["event"], "baseline")

    def test_removed(self):
        before, _ = compass.monitor(self.sources, {}, lambda s, h: self.fp)
        _, events = compass.monitor({}, before)
        self.assertEqual(events, [{"id": "s", "event": "removed"}])

    def test_issue_state_roundtrip(self):
        state, _ = compass.monitor(self.sources, {}, lambda s, h: self.fp)
        body = "report\n" + compass.MARKER + json.dumps(state) + "\n-->"
        self.assertEqual(compass.issue_state(body), state)
        with self.assertRaises(ValueError):
            compass.issue_state("missing")

    def test_unchanged_github_does_not_write(self):
        state, _ = compass.monitor(self.sources, {}, lambda s, h: self.fp)
        issue = {"title": compass.ISSUE_TITLE, "user": {"login": "github-actions[bot]"},
                 "number": 1, "body": compass.MARKER + json.dumps(state) + "\n-->"}
        with patch.object(compass, "gh", return_value=[[issue]]) as gh, \
                patch.object(compass, "monitor", return_value=(state, [])):
            self.assertEqual(compass.github_monitor("owner/repo", self.sources), 0)
            self.assertEqual(gh.call_count, 1)

    def test_failed_github_first_fetch_reports_error(self):
        state = {"s": {"url": self.sources["s"]["url"], "status": "error",
                       "fingerprint": None, "error": "OSError"}}
        with patch.object(compass, "gh", side_effect=[[[]], {}]) as gh, \
                patch.object(compass, "monitor", return_value=(state, [])):
            self.assertEqual(compass.github_monitor("owner/repo", self.sources), 1)
            self.assertEqual(gh.call_count, 2)


class SafetyTests(unittest.TestCase):
    def test_normalization_ignores_nav_script(self):
        content = "A useful instruction. " * 10
        html = f"<html><body><nav>noise</nav><main><p>{content}</p><script>secret</script></main></body></html>"
        result = compass.normalize(html, "html")
        self.assertNotIn("noise", result)
        self.assertNotIn("secret", result)
        self.assertEqual(result, content.strip())

    def test_empty_source(self):
        with self.assertRaises(ValueError):
            compass.normalize("<html><body>404</body></html>", "html")

    def test_unsafe_redirect(self):
        for url in ("http://example.org/", "https://evil.test/", "https://user@example.org/",
                    "https://example.org:444/", "https://127.0.0.1/"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                compass.safe_url(url, {"example.org"})

    def test_bounded_fingerprint(self):
        fp = compass.fingerprint("\n".join(str(i) for i in range(10000)))
        self.assertEqual(len(fp["chunks"]), 24)
        self.assertNotIn("9999", json.dumps(fp))


if __name__ == "__main__":
    unittest.main()
