"""Engine, document-session, metadata, and gallery checks for RL Gridworld."""

import importlib.util
import json
from pathlib import Path
import sys
import unittest

import numpy as np
from bokeh.document import Document
from bokeh.events import ButtonClick


MODULE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = MODULE_ROOT.parents[1]
NAME = "_rl_gridworld_tests"
spec = importlib.util.spec_from_file_location(NAME, MODULE_ROOT / "__init__.py", submodule_search_locations=[str(MODULE_ROOT)])
package = importlib.util.module_from_spec(spec)
sys.modules[NAME] = package
spec.loader.exec_module(package)
engine = __import__(NAME + ".engine", fromlist=["*"])
ui = __import__(NAME + ".ui", fromlist=["*"])
sys.path.insert(0, str(PROJECT_ROOT))
from stem_platform.runtime import create_app, discover_modules  # noqa: E402


class EnvironmentTests(unittest.TestCase):
    def test_ordinary_wall_goal_hazard_and_truncation(self):
        ordinary = engine.transition(12, 0, 0)
        self.assertEqual((ordinary.next_state, ordinary.reward, ordinary.terminated, ordinary.truncated), (8, -.05, False, False))
        wall = engine.transition(12, 3, 0)
        self.assertEqual((wall.next_state, wall.reward), (12, -.05))
        goal = engine.transition(2, 1, 3)
        self.assertEqual((goal.next_state, goal.reward, goal.terminated), (3, 1, True))
        hazard = engine.transition(9, 1, 4)
        self.assertEqual((hazard.next_state, hazard.reward, hazard.terminated), (10, -1, True))
        truncation = engine.transition(12, 3, 39)
        self.assertTrue(truncation.truncated); self.assertFalse(truncation.terminated)
        terminal_on_40 = engine.transition(2, 1, 39)
        self.assertTrue(terminal_on_40.terminated); self.assertFalse(terminal_on_40.truncated)
        for args in ((3, 0, 0), (10, 0, 0), (16, 0, 0), (0, 4, 0), (0, 0, 40)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                engine.transition(*args)

    def test_hand_calculated_updates_and_truncation_bootstrap(self):
        q = engine.new_q_table(); q[5, 1] = .2; q[6, 2] = .4
        record = engine.apply_q_update(q, engine.transition(5, 1, 0), .5, .9)
        self.assertAlmostEqual(record.future, .4)
        self.assertAlmostEqual(record.target, .31)
        self.assertAlmostEqual(record.new_q, .255)
        q[2, 1] = .2; q[3] = 99
        terminal = engine.apply_q_update(q, engine.transition(2, 1, 0), .5, .9)
        self.assertEqual(terminal.future, 0)
        self.assertAlmostEqual(terminal.new_q, .6)
        q = engine.new_q_table(); q[12, 3] = .2; q[12, 0] = .4
        truncated = engine.apply_q_update(q, engine.transition(12, 3, 39), .5, .9)
        self.assertAlmostEqual(truncated.future, .4)
        self.assertAlmostEqual(truncated.target, .31)

    def test_ties_reproducibility_reset_contract_and_evaluation_immutability(self):
        q1 = engine.new_q_table(); q2 = engine.new_q_table()
        rng1 = np.random.default_rng(42); rng2 = np.random.default_rng(42)
        actions1 = [engine.choose_training_action(q1, 12, 0, rng1).action for _ in range(20)]
        actions2 = [engine.choose_training_action(q2, 12, 0, rng2).action for _ in range(20)]
        self.assertEqual(actions1, actions2)
        self.assertGreater(len(set(actions1)), 1)
        self.assertEqual(engine.greedy_action(q1, 12), 0)
        rng1 = np.random.default_rng(42); rng2 = np.random.default_rng(42)
        trace1 = engine.train_episodes(q1, rng1, 40, .3, .95, .2)
        trace2 = engine.train_episodes(q2, rng2, 40, .3, .95, .2)
        self.assertEqual(trace1, trace2)
        np.testing.assert_array_equal(q1, q2)
        before = q1.copy(); result = engine.evaluate_greedy(q1, 100)
        np.testing.assert_array_equal(q1, before)
        self.assertEqual(result["episodes"], 100)
        reset = engine.new_q_table()
        self.assertTrue(np.all(reset == 0))

    def test_validation(self):
        q = engine.new_q_table()
        for value in (-.1, 1.1, np.nan, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                engine.train_episodes(q, np.random.default_rng(1), 1, value, .9, .1)
        for count in (0, 501, 1.5, True):
            with self.subTest(count=count), self.assertRaises(ValueError):
                engine.train_episodes(q, np.random.default_rng(1), count, .3, .9, .1)


def model(doc, name):
    return doc.select_one({"name": name})


class DocumentAndGalleryTests(unittest.TestCase):
    def test_two_documents_step_train_reset_and_settings_warning(self):
        first, second = Document(), Document()
        ui.build_document(first); ui.build_document(second)
        self.assertFalse(set(first.models) & set(second.models))
        first_board = model(first, "board_source")
        second_board = model(second, "board_source")
        before_second = {key: list(value) for key, value in second_board.data.items()}
        model(first, "step_training")._trigger_event(ButtonClick(model=model(first, "step_training")))
        self.assertIn("step 1/40", model(first, "status").text)
        self.assertIn("Last Q update", model(first, "last_update").text)
        self.assertEqual(second_board.data, before_second)
        self.assertNotEqual(first_board.data["q_up"] + first_board.data["q_right"] + first_board.data["q_down"] + first_board.data["q_left"], [0.0] * 64)
        model(first, "episodes").value = 7
        model(first, "train_episodes")._trigger_event(ButtonClick(model=model(first, "train_episodes")))
        self.assertEqual(len(model(first, "episode_curve_source").data["episode"]), 7)
        self.assertEqual(len(model(second, "episode_curve_source").data["episode"]), 0)
        self.assertIn("over 100 episodes", model(first, "evaluation").text)
        model(first, "alpha").value = .4
        self.assertIn("controlled conditions", model(first, "status").text)
        model(first, "seed").value = 9
        model(first, "reset_q")._trigger_event(ButtonClick(model=model(first, "reset_q")))
        self.assertEqual(len(model(first, "episode_curve_source").data["episode"]), 0)
        self.assertIn("seed 9 applied", model(first, "status").text)
        board = model(first, "board_source").data
        for key in ("q_up", "q_right", "q_down", "q_left"):
            self.assertTrue(all(value == 0 for value in board[key]))

    def test_metadata_and_root_gallery(self):
        metadata = json.loads((MODULE_ROOT / "module.json").read_text())
        self.assertGreaterEqual(len(metadata["questions"]), 3)
        self.assertTrue(any("epsilon" in item["question"].lower() for item in metadata["questions"]))
        modules = {item["id"] for item in discover_modules(PROJECT_ROOT)}
        self.assertIn("reinforcement-learning", modules)
        self.assertIn("neural-equation-finder", modules)
        client = create_app(PROJECT_ROOT).test_client()
        home = client.get("/")
        self.assertEqual(home.status_code, 200)
        text = home.get_data(as_text=True)
        self.assertIn("RL Gridworld Lab", text)
        self.assertIn("Neural Equation Finder", text)
        self.assertIn("/modules/reinforcement-learning/", text)
        self.assertEqual(client.get("/modules/reinforcement-learning/").status_code, 200)


if __name__ == "__main__":
    unittest.main()
