import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import build_site
import compass
import generator


class SiteTests(unittest.TestCase):
    def test_public_build_and_generator_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "site"
            metadata = build_site.build(dest)
            s, t, p = compass.load_registry()
            g = generator.load_generation(t, p)
            self.assertEqual(len(metadata["practices"]), len(p))
            count = len(g["harnesses"]) * (1 + sum(v["kind"] in {"model", "family"}
                                                    for v in t.values())) * (1 + len(g["frameworks"])) * 2
            self.assertEqual(len(metadata["profiles"]), count)
            self.assertEqual(set(x.name for x in dest.iterdir()),
                             {"index.html", "style.css", "app.js", "audit.js",
                              "bundles", "data.json", ".nojekyll", "knowledge", "api", "skills",
                              "llms.txt", "llms.ja.txt", "llms-full.txt", "llms-full.ja.txt"})
            for item in metadata["profiles"].values():
                raw = (dest / item["path"]).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), item["sha256"])
                self.assertEqual(set(json.loads(raw)),
                                 {"AGENTS.draft.md", "CONFIGURATION.md", "EVIDENCE.md"})
            for lang in ("ja", "en"):
                key = "opencode|kimi-k3|superpowers|" + lang
                bundle = json.loads((dest / metadata["profiles"][key]["path"]).read_bytes())
                self.assertEqual(bundle, generator.generate(s, t, p, g, "opencode",
                                                            "kimi-k3", "superpowers", lang))
            with self.assertRaises(FileExistsError):
                build_site.build(dest)

    def test_invalid_profile_path(self):
        with self.assertRaises(ValueError):
            build_site.bundle_name("../bad", None, None, "ja")


if __name__ == "__main__":
    unittest.main()
