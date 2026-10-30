import csv
import importlib.util
import inspect
import io
from pathlib import Path
import sys
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("csv_adapter_fixture", ROOT / "csv_adapter.py")
adapter = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = adapter
spec.loader.exec_module(adapter)


def csv_text(xs, ys):
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(["x", "y"])
    writer.writerows(zip(xs, ys))
    return buffer.getvalue()


class CSVAdaptationTests(unittest.TestCase):
    def test_generated_data_round_trip_and_shipped_scientific_pipeline(self):
        original = adapter._engine.generate_data(1.7, 91, 18)
        text = csv_text(original.x, original.y)
        data, result = adapter.fit_csv(text, seed=9)
        self.assertIsInstance(data, adapter.Dataset)
        self.assertTrue(inspect.getfile(adapter.fit_and_evaluate).endswith("modules/linear-regression/engine.py"))
        np.testing.assert_array_equal(data.x, original.x)
        np.testing.assert_array_equal(data.y, original.y)
        np.testing.assert_array_equal(data.standard_noise, np.zeros(91))
        xs = [float(data.x[i]) for i in data.train_idx]
        ys = [float(data.y[i]) for i in data.train_idx]
        mx, my = sum(xs)/len(xs), sum(ys)/len(ys)
        slope = sum((x-mx)*(y-my) for x,y in zip(xs,ys))/sum((x-mx)**2 for x in xs)
        intercept = my - slope*mx
        self.assertAlmostEqual(result.slope,slope,places=12)
        self.assertAlmostEqual(result.intercept,intercept,places=12)
        residuals = [float(y)-(slope*float(x)+intercept) for x,y in zip(data.x,data.y)]
        np.testing.assert_allclose(result.residuals,residuals,atol=1e-12)
        for indices,mse in ((data.train_idx,result.train_mse),(data.test_idx,result.test_mse)):
            self.assertAlmostEqual(mse,sum(residuals[i]**2 for i in indices)/len(indices),places=12)

    def test_boundary_sizes_and_known_line(self):
        for n in (20,300):
            x = np.linspace(-12, 12, n)
            data,result = adapter.fit_csv(csv_text(x,-3*x+7),2**32-1)
            self.assertEqual(len(data.x),n)
            self.assertAlmostEqual(result.slope,-3,delta=1e-12)
            self.assertAlmostEqual(result.intercept,7,delta=1e-12)
            self.assertLess(result.test_mse,1e-24)

    def test_split_reproducible_disjoint_exhaustive(self):
        text = csv_text(range(83),range(83))
        a,b,c = adapter.parse_csv(text,0),adapter.parse_csv(text,0),adapter.parse_csv(text,1)
        np.testing.assert_array_equal(a.train_idx,b.train_idx)
        np.testing.assert_array_equal(a.test_idx,b.test_idx)
        self.assertEqual(len(a.train_idx),62)
        self.assertEqual(len(a.test_idx),21)
        self.assertEqual(set(a.train_idx)&set(a.test_idx),set())
        self.assertEqual(set(a.train_idx)|set(a.test_idx),set(range(83)))
        self.assertFalse(np.array_equal(a.train_idx,c.train_idx))

    def test_held_out_response_changes_preserve_fit(self):
        x = np.arange(40,dtype=float)
        y = 4*x+5+np.sin(x)
        data,before = adapter.fit_csv(csv_text(x,y),12)
        y[data.test_idx] += 200
        changed,after = adapter.fit_csv(csv_text(x,y),12)
        np.testing.assert_array_equal(data.train_idx,changed.train_idx)
        self.assertEqual(before.slope,after.slope)
        self.assertEqual(before.intercept,after.intercept)
        self.assertGreater(after.test_mse,before.test_mse+1000)

    def test_reject_headers_and_malformed_columns_quotes(self):
        body = "\n".join(f"{i},{i}" for i in range(20))
        cases = ["", "y,x\n"+body, "x,y,z\n"+body, "x,x\n"+body,
                 " x,y\n"+body, "x,y\n"+body+"\n20,20,20", "x,y\n"+body+"\n20",
                 'x,y\n"unterminated,1', "x,y\n"+body+"\n\n"]
        for text in cases:
            with self.subTest(text=text[:30]),self.assertRaises(ValueError):
                adapter.parse_csv(text)

    def test_reject_nonnumeric_nonfinite_empty_cells(self):
        body = "x,y\n"+"\n".join(f"{i},{i}" for i in range(20))
        for value in ("hello","NaN","inf","-Infinity","1e9999",""):
            for row in (f"{value},1", f"1,{value}"):
                with self.subTest(row=row),self.assertRaises(ValueError):
                    adapter.parse_csv(body+"\n"+row)

    def test_reject_row_count_boundaries(self):
        for n in (0,19,301,500):
            with self.subTest(n=n),self.assertRaises(ValueError):
                adapter.parse_csv(csv_text(range(n),range(n)))

    def test_reject_invalid_seed_and_nontext(self):
        text = csv_text(range(20),range(20))
        for seed in (-1,2**32,1.5,True,None,"42"):
            with self.subTest(seed=seed),self.assertRaises(ValueError):
                adapter.parse_csv(text,seed)
        for text in (None,b"x,y",42):
            with self.subTest(text=text),self.assertRaises(ValueError):
                adapter.parse_csv(text)

    def test_shipped_rank_validation_remains_effective(self):
        text = csv_text(np.ones(20),np.arange(20))
        self.assertEqual(len(adapter.parse_csv(text).x),20)
        with self.assertRaisesRegex(ValueError,"rank deficient"):
            adapter.fit_csv(text)


if __name__ == "__main__":
    unittest.main()
