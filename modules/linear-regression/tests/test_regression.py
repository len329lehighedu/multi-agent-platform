"""Independent numerical oracles and per-document callback contract tests."""
import importlib.util
from pathlib import Path
import sys
import unittest
from dataclasses import replace
import numpy as np
from bokeh.document import Document
from bokeh.events import ButtonClick

PACKAGE = "pilot_linear_regression_tests"
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(PACKAGE, ROOT / "__init__.py", submodule_search_locations=[str(ROOT)])
module = importlib.util.module_from_spec(spec)
sys.modules[PACKAGE] = module
spec.loader.exec_module(module)
from pilot_linear_regression_tests.engine import Dataset, generate_data, fit_and_evaluate
from pilot_linear_regression_tests.ui import build_document


class NumericalTests(unittest.TestCase):
    def test_independent_centered_sums_oracle(self):
        data = generate_data(2.3, 87, 17)
        result = fit_and_evaluate(data)
        xs = [float(data.x[i]) for i in data.train_idx]
        ys = [float(data.y[i]) for i in data.train_idx]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        slope = sum((x-mx)*(y-my) for x,y in zip(xs,ys)) / sum((x-mx)**2 for x in xs)
        intercept = my - slope * mx
        self.assertAlmostEqual(result.slope, slope, places=12)
        self.assertAlmostEqual(result.intercept, intercept, places=12)
        errors = [float(y) - (slope * float(x) + intercept) for x,y in zip(data.x,data.y)]
        np.testing.assert_allclose(result.residuals, errors, atol=1e-12)
        np.testing.assert_allclose(result.predictions, [slope*float(x)+intercept for x in data.x], atol=1e-12)
        for idx, actual in ((data.train_idx,result.train_mse),(data.test_idx,result.test_mse)):
            self.assertAlmostEqual(actual, sum(errors[i]**2 for i in idx)/len(idx), places=12)

    def test_held_out_responses_do_not_affect_fit(self):
        data = generate_data()
        original = fit_and_evaluate(data)
        changed_y = data.y.copy()
        changed_y[data.test_idx] += 100
        altered = fit_and_evaluate(replace(data, y=changed_y))
        self.assertEqual(original.slope, altered.slope)
        self.assertEqual(original.intercept, altered.intercept)
        self.assertEqual(original.train_mse, altered.train_mse)
        self.assertGreater(altered.test_mse, original.test_mse + 1000)

    def test_zero_noise_recovers_true_line_at_boundaries(self):
        for n in (20,100,300):
            result = fit_and_evaluate(generate_data(0,n,0))
            self.assertAlmostEqual(result.slope,2,delta=1e-12)
            self.assertAlmostEqual(result.intercept,1,delta=1e-12)
            self.assertLess(result.train_mse,1e-24)
            self.assertLess(result.test_mse,1e-24)
        fit_and_evaluate(generate_data(5,300,2**32-1))

    def test_reproducibility_and_noise_comparisons(self):
        a,b,c = generate_data(1,101,42),generate_data(1,101,42),generate_data(3,101,42)
        for name in ("x","y","standard_noise","train_idx","test_idx"):
            np.testing.assert_array_equal(getattr(a,name),getattr(b,name))
        np.testing.assert_array_equal(a.standard_noise,c.standard_noise)
        np.testing.assert_array_equal(a.train_idx,c.train_idx)
        np.testing.assert_allclose(c.y - (2*c.x+1),3*(a.y-(2*a.x+1)),atol=1e-14)
        self.assertEqual(len(a.train_idx),75)
        self.assertEqual(set(a.train_idx) & set(a.test_idx),set())
        self.assertEqual(set(a.train_idx) | set(a.test_idx),set(range(101)))
        self.assertFalse(np.array_equal(a.y,generate_data(1,101,43).y))

    def test_fixed_realization_residuals_and_mse_scale_with_sigma(self):
        # Metamorphic oracle: projection onto a fixed linear design is linear;
        # the exactly linear truth contributes zero residual. No OLS copy.
        for n, seed in ((20, 0), (101, 42), (300, 2**32-1)):
            base = fit_and_evaluate(generate_data(.5, n, seed))
            scaled = fit_and_evaluate(generate_data(2, n, seed))
            np.testing.assert_allclose(scaled.residuals, 4*base.residuals, rtol=1e-11, atol=1e-12)
            self.assertAlmostEqual(scaled.train_mse, 16*base.train_mse, delta=1e-11)
            self.assertAlmostEqual(scaled.test_mse, 16*base.test_mse, delta=1e-11)

    def test_invalid_controls(self):
        for name, values in {"noise":[-1,5.1,np.nan,np.inf,True,"1"],"sample_count":[19,301,20.5,True,"20"],"seed":[-1,2**32,1.5,True,None]}.items():
            for value in values:
                with self.subTest(name=name,value=value), self.assertRaises(ValueError):
                    generate_data(**{name:value})

    def test_invalid_dataset_shapes_values_partitions_and_rank(self):
        data = generate_data()
        bad = [None, replace(data,x=data.x[:,None]), replace(data,y=data.y[:-1]),
               replace(data,standard_noise=np.full(100,np.nan)), replace(data,y=np.full(100,np.inf)),
               replace(data,x=np.array(["bad"]*100)), replace(data,x=np.ones(100)),
               replace(data,train_idx=data.train_idx.astype(float)), replace(data,test_idx=np.array([],dtype=int)),
               replace(data,train_idx=np.array([-1]+list(data.train_idx[1:]))),
               replace(data,train_idx=np.array([100]+list(data.train_idx[1:]))),
               replace(data,test_idx=data.train_idx[:25]), replace(data,test_idx=data.test_idx[:-1]),
               replace(data,train_idx=data.train_idx[:,None])]
        for i, invalid in enumerate(bad):
            with self.subTest(case=i), self.assertRaises(ValueError):
                fit_and_evaluate(invalid)


