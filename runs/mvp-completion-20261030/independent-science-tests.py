"""Independent QA oracles, authored without using Builder tests as an oracle."""
import importlib.util
import pathlib
import sys
import unittest
import math
import numpy as np
from dataclasses import replace
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    module=importlib.util.module_from_spec(spec); sys.modules[name]=module; spec.loader.exec_module(module); return module
pm=load('qa_projectile','modules/projectile/engine.py')
lr=load('qa_regression','modules/linear-regression/engine.py')
class ScientificQA(unittest.TestCase):
    def test_projectile_component_dynamics_grid(self):
        for v in (0,0.001,5,20,50):
            for a in (0,0.001,15,30,45,60,89.999,90):
                r=pm.trajectory(v,a,samples=202)
                u=v*math.cos(math.radians(a)); w=v*math.sin(math.radians(a))
                T=2*w/9.81
                self.assertAlmostEqual(r.flight_time,T,places=12)
                self.assertAlmostEqual(r.range,u*T,places=11)
                self.assertAlmostEqual(r.max_height,w*w/19.62,places=11)
                np.testing.assert_allclose(r.x,u*r.time,atol=1e-12)
                np.testing.assert_allclose(r.y,w*r.time-4.905*r.time**2,atol=1e-12)
                if T>1e-5:
                    dt=np.diff(r.time)
                    np.testing.assert_allclose(np.diff(r.y)/dt,w-9.81*(r.time[1:]+r.time[:-1])/2,atol=1e-9)
                self.assertTrue(np.isfinite(r.x).all() and np.isfinite(r.y).all())
        self.assertEqual(pm.trajectory(50,90).range,0)
        self.assertTrue((pm.trajectory(50,90).x==0).all())
    def test_projectile_scalings_and_validation(self):
        lo=pm.trajectory(13,37); hi=pm.trajectory(26,37)
        self.assertAlmostEqual(hi.flight_time/lo.flight_time,2)
        self.assertAlmostEqual(hi.range/lo.range,4)
        self.assertAlmostEqual(hi.max_height/lo.max_height,4)
        self.assertAlmostEqual(pm.trajectory(13,53).range,lo.range)
        for value in (-1,51,float('nan'),float('inf'),True,'2',[],complex(2,0)):
            with self.subTest(value=repr(value)),self.assertRaises(ValueError): pm.trajectory(value,45)
        for value in (-1,91,float('nan'),True,'2'):
            with self.assertRaises(ValueError): pm.trajectory(20,value)
        for value in (1,10002,2.0,True,None):
            with self.assertRaises(ValueError): pm.trajectory(20,45,samples=value)
    def test_regression_custom_data_centered_sums_oracle(self):
        # Non-generator relationship, arbitrary partition, nonuniform x: avoids verifying only y=2x+1.
        x=np.linspace(-4,9,37)**3; y=-1.7*x+4.8+np.sin(x)
        test=np.arange(0,37,4); train=np.setdiff1d(np.arange(37),test)
        d=lr.Dataset(x,y,np.zeros(37),train,test); r=lr.fit_and_evaluate(d)
        xt=x[train]; yt=y[train]
        slope=sum((xt-xt.mean())*(yt-yt.mean()))/sum((xt-xt.mean())**2)
        intercept=yt.mean()-slope*xt.mean()
        self.assertAlmostEqual(r.slope,slope,places=12); self.assertAlmostEqual(r.intercept,intercept,places=10)
        pred=slope*x+intercept; residual=y-pred
        np.testing.assert_allclose(r.predictions,pred,atol=1e-10)
        np.testing.assert_allclose(r.residuals,residual,atol=1e-10)
        self.assertAlmostEqual(r.train_mse,sum(residual[train]**2)/len(train),places=10)
        self.assertAlmostEqual(r.test_mse,sum(residual[test]**2)/len(test),places=10)
        poisoned=y.copy(); poisoned[test]+=np.arange(len(test))*1000+500
        altered=lr.fit_and_evaluate(replace(d,y=poisoned))
        self.assertEqual((r.slope,r.intercept,r.train_mse),(altered.slope,altered.intercept,altered.train_mse))
        self.assertGreater(altered.test_mse,r.test_mse)
    def test_seeded_split_and_zero_noise_grid(self):
        for n in (20,21,99,100,299,300):
            for seed in (0,42,4294967295):
                a=lr.generate_data(0,n,seed); b=lr.generate_data(5,n,seed)
                np.testing.assert_array_equal(a.standard_noise,b.standard_noise)
                np.testing.assert_array_equal(a.train_idx,b.train_idx)
                np.testing.assert_array_equal(a.test_idx,b.test_idx)
                self.assertEqual(len(a.train_idx),math.floor(.75*n))
                np.testing.assert_array_equal(np.sort(np.r_[a.train_idx,a.test_idx]),np.arange(n))
                self.assertFalse(set(a.train_idx)&set(a.test_idx))
                r=lr.fit_and_evaluate(a)
                self.assertAlmostEqual(r.slope,2,places=12); self.assertAlmostEqual(r.intercept,1,places=12)
                self.assertLess(max(r.train_mse,r.test_mse),1e-24)
    def test_fixed_noise_scaling_and_repaired_instruction(self):
        for n in (20,67,300):
            a=lr.fit_and_evaluate(lr.generate_data(.7,n,123))
            b=lr.fit_and_evaluate(lr.generate_data(2.1,n,123))
            np.testing.assert_allclose(b.residuals,3*a.residuals,atol=1e-12)
            self.assertAlmostEqual(b.train_mse/a.train_mse,9,places=11)
            self.assertAlmostEqual(b.test_mse/a.test_mse,9,places=11)
        content=(ROOT/'modules/linear-regression/module.json').read_text()
        ui=(ROOT/'modules/linear-regression/ui.py').read_text()
        self.assertIn('same seed',content)
        self.assertIn('different',content)
        self.assertIn('σ²',ui)
    def test_regression_validation(self):
        for args in ((-1,100,42),(6,100,42),(float('nan'),100,42),(True,100,42),(1,19,42),(1,301,42),(1,100.0,42),(1,100,-1),(1,100,4294967296),(1,100,True)):
            with self.subTest(args=args),self.assertRaises(ValueError): lr.generate_data(*args)
        d=lr.generate_data()
        for bad in (replace(d,x=np.zeros(100)),replace(d,y=np.r_[np.nan,d.y[1:]]),replace(d,train_idx=d.test_idx),replace(d,test_idx=np.array([],dtype=int)),replace(d,test_idx=np.array([100])),replace(d,train_idx=d.train_idx.astype(float)),replace(d,y=d.y[:-1])):
            with self.assertRaises(ValueError): lr.fit_and_evaluate(bad)
    def test_document_isolation_and_commit_callbacks(self):
        from bokeh.document import Document
        from bokeh.events import ButtonClick
        from stem_platform.runtime import load_document_builder
        for name in ('projectile','linear-regression'):
            builder=load_document_builder(ROOT,name); one=Document(); two=Document(); builder(one); builder(two)
            self.assertFalse(set(one.models)&set(two.models))
            if name=='projectile':
                before=np.array(two.select_one({'name':'trajectory'}).data['x'])
                one.select_one({'name':'speed'}).value=40
                self.assertGreater(max(one.select_one({'name':'trajectory'}).data['x']),max(before))
                np.testing.assert_array_equal(before,two.select_one({'name':'trajectory'}).data['x'])
            else:
                src=one.select_one({'name':'observations'}); before=np.array(src.data['y'])
                second=np.array(two.select_one({'name':'observations'}).data['y'])
                one.select_one({'name':'noise'}).value=0
                np.testing.assert_array_equal(before,src.data['y'])
                button=one.select_one({'name':'generate'}); button._trigger_event(ButtonClick(model=button))
                np.testing.assert_allclose(src.data['y'],2*np.array(src.data['x'])+1)
                np.testing.assert_array_equal(second,two.select_one({'name':'observations'}).data['y'])
    def test_csv_adapter_independent_roundtrip_and_validation(self):
        import csv, io, inspect
        adapter=load('qa_csv_adapter','evaluations/artifacts/csv-adaptation/csv_adapter.py')
        def text(x,y):
            buffer=io.StringIO(); writer=csv.writer(buffer); writer.writerow(['x','y']); writer.writerows(zip(x,y)); return buffer.getvalue()
        x=np.linspace(-7,14,73); y=3.2*x-9+np.cos(x)
        d,r=adapter.fit_csv(text(x,y),seed=51)
        np.testing.assert_array_equal(d.x,x); np.testing.assert_array_equal(d.y,y)
        tx=x[d.train_idx]; ty=y[d.train_idx]
        a=sum((tx-tx.mean())*(ty-ty.mean()))/sum((tx-tx.mean())**2); b=ty.mean()-a*tx.mean()
        self.assertAlmostEqual(a,r.slope,places=12); self.assertAlmostEqual(b,r.intercept,places=12)
        poisoned=y.copy(); poisoned[d.test_idx]+=10000
        _,other=adapter.fit_csv(text(x,poisoned),seed=51)
        self.assertEqual((r.slope,r.intercept),(other.slope,other.intercept))
        self.assertTrue(inspect.getfile(adapter.fit_and_evaluate).endswith('modules/linear-regression/engine.py'))
        for bad in ('y,x\n'+text(x,y).split('\n',1)[1],text(x,y)+'1,nan\n',text(x,y)+'1,2,3\n',text(range(19),range(19)),text(range(301),range(301))):
            with self.assertRaises(ValueError): adapter.fit_csv(bad)
        with self.assertRaises(ValueError): adapter.fit_csv(text(np.ones(30),range(30)))
if __name__=='__main__': unittest.main(verbosity=2)
