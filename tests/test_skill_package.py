from pathlib import Path
import re
import unittest

import agent_exports


class SkillPackageTests(unittest.TestCase):
    def test_manifestless_skill_contract(self):
        root = Path(__file__).resolve().parents[1] / "skills/agent-compass"
        expected = {"SKILL.md", "references/usage.md", "references/selection-rules.md",
                    "references/evidence-policy.md"}
        actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
        self.assertEqual(actual, expected)
        self.assertEqual(set(agent_exports.SKILL_FILES), expected)
        for path in root.rglob("*"):
            self.assertFalse(path.is_symlink())
        skill = (root / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(skill.startswith("---\nname: agent-compass\ndescription: "))
        self.assertRegex(skill, r"(?m)^description: .{1,1024}$")
        links = set(re.findall(r"\]\((references/[^)]+)\)", skill))
        self.assertEqual(links, expected - {"SKILL.md"})
        for link in links:
            self.assertTrue((root / link).is_file())


if __name__ == "__main__":
    unittest.main()
