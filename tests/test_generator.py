import contextlib
import copy
import io
from pathlib import Path
import tempfile
import unittest

import compass
import generator


class GeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources, cls.targets, cls.practices = compass.load_registry()
        cls.data = generator.load_generation(cls.targets, cls.practices)

    def build(self, harness="opencode", model="kimi-k3", framework=None, language="en",
              practices=None):
        return generator.generate(self.sources, self.targets, practices or self.practices,
                                  self.data, harness, model, framework, language)

    def test_model_api_not_in_agents(self):
        bundle = self.build(framework="superpowers")
        draft = bundle["AGENTS.draft.md"]
        self.assertIn("Superpowers", draft)
        self.assertNotIn("reasoning_effort", draft)
        self.assertNotIn("reasoning_content", draft)
        self.assertIn("reasoning_effort", bundle["CONFIGURATION.md"])
        self.assertIn("BP-039", bundle["EVIDENCE.md"])
        self.assertIn("BP-040", bundle["CONFIGURATION.md"])
        self.assertNotIn("BP-025", bundle["EVIDENCE.md"])

    def test_exact_model_scope(self):
        bundle = self.build("codex", "gpt-6.2-astra")
        evidence = bundle["EVIDENCE.md"]
        self.assertIn("BP-020", evidence)
        self.assertNotIn("BP-023", evidence)
        self.assertNotIn("BP-019", evidence)
        self.assertIn("decisions reserved for the user", bundle["AGENTS.draft.md"])

    def test_unknown_model_guidance_explicit(self):
        bundle = self.build(model="kimi-k2.8-preview")
        self.assertIn("No selected model-specific standing instructions", bundle["EVIDENCE.md"])
        self.assertNotIn("BP-039", bundle["EVIDENCE.md"])

    def test_invalid_selection(self):
        for harness, model, framework in [("kimi", "kimi-k3", None),
                                          ("codex", "fake-model", None),
                                          ("codex", "opencode", None),
                                          ("codex", None, "common")]:
            with self.subTest(harness=harness, model=model, framework=framework):
                with self.assertRaises(ValueError):
                    self.build(harness, model, framework)

    def test_framework_opt_in(self):
        self.assertNotIn("BP-051", self.build()["EVIDENCE.md"])
        self.assertIn("BP-051", self.build(framework="superpowers")["EVIDENCE.md"])

    def test_inactive_or_contradicted_excluded(self):
        practices = copy.deepcopy(self.practices)
        practices["BP-020"]["status"] = "deprecated"
        practices["BP-021"]["local_eval"] = "contradicted"
        result = self.build("codex", "gpt-6.2-astra", practices=practices)
        self.assertNotIn("decisions reserved for the user", result["AGENTS.draft.md"])
        self.assertNotIn("verify the requested behavior", result["AGENTS.draft.md"])
        self.assertIn("BP-020 — excluded-status-or-evaluation", result["EVIDENCE.md"])

    def test_new_unclassified_practice_not_injected(self):
        practices = copy.deepcopy(self.practices)
        practices["BP-999"] = {**practices["BP-020"], "id": "BP-999",
                               "en": "Unclassified instruction must not be injected."}
        result = self.build("codex", "gpt-6.2-astra", practices=practices)
        self.assertNotIn("Unclassified instruction", result["AGENTS.draft.md"])
        self.assertIn("BP-999 — unclassified", result["EVIDENCE.md"])

    def test_configuration_only_and_author_guidance(self):
        bundle = self.build("opencode", "kimi-k3")
        self.assertNotIn("policy allow", bundle["AGENTS.draft.md"])
        self.assertIn("policy allow", bundle["CONFIGURATION.md"])
        self.assertIn("BP-009 — author-guidance", bundle["EVIDENCE.md"])
        self.assertNotIn("## Model-specific", bundle["AGENTS.draft.md"])

    def test_language_and_reproducibility(self):
        bundle = self.build(language="ja")
        self.assertIn("生成候補・未適用", bundle["AGENTS.draft.md"])
        self.assertEqual(bundle, self.build(language="ja"))
        self.assertIn("Registry SHA-256:", bundle["EVIDENCE.md"])

    def test_native_entry_point_not_installed(self):
        bundle = self.build("claude-code", "claude-sonnet-5.5")
        self.assertIn("CLAUDE.md", bundle["EVIDENCE.md"])
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            original = project / "AGENTS.md"
            original.write_text("existing", encoding="utf-8")
            directory = project / "draft"
            generator.write_bundle(directory, bundle)
            self.assertEqual(original.read_text(encoding="utf-8"), "existing")
            self.assertEqual(set(p.name for p in directory.iterdir()), set(bundle))
            with self.assertRaises(FileExistsError):
                generator.write_bundle(directory, bundle)
            with self.assertRaises(FileExistsError):
                generator.write_bundle(project, bundle)

    def test_cli_stdout_and_bundle(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(compass.main(["generate", "--harness", "opencode", "--model", "kimi-k3"]), 0)
        self.assertIn("AGENTS.md", out.getvalue())
        self.assertNotIn("reasoning_effort", out.getvalue())
        self.assertIn("--output-dir", err.getvalue())
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "new"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(compass.main(["generate", "--harness", "opencode",
                                               "--model", "kimi-k3", "--output-dir", str(dest)]), 0)
            self.assertTrue((dest / "EVIDENCE.md").is_file())


if __name__ == "__main__":
    unittest.main()
