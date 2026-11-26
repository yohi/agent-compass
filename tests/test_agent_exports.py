import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest

import agent_exports
import build_site


class AgentExportsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.site = Path(cls.tmp.name) / "site"
        cls.metadata = build_site.build(cls.site)
        cls.manifest = cls.read("api/v1/manifest.json")

    @classmethod
    def read(cls, path):
        return json.loads((cls.site / path).read_text(encoding="utf-8"))

    def test_manifest_and_file_identities(self):
        m = self.manifest
        self.assertEqual(m["registry_sha256"], self.metadata["registry_sha256"])
        self.assertEqual(m["counts"]["targets"], len(self.metadata["targets"]))
        for path, record in m["files"].items():
            raw = (self.site / path).read_bytes()
            self.assertEqual(record["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(record["bytes"], len(raw))
        for name in ("llms.txt", "llms.ja.txt"):
            content = (self.site / name).read_text()
            for path in re.findall(re.escape(agent_exports.BASE_URL) + r"([^)\s]*)\)", content):
                self.assertTrue((self.site / path).exists(), path)

    def test_exact_scopes_and_complete_evidence(self):
        m = self.manifest
        expected = {p["id"]: p for p in self.metadata["practices"]}
        all_ids = set()
        for target in m["targets"]:
            scoped = self.read(target["json"])
            key = target["id"]
            ids = {p["id"] for p in scoped["practices"]}
            self.assertEqual(ids, {pid for pid, p in expected.items() if p["target"] == key})
            self.assertEqual(target["practice_count"], len(ids))
            self.assertEqual(scoped["registry_sha256"], m["registry_sha256"])
            sources = {s["id"]: s for s in scoped["sources"]}
            for lang, path in target["markdown"].items():
                md = (self.site / path).read_text()
                self.assertEqual(set(re.findall(r"^## (BP-\d+) —", md, re.M)), ids)
                for p in scoped["practices"]:
                    self.assertIn(p[lang], md)
                    self.assertIn(p["status"], md)
                    self.assertIn(p["local_eval"], md)
                    self.assertIn(p["scope"], md)
                    for sid in p["evidence"]:
                        self.assertIn(sources[sid]["url"], md)
            all_ids.update(ids)
        self.assertEqual(all_ids, set(expected))
        self.assertEqual(self.read("api/v1/targets/kimi-k2.8-preview.json")["practices"], [])

    def test_full_and_generator_index(self):
        ids = {p["id"] for p in self.metadata["practices"]}
        for path in ("llms-full.txt", "llms-full.ja.txt"):
            text = (self.site / path).read_text()
            self.assertEqual(set(re.findall(r"^## (BP-\d+) —", text, re.M)), ids)
        idx = self.read("api/v1/generator.json")
        self.assertEqual(idx["profiles"], self.metadata["profiles"])
        self.assertIn("opencode|kimi-k3|superpowers|ja", idx["profiles"])
        self.assertEqual(self.read("api/v1/practices.json")["practices"], self.metadata["practices"])
        self.assertEqual(self.read("api/v1/sources.json")["sources"], self.metadata["sources"])

    def test_skill_package_and_reproducibility(self):
        skill = self.site / "skills/agent-compass/SKILL.md"
        text = skill.read_text()
        self.assertTrue(text.startswith("---\nname: agent-compass\ndescription: "))
        for path in re.findall(r"\]\((references/[^)]+)\)", text):
            self.assertTrue((skill.parent / path).is_file())
        other = Path(self.tmp.name) / "repeat"
        build_site.build(other)
        self.assertEqual((self.site / "api/v1/manifest.json").read_bytes(),
                         (other / "api/v1/manifest.json").read_bytes())

    def test_no_implicit_family_or_framework(self):
        ids = {r["id"]: r for r in self.manifest["targets"]}
        self.assertEqual(ids["kimi-k3"]["markdown"]["en"], "knowledge/models/kimi-k3.md")
        self.assertEqual(ids["kimi"]["markdown"]["en"], "knowledge/families/kimi.md")
        self.assertEqual(ids["superpowers"]["markdown"]["en"], "knowledge/frameworks/superpowers.md")
        self.assertEqual(ids["common"]["markdown"]["en"], "knowledge/common.md")
        self.assertEqual(ids["opencode"]["markdown"]["en"], "knowledge/harnesses/opencode.md")


if __name__ == "__main__":
    unittest.main()
