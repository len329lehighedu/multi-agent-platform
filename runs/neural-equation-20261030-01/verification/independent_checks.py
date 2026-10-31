"""Independent QA: reference calculations and metamorphic leakage checks."""
import csv
from dataclasses import replace
import importlib.util
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('qa_neural_engine',ROOT/'modules/neural-equation-finder/engine.py')
e=importlib.util.module_from_spec(spec);sys.modules[spec.name]=e;spec.loader.exec_module(e)
LINEAR=dict(hidden_layers=(8,),activation='identity',solver='lbfgs',alpha=0,max_iter=1000,equation_degree=1,seed=42,test_fraction=.2)
QUAD=dict(hidden_layers=(32,32),activation='tanh',solver='lbfgs',alpha=1e-6,max_iter=2000,equation_degree=2,seed=42,test_fraction=.2)

def csv_text(X,y):
    X=np.asarray(X)
    if X.ndim==1:X=X[:,None]
    out=io.StringIO();w=csv.writer(out);w.writerow([f'f{i}' for i in range(X.shape[1])]+['response'])
    w.writerows([*x,v] for x,v in zip(X,y));return out.getvalue()

def data(X,y):
    X=np.asarray(X)
    names=['f0'] if X.ndim==1 else [f'f{i}' for i in range(X.shape[1])]
    return e.prepare_data(e.parse_csv(csv_text(X,y)),names,'response')

def manual_prediction(r,X):
    z=(np.asarray(X)-r['scaler_state']['x_mean'])/r['scaler_state']['x_scale']
    for k,(w,b) in enumerate(zip(r['model_state']['coefs'],r['model_state']['intercepts'])):
        z=z@np.asarray(w)+b
        if k<len(r['model_state']['coefs'])-1:
            activation=r['config']['activation']
            if activation=='tanh':z=np.tanh(z)
            elif activation=='logistic':z=1/(1+np.exp(-z))
            elif activation=='relu':z=np.maximum(z,0)
    return z.ravel()*r['scaler_state']['y_scale'][0]+r['scaler_state']['y_mean'][0]

