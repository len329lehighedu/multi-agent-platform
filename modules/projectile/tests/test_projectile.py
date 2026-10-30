"""Independent scientific checks and Bokeh callback/session contracts."""
import json
import math
from pathlib import Path
import unittest

import numpy as np
from bokeh.document import Document
from modules.projectile.engine import MAX_SAMPLES, trajectory
from modules.projectile.ui import build_document


class TrajectoryTests(unittest.TestCase):
    def test_independent_thirty_degree_oracle(self):
        result = trajectory(20, 30)
        self.assertAlmostEqual(result.flight_time, 20 / 9.81, places=12)
        self.assertAlmostEqual(result.range, 200 * math.sqrt(3) / 9.81, places=12)
        self.assertAlmostEqual(result.max_height, 50 / 9.81, places=12)
        # Evaluate Newtonian position independently at every returned time.
        for t, x, y in zip(result.time, result.x, result.y):
            self.assertAlmostEqual(x, 10 * math.sqrt(3) * t, places=11)
            self.assertAlmostEqual(y, 10 * t - 9.81 * t * t / 2, places=11)
        self.assertAlmostEqual(max(result.y), result.max_height, places=12)

    def test_speed_scaling_and_complementary_angles(self):
        slow, fast = trajectory(20, 30), trajectory(40, 30)
        self.assertAlmostEqual(fast.flight_time, 2 * slow.flight_time)
        self.assertAlmostEqual(fast.range, 4 * slow.range)
        self.assertAlmostEqual(fast.max_height, 4 * slow.max_height)
        high = trajectory(20, 60)
        self.assertAlmostEqual(high.range, slow.range)
        self.assertGreater(high.flight_time, slow.flight_time)
        self.assertGreater(high.max_height, slow.max_height)

    def test_edges_and_sample_grid(self):
        for speed, angle in [(0, 0), (0, 90), (50, 0), (50, 90), (50, 45), (0.01, 1)]:
            for count in [2, 3, 201, MAX_SAMPLES]:
                with self.subTest(speed=speed, angle=angle, samples=count):
                    result = trajectory(speed, angle, samples=count)
                    for array in [result.time, result.x, result.y]:
                        self.assertEqual(array.shape, (count,))
                        self.assertEqual(array.dtype, np.float64)
                        self.assertTrue(np.isfinite(array).all())
                    self.assertTrue((np.diff(result.time) >= 0).all())
                    self.assertTrue((result.y >= -1e-12).all())
                    self.assertEqual(result.y[0], 0)
                    self.assertEqual(result.y[-1], 0)
                    self.assertEqual(result.x[-1], result.range)
                    if speed == 0 or angle == 0:
                        self.assertEqual(result.flight_time, 0)
                        self.assertEqual(result.range, 0)
                        self.assertEqual(result.max_height, 0)
                        self.assertTrue((result.y == 0).all())
                    if angle == 90:
                        self.assertEqual(result.range, 0)
                        self.assertTrue((result.x == 0).all())

    def test_scalar_validation(self):
        invalid = [True, np.bool_(False), None, "20", 1 + 0j, [], [20],
                   np.array([20]), np.array(20), float("nan"), float("inf"), -1]
        for value in invalid:
            for field in ["speed", "angle"]:
                with self.subTest(field=field, value=repr(value)):
                    arguments = dict(speed=20, angle=45)
                    arguments[field] = value
                    with self.assertRaisesRegex(ValueError, field):
                        trajectory(**arguments)
        with self.assertRaisesRegex(ValueError, "speed"):
            trajectory(50.01, 45)
        with self.assertRaisesRegex(ValueError, "angle"):
            trajectory(20, 90.01)
        self.assertGreater(trajectory(np.float64(20), np.int64(45)).range, 0)

    def test_sample_validation_and_fresh_arrays(self):
        for count in [True, None, 2.0, "201", 1, 0, MAX_SAMPLES + 1, float("inf"), np.array(201)]:
            with self.subTest(samples=repr(count)):
                with self.assertRaisesRegex(ValueError, "samples"):
                    trajectory(20, 45, samples=count)
        a, b = trajectory(20, 45), trajectory(20, 45, samples=np.int64(201))
        a.y[1] = 12345
        self.assertNotEqual(a.y[1], b.y[1])


class DocumentTests(unittest.TestCase):
    def document(self):
        doc = Document()
        build_document(doc)
        return doc

    def test_controls_update_arrays_and_all_summaries(self):
        doc = self.document()
        speed, angle = doc.get_model_by_name("speed"), doc.get_model_by_name("angle")
        source, metrics = doc.get_model_by_name("trajectory"), doc.get_model_by_name("metrics")
        old_y = source.data["y"].copy()
        speed.value = 40
        self.assertFalse(np.array_equal(source.data["y"], old_y))
        angle.value = 30
        result = trajectory(40, 30)
        for key, expected in [("t", result.time), ("x", result.x), ("y", result.y)]:
            np.testing.assert_allclose(source.data[key], expected)
        for value, unit in [(result.flight_time, "s"), (result.range, "m"), (result.max_height, "m")]:
            self.assertIn(f"{value:.3f} {unit}", metrics.text)
        angle.value = 90
        self.assertTrue((source.data["x"] == 0).all())
        speed.value = 0
        self.assertIn("Zero-duration", doc.get_model_by_name("status").text)
        self.assertTrue(np.isfinite(source.data["y"]).all())
        # A malformed server-side value is reported, retaining last valid data.
        speed.value = -1
        self.assertIn("Choose valid controls", doc.get_model_by_name("status").text)
        speed.value = 20
        self.assertNotIn("Choose valid controls", doc.get_model_by_name("status").text)
        doc.validate()

    def test_two_documents_share_no_models_or_arrays(self):
        a, b = self.document(), self.document()
        self.assertFalse(set(a.models) & set(b.models))
        original = b.get_model_by_name("trajectory").data["y"].copy()
        metrics = b.get_model_by_name("metrics").text
        a.get_model_by_name("speed").value = 50
        a.get_model_by_name("angle").value = 20
        self.assertEqual(b.get_model_by_name("speed").value, 20)
        self.assertEqual(b.get_model_by_name("angle").value, 45)
        np.testing.assert_array_equal(b.get_model_by_name("trajectory").data["y"], original)
        self.assertEqual(b.get_model_by_name("metrics").text, metrics)
        self.assertEqual(a.get_model_by_name("trajectory_plot").xaxis[0].axis_label, "Horizontal position x (m)")
        self.assertEqual(a.roots[0].sizing_mode, "stretch_width")

    def test_lesson_contract(self):
        metadata = json.loads((Path(__file__).parents[1] / "module.json").read_text())
        self.assertEqual(len(metadata["questions"]), 3)
        self.assertEqual(len(metadata["objectives"]), 3)
        self.assertTrue(all(item["question"] and item["answer"] for item in metadata["questions"]))
        self.assertIn("9.81", " ".join(metadata["assumptions"]))


if __name__ == "__main__":
    unittest.main()
