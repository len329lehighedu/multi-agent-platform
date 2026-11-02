"""Independent acceptance checks for RL-01, RL-02, RL-03, and RL-07.

The numerical expectations here are written from the accepted brief rather than
derived from the module implementation.
"""

import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np
from bokeh.document import Document
from bokeh.events import ButtonClick


PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODULE_ROOT = PROJECT_ROOT / "modules" / "reinforcement-learning"
PACKAGE = "_rl_independent_qa"
spec = importlib.util.spec_from_file_location(
    PACKAGE,
    MODULE_ROOT / "__init__.py",
    submodule_search_locations=[str(MODULE_ROOT)],
)
package = importlib.util.module_from_spec(spec)
sys.modules[PACKAGE] = package
assert spec.loader is not None
spec.loader.exec_module(package)
engine = __import__(PACKAGE + ".engine", fromlist=["*"])
ui = __import__(PACKAGE + ".ui", fromlist=["*"])


def named(doc, name):
    return doc.select_one({"name": name})


class ScientificOracleTests(unittest.TestCase):
    def test_transition_oracles_from_grid_coordinates(self):
        # Ordinary move: start (3, 0) up to (2, 0), state 8.
        item = engine.transition(12, 0, 0)
        self.assertEqual(
            (item.next_state, item.reward, item.terminated, item.truncated, item.steps_taken),
            (8, -0.05, False, False, 1),
        )

        # Boundary action: (3, 0) left remains at state 12.
        item = engine.transition(12, 3, 8)
        self.assertEqual(
            (item.next_state, item.reward, item.terminated, item.truncated, item.steps_taken),
            (12, -0.05, False, False, 9),
        )

        # Enter goal at (0, 3) and hazard at (2, 2).
        goal = engine.transition(2, 1, 6)
        hazard = engine.transition(9, 1, 6)
        self.assertEqual((goal.next_state, goal.reward, goal.terminated), (3, 1.0, True))
        self.assertEqual((hazard.next_state, hazard.reward, hazard.terminated), (10, -1.0, True))

        # The 40th ordinary action truncates; terminal arrival takes precedence.
        limit = engine.transition(12, 3, 39)
        terminal_at_limit = engine.transition(2, 1, 39)
        self.assertEqual((limit.terminated, limit.truncated), (False, True))
        self.assertEqual((terminal_at_limit.terminated, terminal_at_limit.truncated), (True, False))

    def test_q_update_oracles_calculated_directly(self):
        # Nonterminal: target = -0.05 + 0.9*0.4 = 0.31;
        # Qnew = 0.2 + 0.5*(0.31-0.2) = 0.255.
        q = engine.new_q_table()
        q[5, 1] = 0.2
        q[6, 2] = 0.4
        record = engine.apply_q_update(q, engine.transition(5, 1, 0), 0.5, 0.9)
        self.assertAlmostEqual(record.future, 0.4, places=12)
        self.assertAlmostEqual(record.target, 0.31, places=12)
        self.assertAlmostEqual(record.td_error, 0.11, places=12)
        self.assertAlmostEqual(record.new_q, 0.255, places=12)

        # Terminal: target = reward = 1; next-state Q values must be ignored.
        q = engine.new_q_table()
        q[2, 1] = 0.2
        q[3, :] = 50.0
        record = engine.apply_q_update(q, engine.transition(2, 1, 0), 0.5, 0.9)
        self.assertEqual(record.future, 0.0)
        self.assertAlmostEqual(record.target, 1.0, places=12)
        self.assertAlmostEqual(record.new_q, 0.6, places=12)

        # Time-limit truncation is not terminal and therefore bootstraps.
        q = engine.new_q_table()
        q[12, 3] = 0.2
        q[12, 0] = 0.4
        record = engine.apply_q_update(q, engine.transition(12, 3, 39), 0.5, 0.9)
        self.assertAlmostEqual(record.target, 0.31, places=12)
        self.assertAlmostEqual(record.new_q, 0.255, places=12)

    def test_seeded_training_repeats_and_evaluation_is_read_only(self):
        q1 = engine.new_q_table()
        q2 = engine.new_q_table()
        trace1 = engine.train_episodes(q1, np.random.default_rng(42), 60, 0.3, 0.95, 0.2)
        trace2 = engine.train_episodes(q2, np.random.default_rng(42), 60, 0.3, 0.95, 0.2)
        self.assertEqual(trace1, trace2)
        np.testing.assert_array_equal(q1, q2)
        before = q1.copy()
        result = engine.evaluate_greedy(q1, 100)
        np.testing.assert_array_equal(q1, before)
        self.assertEqual(result["episodes"], 100)


class SessionContractTests(unittest.TestCase):
    def test_documents_are_isolated_and_reset_clears_visible_state(self):
        first = Document()
        second = Document()
        ui.build_document(first)
        ui.build_document(second)
        self.assertFalse(set(first.models) & set(second.models))

        second_before = {key: list(value) for key, value in named(second, "board_source").data.items()}
        button = named(first, "step_training")
        button._trigger_event(ButtonClick(model=button))
        self.assertIn("step 1/40", named(first, "status").text)
        self.assertEqual(named(second, "board_source").data, second_before)
        self.assertEqual(named(second, "episode_curve_source").data["episode"], [])

        named(first, "episodes").value = 12
        train = named(first, "train_episodes")
        train._trigger_event(ButtonClick(model=train))
        self.assertEqual(len(named(first, "episode_curve_source").data["episode"]), 12)
        self.assertEqual(named(second, "episode_curve_source").data["episode"], [])

        named(first, "seed").value = 99
        reset = named(first, "reset_q")
        reset._trigger_event(ButtonClick(model=reset))
        self.assertIn("seed 99 applied", named(first, "status").text)
        self.assertEqual(named(first, "episode_curve_source").data["episode"], [])
        board = named(first, "board_source").data
        for key in ("q_up", "q_right", "q_down", "q_left"):
            self.assertTrue(all(value == 0.0 for value in board[key]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