class IndependentChecks(unittest.TestCase):
    def test_csv_cleaning_and_rejections(self):
        good='feature,target,unused\n'+'\n'.join(f'{i},{3*i-2},not numeric' for i in range(27))
        table=e.parse_csv('\ufeff'+good+'\n,5,inf\n3,NaN,text\nno,4,text')
        d=e.prepare_data(table,['feature'],'target')
        self.assertEqual((len(d.y),d.dropped),(27,3));np.testing.assert_array_equal(d.row_indices,np.arange(27))
        for extra in ('inf,broken,text','broken,-inf,text','1e9999,2,text'):
            with self.assertRaisesRegex(ValueError,'Row.*column.*infinity'):
                e.prepare_data(e.parse_csv(good+'\n'+extra),['feature'],'target')
        for raw in ('',good.replace('feature,target,unused','x,x,unused'),good+'\n1,2',good+'\x00',b'\xff','a,b\n'+'1,2\n'*5001,'a,b\n'+'1,2\n'*19,'a,b\n"unterminated,2'):
            with self.subTest(raw=str(raw)[:40]),self.assertRaises(ValueError):e.parse_csv(raw)
        with self.assertRaises(ValueError):e.parse_csv(b'x,y\n'+b' '*5_000_000)
        for features,target in ((['feature','feature'],'target'),(['target'],'target'),(['missing'],'target'),([], 'target')):
            with self.assertRaises(ValueError):e.prepare_data(table,features,target)
        with self.assertRaisesRegex(ValueError,'constant'):data(np.ones(25),np.arange(25))

    def test_linear_gate_repeatability_and_leakage(self):
        x=np.linspace(-2,2,300);d=data(x,2*x+1);r=e.fit_model(d,LINEAR);again=e.fit_model(d,LINEAR)
        np.testing.assert_allclose(r['predictions'],again['predictions'],atol=1e-12)
        train=np.array(r['train_idx']);test=np.array(r['test_idx'])
        self.assertFalse(set(train)&set(test));self.assertEqual(set(train)|set(test),set(range(300)))
        np.testing.assert_allclose(r['scaler_state']['x_mean'],[sum(x[train])/len(train)],atol=1e-14)
        np.testing.assert_allclose(r['scaler_state']['x_scale'],[np.sqrt(sum((x[train]-x[train].mean())**2)/len(train))])
        self.assertAlmostEqual(r['scaler_state']['y_mean'][0],d.y[train].mean(),places=12)
        self.assertAlmostEqual(r['scaler_state']['y_scale'][0],d.y[train].std(),places=12)
        poison=d.y.copy();poison[test]+=np.linspace(70,100,len(test))
        changed=e.fit_model(replace(d,y=poison),LINEAR)
        self.assertEqual(r['scaler_state'],changed['scaler_state']);self.assertEqual(r['model_state'],changed['model_state'])
        np.testing.assert_allclose(r['coefficients'],changed['coefficients'],atol=1e-12)
        self.assertGreater(changed['test_rmse'],70)
        self.assertGreaterEqual(r['test_r2'],.9999);self.assertLessEqual(r['test_rmse'],.02);self.assertGreaterEqual(r['fidelity_r2'],.99999)
        np.testing.assert_allclose(r['coefficients'],[1,2],atol=.02)

    def test_quadratic_gate_and_independent_nn_execution(self):
        x=np.linspace(-2,2,300);d=data(x,.5*x*x-1.2*x+.7);r=e.fit_model(d,QUAD)
        self.assertGreaterEqual(r['test_r2'],.995);self.assertLessEqual(r['test_rmse'],.08);self.assertGreaterEqual(r['fidelity_r2'],.995)
        np.testing.assert_allclose(r['coefficients'],[.7,-1.2,.5],atol=.08)
        np.testing.assert_allclose(manual_prediction(r,d.X),r['predictions'],atol=1e-11)

    def test_multifeature_metrics_equation_and_fidelity_oracle(self):
        X=np.random.default_rng(78).uniform(-1.5,2.0,(173,3));y=8-3*X[:,0]+.4*X[:,1]*X[:,2]+np.sin(2*X[:,2])
        d=data(X,y);r=e.fit_model(d,{**QUAD,'hidden_layers':(16,),'max_iter':300})
        p=manual_prediction(r,X);np.testing.assert_allclose(p,r['predictions'],atol=1e-11)
        idx=r['test_idx'];res=y-p;np.testing.assert_allclose(res,r['residuals'],atol=1e-11)
        self.assertAlmostEqual(r['test_rmse'],np.sqrt(sum(float(res[i])**2 for i in idx)/len(idx)),places=11)
        self.assertAlmostEqual(r['test_r2'],1-sum(float(res[i])**2 for i in idx)/sum(float(y[i]-y[idx].mean())**2 for i in idx),places=11)
        eq=[]
        for row in X:
            total=0
            for c,powers in zip(r['coefficients'],r['powers']):
                term=c
                for x,power in zip(row,powers):term*=float(x)**power
                total+=term
            eq.append(total)
        np.testing.assert_allclose(eq,r['surrogate_predictions'],atol=1e-11)
        expr=r['equation'].partition(' = ')[2].replace('^','**')
        rendered=[eval(expr,{'__builtins__':{}},{f'x{i+1}':float(v) for i,v in enumerate(row)}) for row in X]
        np.testing.assert_allclose(rendered,eq,atol=1e-11)
        test_nn=p[idx];test_eq=np.array(eq)[idx]
        self.assertAlmostEqual(r['fidelity_r2'],1-sum((test_nn-test_eq)**2)/sum((test_nn-test_nn.mean())**2),places=11)
        self.assertEqual(r['curve_x'],[]);self.assertEqual(r['loss'],[])
        self.assertIsNone(e._r2(np.ones(4),np.zeros(4)))

    def test_solver_config_forwarding_and_objectives(self):
        x=np.linspace(-3,2,51);d=data(x,4*x-2)
        real=e.MLPRegressor;seen=[]
        def constructor(**kw):seen.append(kw);return real(**kw)
        for solver in ('lbfgs','adam','sgd'):
            cfg={**LINEAR,'hidden_layers':(3,2),'activation':'relu','solver':solver,'alpha':.03,'learning_rate':.017,'max_iter':3,'seed':17}
            with patch.object(e,'MLPRegressor',side_effect=constructor):r=e.fit_model(d,cfg)
            kw=seen[-1]
            for key,expected in {'hidden_layer_sizes':(3,2),'activation':'relu','solver':solver,'alpha':.03,'learning_rate_init':.017,'max_iter':3,'random_state':17,'early_stopping':False,'warm_start':False,'loss':'squared_error'}.items():self.assertEqual(kw[key],expected)
            self.assertTrue(r['warnings'])
            self.assertEqual(len(r['loss']),0 if solver=='lbfgs' else r['iterations'])
            np.testing.assert_allclose(manual_prediction(r,d.X),r['predictions'],atol=1e-11)
        for cfg in ({'hidden_layers':'256,256,256,1'},{'alpha':float('nan')},{'max_iter':2001},{'seed':True},{'equation_degree':5},{'test_fraction':.41}):
            with self.assertRaises(ValueError):e.validate_config(cfg)

if __name__=='__main__':unittest.main(verbosity=2)