class UITests(unittest.TestCase):
    def make_document(self):
        doc = Document()
        build_document(doc)
        return doc

    def click(self,doc):
        button = doc.select_one({"name":"generate"})
        button._trigger_event(ButtonClick(model=button))

    def test_pending_then_atomic_generate_updates_sources_metrics(self):
        doc = self.make_document()
        source = doc.select_one({"name":"observations"})
        original = np.array(source.data['y'])
        metrics = doc.select_one({"name":"metrics"})
        old_metrics = metrics.text
        doc.select_one({"name":"noise"}).value = 0
        self.assertIn("Click Generate",doc.select_one({"name":"status"}).text)
        self.assertEqual(old_metrics,metrics.text)
        np.testing.assert_array_equal(source.data['y'],original)
        doc.select_one({"name":"sample_count"}).value = 20
        doc.select_one({"name":"seed"}).value = 7
        self.click(doc)
        self.assertEqual(len(source.data['x']),20)
        np.testing.assert_allclose(source.data['y'],2*source.data['x']+1)
        np.testing.assert_allclose(doc.select_one({"name":"residuals"}).data['residual'],0,atol=1e-12)
        np.testing.assert_allclose(doc.select_one({"name":"fit_line"}).data['y'],[1,21],atol=1e-12)
        self.assertEqual(set(source.data['marker']),{'circle','triangle'})
        self.assertEqual(sum(s=='train' for s in source.data['split']),15)
        self.assertIn("n = 20; seed = 7",metrics.text)
        self.assertIn("σ = 0",metrics.text)

    def test_invalid_seed_retains_committed_results(self):
        doc = self.make_document()
        source = doc.select_one({"name":"observations"})
        old = np.array(source.data['y'])
        doc.select_one({"name":"seed"}).value = None
        self.click(doc)
        self.assertIn("Input error",doc.select_one({"name":"status"}).text)
        np.testing.assert_array_equal(source.data['y'],old)

    def test_documents_have_distinct_models_and_callback_state(self):
        a,b = self.make_document(),self.make_document()
        a_models,b_models = set(a.models),set(b.models)
        self.assertFalse(a_models & b_models)
        old = np.array(b.select_one({"name":"observations"}).data['y'])
        old_status = b.select_one({"name":"status"}).text
        a.select_one({"name":"noise"}).value = 5
        self.click(a)
        np.testing.assert_array_equal(b.select_one({"name":"observations"}).data['y'],old)
        self.assertEqual(b.select_one({"name":"status"}).text,old_status)
        self.assertNotEqual(a.select_one({"name":"metrics"}).text,b.select_one({"name":"metrics"}).text)


if __name__ == "__main__":
    unittest.main()
