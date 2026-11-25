import copy
import json
import tempfile
import unittest
from pathlib import Path

from module_platform import artifacts as checks
from module_platform.agents import AgentCatalog
from module_platform.artifacts import ArtifactSchemas
from module_platform.skills import SkillLibrary, estimate_tokens, report

CONFIG = Path(__file__).resolve().parents[1] / "config"
DEMO = json.loads((CONFIG / "replay" / "demo.json").read_text())
TASK = DEMO["project_manager"][1]["artifact"]
BRIEF = DEMO["researcher"][0]["artifact"]
DESIGN = DEMO["builder"][0]["artifact"]
PLAN = DEMO["tester"][0]["artifact"]
PROJECT = DEMO["project_manager"][2]["artifact"]
MAX_PROMPT_TOKENS = 2200


class SkillTests(unittest.TestCase):
    def setUp(self):
        self.catalog = AgentCatalog.load(CONFIG / "agents")
        self.library = SkillLibrary(CONFIG / "skills")

    def test_manifest_matches_skill_library(self):
        self.library.validate(self.catalog)
        self.assertEqual(self.catalog.ids(), ("project_manager", "researcher", "builder", "tester"))
        used = {s for a in self.catalog.ids() for s in self.catalog.get(a).skills}
        self.assertEqual(used, set(self.library.ids()), "every skill belongs to exactly one agent")

    def test_agent_prompts_stay_within_budget(self):
        for agent_id in self.catalog.ids():
            agent = self.catalog.get(agent_id)
            worst = self.library.compose(agent, tags=tuple(r.when_tag for r in agent.references))
            self.assertLessEqual(worst.tokens_est, MAX_PROMPT_TOKENS, agent_id)

    def test_references_load_by_tag_only(self):
        researcher = self.catalog.get("researcher")
        without = self.library.compose(researcher, tags=("tabular",))
        with_tag = self.library.compose(researcher, tags=("equation_discovery",))
        self.assertEqual(without.references, ())
        self.assertEqual(len(with_tag.references), 1)
        self.assertGreater(with_tag.tokens_est, without.tokens_est)
        builder = self.library.compose(self.catalog.get("builder"))
        self.assertEqual(len(builder.references), 1)  # "*" is always loaded

    def test_subset_excludes_other_skills_and_references(self):
        pm = self.library.compose(self.catalog.get("project_manager"), only=("plan-synthesis",))
        self.assertEqual(pm.skills, ("plan-synthesis",))
        self.assertNotIn("Intake and scoping", pm.text)

    def test_skill_text_comes_after_role_prompt_for_cache_stability(self):
        text = self.library.compose(self.catalog.get("tester")).text
        self.assertTrue(text.startswith("# Tester"))
        self.assertLess(text.index("# Skills"), text.index("Test design"))

    def test_unknown_skill_and_bad_frontmatter_fail_fast(self):
        with self.assertRaises(ValueError):
            self.library.get("nope")
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "bad").mkdir()
            (Path(tmp) / "bad" / "SKILL.md").write_text("no frontmatter")
            with self.assertRaisesRegex(ValueError, "frontmatter"):
                SkillLibrary(Path(tmp))

    def test_report_lists_every_agent(self):
        text = report(CONFIG)
        for agent_id in self.catalog.ids():
            self.assertIn(agent_id, text)
        self.assertGreater(estimate_tokens("one two three four"), 4)


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.schemas = ArtifactSchemas.load(CONFIG / "schemas")

    def test_fixture_artifacts_are_valid_and_consistent(self):
        for name, art in (("task_spec", TASK), ("research_brief", BRIEF), ("design_spec", DESIGN), ("test_plan", PLAN), ("project_plan", PROJECT)):
            self.assertEqual(self.schemas.validate(name, art), [], name)
        self.assertEqual(checks.check_research(TASK, BRIEF), [])
        self.assertEqual(checks.check_design(TASK, BRIEF, DESIGN), [])
        self.assertEqual(checks.check_test_plan(TASK, BRIEF, PLAN), [])
        self.assertEqual(checks.check_plan(TASK, BRIEF, PROJECT), [])

    def test_schema_reports_missing_wrong_type_and_enum(self):
        bad = copy.deepcopy(TASK)
        del bad["title"]
        bad["tags"] = ["magic"]
        bad["budget"]["max_repair_cycles"] = "two"
        errors = self.schemas.validate("task_spec", bad)
        self.assertTrue(any("title: missing" in e for e in errors))
        self.assertTrue(any("tags[0]" in e for e in errors))
        self.assertTrue(any("max_repair_cycles" in e for e in errors))
        self.assertEqual(self.schemas.validate("task_spec", "text"), ["task_spec: expected object"])

    def test_bool_is_not_a_number(self):
        bad = copy.deepcopy(BRIEF)
        bad["compute_budget"]["train_seconds_max"] = True
        self.assertTrue(self.schemas.validate("research_brief", bad))

    def test_defaults_may_be_numbers_or_strings_but_not_objects(self):
        design = copy.deepcopy(DESIGN)
        design["tabs"][0]["controls"][1]["default"] = 2
        self.assertEqual(self.schemas.validate("design_spec", design), [])
        design["tabs"][0]["controls"][1]["default"] = {"a": 1}
        self.assertTrue(self.schemas.validate("design_spec", design))

    def test_design_checks(self):
        design = copy.deepcopy(DESIGN)
        design["tabs"][0]["controls"] = [c for c in design["tabs"][0]["controls"] if c.get("hyperparameter") != "threshold"]
        design["files"] = [f for f in design["files"] if f["path"] != "tabs/predict_tab.py" and not f["path"].startswith("tests/")]
        design["tabs"][0]["plots"] = design["tabs"][0]["plots"] * 2
        errors = " | ".join(checks.check_design(TASK, BRIEF, design))
        self.assertIn("'threshold'", errors)
        self.assertIn("tabs/predict_tab.py", errors)
        self.assertIn("tests/ is required", errors)
        self.assertIn("maximum is 5", errors)

    def test_research_must_cover_oracle_criteria(self):
        brief = copy.deepcopy(BRIEF)
        brief["covers"] = []
        self.assertTrue(checks.check_research(TASK, brief))

    def test_test_plan_needs_coverage_edge_case_and_oracle(self):
        plan = copy.deepcopy(PLAN)
        plan["cases"] = [c for c in plan["cases"] if c["id"] != "T8"]
        for case in plan["cases"]:
            case["edge_case"] = False
        plan["oracle_checks"] = []
        errors = " | ".join(checks.check_test_plan(TASK, BRIEF, plan))
        self.assertIn("AC5", errors)
        self.assertIn("edge case", errors)
        self.assertIn("oracle", errors)

    def test_describe_is_compact_and_marks_optional_fields(self):
        text = self.schemas.describe("design_spec")
        self.assertIn("hyperparameter?: string", text)
        self.assertLess(estimate_tokens(text), 400)

    def test_render_plan_is_deterministic_and_honest(self):
        text = checks.render_plan(TASK, PROJECT)
        self.assertIn(TASK["title"], text)
        for criterion in TASK["acceptance_criteria"]:
            self.assertIn(criterion["id"], text)
        self.assertTrue(text.rstrip().endswith("Approve this plan to start the build."))
        self.assertEqual(text, checks.render_plan(TASK, PROJECT))




class EnvironmentNoteTests(unittest.TestCase):
    def test_note_lists_only_installed_science_packages(self):
        from module_platform.environment import available_packages, environment_note

        found = available_packages()
        self.assertIn("numpy", found)
        self.assertNotIn("flask", {name.lower() for name in found})
        self.assertIn(f"numpy {found['numpy']}", environment_note())


if __name__ == "__main__":
    unittest.main()
