import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import auditor
import compass
import generator


class AuditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources, cls.targets, cls.practices = compass.load_registry()
        cls.generation = generator.load_generation(cls.targets, cls.practices)
        cls.rules = auditor.load_rules(cls.practices)

    def check(self, text, harness="opencode", model="kimi-k3", framework=None, practices=None):
        raw = text.encode()
        return auditor.audit(text, hashlib.sha256(raw).hexdigest(), len(raw),
                             self.sources, self.targets, practices or self.practices,
                             self.generation, self.rules, harness, model, framework)

    def test_observations_and_scoped_evidence(self):
        report = self.check("- Set reasoning_effort = max\n- Preserve credentials securely.\n"
                            "- Preserve credentials securely.\n- Always use independent review.\n")
        findings = {f["kind"]: f for f in report["findings"]}
        self.assertEqual(findings["duplicate"]["lines"], [2, 3])
        self.assertTrue(findings["duplicate"]["protected_context"])
        self.assertEqual(findings["runtime-setting"]["lines"], [1])
        self.assertIn("BP-039", [e["practice"] for e in findings["runtime-setting"]["evidence"]])
        self.assertNotIn("BP-025", [e["practice"] for e in findings["runtime-setting"]["evidence"]])
        self.assertEqual(findings["repeated-review"]["evidence"], [])
        self.assertEqual(report["verdict"], "NOT_ASSESSED")
        self.assertNotIn("Preserve credentials securely.", json.dumps(report))

    def test_japanese_and_review_boundary(self):
        report = self.check("- 毎回独立レビューを行う。\n- すべての操作について承認を得る。\n"
                            "- 本番環境への変更は必ず承認を得る。\n",
                            "claude-code", "claude-fable-5.2")
        findings = {f["kind"]: f for f in report["findings"]}
        self.assertEqual(findings["approval-checkpoint"]["lines"], [2])
        self.assertTrue(findings["approval-checkpoint"]["protected_context"])
        self.assertIn("BP-033", [e["practice"] for e in findings["approval-checkpoint"]["evidence"]])
        self.assertIn("承認", auditor.render(report))

    def test_skip_examples_and_comments(self):
        text = ("# Example\n" + chr(96)*3 + "python\nreasoning_effort = max\n" + chr(96)*3 +
                "\n> Always use independent review.\n<!-- reasoning_content -->\n"
                "    temperature = 1\n- Run tests.\n")
        report = self.check(text)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["input"]["scanned_lines"], 2)

    def test_model_identifiers_not_substrings(self):
        report = self.check("- Migration from kimi-k2.7-code to kimi-k3.\n"
                            "- kimi-k3.1 is not a registered ID in this fixture.\n")
        hits = [f for f in report["findings"] if f["kind"] == "other-model"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["lines"], [1])
        self.assertIn("kimi-k2.7-code", hits[0]["observation"])

    def test_no_absence_inference_and_exact_coverage(self):
        text = "- " + next(r["instruction"]["ja"] for r in self.generation["placements"]
                           if r["id"] == "BP-020") + "\n"
        report = self.check(text, "codex", "gpt-6.2-astra")
        coverage = {r["practice"]: r["literal_match"] for r in report["literal_coverage"]}
        self.assertTrue(coverage["BP-020"])
        self.assertFalse(coverage["BP-021"])
        self.assertEqual(report["findings"], [])
        self.assertIn("非一致は欠落を意味しない", auditor.render(report))

    def test_inactive_evidence_excluded(self):
        practices = copy.deepcopy(self.practices)
        practices["BP-039"]["status"] = "deprecated"
        report = self.check("- reasoning_effort = max", practices=practices)
        self.assertNotIn("BP-039", [e["practice"] for e in report["findings"][0]["evidence"]])

    def test_local_length_threshold_not_vendor_limit(self):
        report = self.check("\n".join("# Section" for _ in range(201)), "codex", "gpt-6.2-astra")
        self.assertEqual(report["findings"][0]["kind"], "size")
        self.assertEqual(report["verdict"], "NOT_ASSESSED")
        self.assertIn("local triage threshold", report["findings"][0]["observation"])

    def test_reread_only_scoped_evidence(self):
        text = "- Always re-read all files before every edit."
        report = self.check(text, "codex", "gpt-6-astra")
        self.assertEqual(report["findings"][0]["kind"], "unconditional-reread")
        self.assertIn("BP-019", [e["practice"] for e in report["findings"][0]["evidence"]])
        other = self.check(text, "codex", "gpt-6.2-astra")
        self.assertEqual(other["findings"][0]["evidence"], [])

    def test_input_and_exclusive_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "AGENTS.md"
            raw = b"\xef\xbb\xbf- Run tests.\r\n"
            path.write_bytes(raw)
            text, sha, count = auditor.read_input(path)
            self.assertEqual(sha, hashlib.sha256(raw).hexdigest())
            self.assertEqual(count, len(raw))
            self.assertTrue(text.startswith("-"))
            with self.assertRaises(FileExistsError):
                auditor.write_report(path, "must not overwrite")
            self.assertEqual(path.read_bytes(), raw)
            link = root / "link"
            link.symlink_to(path)
            with self.assertRaises(ValueError):
                auditor.read_input(link)
            with self.assertRaises(FileExistsError):
                auditor.write_report(link, "must not overwrite")
            path.write_bytes(b"x" * (auditor.MAX_INPUT_BYTES + 1))
            with self.assertRaises(ValueError):
                auditor.read_input(path)

    def test_cli_json_no_raw_text_and_no_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AGENTS.md"
            raw = "- Set reasoning_effort = max # PRIVATE_PROJECT_NAME\n"
            path.write_text(raw)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                result = compass.main(["audit", str(path), "--harness", "opencode",
                                       "--model", "kimi-k3", "--format", "json"])
            report = json.loads(out.getvalue())
            self.assertEqual(result, 0)
            self.assertEqual(report["verdict"], "NOT_ASSESSED")
            self.assertNotIn("PRIVATE_PROJECT_NAME", out.getvalue())
            self.assertEqual(path.read_text(), raw)
            self.assertEqual(list(Path(tmp).iterdir()), [path])

    def test_unknown_profile_rejected(self):
        with self.assertRaises(ValueError):
            self.check("Hello", "codex", "unknown-model")


if __name__ == "__main__":
    unittest.main()
