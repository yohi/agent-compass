import copy
import hashlib
from pathlib import Path
import tempfile
import unittest

import pilot


class PilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = pilot.load_manifest()
        cls.registry = pilot.registry()

    def fixture(self):
        project = copy.deepcopy(self.manifest["projects"][0])
        case = copy.deepcopy(self.manifest["case"])
        raw = ("# Project\n- Preserve secrets.\n" + case["replace_before"] + "\n").encode()
        evidence = b"fixture evidence"
        project["blob"] = pilot.blob_sha(raw)
        case["evidence"]["blob"] = pilot.blob_sha(evidence)
        return project, case, raw, evidence

    def test_blob_and_variant(self):
        project, case, raw, _ = self.fixture()
        changed = pilot.variant(raw, case)
        self.assertEqual(changed, raw.replace(case["replace_before"].encode(),
                                              case["replace_after"].encode()))
        self.assertIn(b"Preserve secrets.", changed)
        self.assertIn(b"run all four commands fresh", changed)
        with self.assertRaises(ValueError):
            pilot.variant(b"no anchor", case)
        with self.assertRaises(ValueError):
            pilot.variant(raw + raw, case)

    def test_real_auditor_profile_and_no_replace_claim(self):
        project, _, raw, _ = self.fixture()
        result = pilot.evaluate(project, raw, self.registry)
        self.assertEqual(result["input"]["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result["verdict"], "NOT_ASSESSED")
        self.assertEqual(result["model_effectiveness"], "NOT_RUN")
        self.assertFalse(result["generic_draft"]["replacement_allowed"])
        with self.assertRaises(ValueError):
            pilot.evaluate(project, raw + b"changed", self.registry)

    def test_prepare_new_directory_only(self):
        project, case, raw, evidence = self.fixture()
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "new"
            manifest = pilot.prepare(directory, project, case, raw, evidence)
            self.assertEqual((directory / "baseline.AGENTS.md").read_bytes(), raw)
            self.assertEqual((directory / "candidate.AGENTS.md").read_bytes(), pilot.variant(raw, case))
            self.assertEqual(manifest["execution_status"], "NOT_RUN")
            with self.assertRaises(FileExistsError):
                pilot.prepare(directory, project, case, raw, evidence)
            with self.assertRaises(ValueError):
                pilot.prepare(Path(tmp) / "invalid", project, case, raw, b"changed")
            self.assertFalse((Path(tmp) / "invalid").exists())


if __name__ == "__main__":
    unittest.main()
