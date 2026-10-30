"""Synthetic input tests; these are not measured project productivity results."""

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from evaluate_productivity import evaluate


class ProductivityTests(unittest.TestCase):
    def result(self, rows):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "measurements.csv"
            path.write_text("pair_id,mode,human_minutes,wall_seconds,cost_usd,quality_pass\n" + rows)
            return evaluate(path)

    def test_no_data_is_not_a_success(self):
        self.assertEqual(self.result("")["status"], "insufficient-data")

    def test_quality_failure_is_not_excluded_from_comparison(self):
        rows = "".join(f"{i},baseline,10,100,,true\n{i},multi-agent,5,80,,{'false' if i == 1 else 'true'}\n" for i in range(3))
        result = self.result(rows)
        self.assertEqual(result["status"], "quality-failed")
        self.assertFalse(result["target_met"])

    def test_median_matched_comparison_and_unavailable_cost(self):
        rows = "".join(f"{i},baseline,10,100,,true\n{i},multi-agent,6,80,,true\n" for i in range(3))
        result = self.result(rows)
        self.assertAlmostEqual(result["reduction_percent"], 40)
        self.assertTrue(result["target_met"])
        self.assertIsNone(result["measurements"]["0"]["baseline"]["cost_usd"])

    def test_invalid_and_duplicate_measurements_fail(self):
        for rows in ("x,baseline,nan,20,,true\n", "x,baseline,0,20,,true\n", "x,baseline,10,20,,true\nx,baseline,10,20,,true\n"):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.result(rows)


if __name__ == "__main__":
    unittest.main()
