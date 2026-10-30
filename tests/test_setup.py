"""Behavior checks for adapter synchronization and exemplar-integrity detection."""

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_setup import check
from sync_runtime import adapter_errors, expected_adapters


class SetupChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "platform"
        # Copy only the setup inputs, not live runs or generated modules.
        for name in ("agents", ".agents", ".codex", ".claude", "docs", "templates", "corpus", "evaluations"):
            shutil.copytree(ROOT / name, self.root / name)
        for name in ("AGENTS.md", "README.md", "sources.json"):
            shutil.copyfile(ROOT / name, self.root / name)
        catalog_path = self.root / "corpus/catalog.json"
        catalog = json.loads(catalog_path.read_text())
        for module in catalog["modules"]:
            source_root = (ROOT / "corpus" / module["source_root"]).resolve()
            module["source_root"] = str(source_root)
        catalog_path.write_text(json.dumps(catalog))

    def test_current_configuration_is_consistent(self):
        errors, roles, skills = check(self.root)
        self.assertEqual(errors, [])
        self.assertEqual((roles, skills), (4, 8))

    def test_shared_skill_change_requires_claude_adapter_refresh(self):
        path = self.root / ".agents/skills/stem-learning-ui/SKILL.md"
        path.write_text(path.read_text() + "\nA new shared instruction.\n")
        self.assertTrue(any("Stale runtime adapter" in error for error in adapter_errors(self.root)))
        for relative, text in expected_adapters(self.root).items():
            (self.root / relative).write_text(text)
        self.assertEqual(adapter_errors(self.root), [])

    def test_unknown_skill_is_detected(self):
        path = self.root / "agents/stem-builder.md"
        path.write_text(path.read_text().replace("  - stem-module-examples", "  - missing-skill"))
        self.assertTrue(any("Unknown preloaded skill" in error for error in check(self.root)[0]))

    def test_changed_exemplar_hash_is_detected(self):
        path = self.root / "corpus/catalog.json"
        data = json.loads(path.read_text())
        data["modules"][0]["files"][0]["sha256"] = "0" * 64
        path.write_text(json.dumps(data))
        self.assertTrue(any("Exemplar source drift" in error for error in check(self.root)[0]))

    def test_missing_case_study_is_detected(self):
        (self.root / "corpus/sindy.md").unlink()
        self.assertTrue(any("Missing case study" in error for error in check(self.root)[0]))


if __name__ == "__main__":
    unittest.main()
