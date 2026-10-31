"""Independent numerical, parser, subprocess, and session-state evidence."""
import base64
import csv
import importlib.util
import io
import json
from pathlib import Path
import sys
import threading
import time
import unittest
from unittest.mock import patch
import numpy as np
from bokeh.document import Document
from bokeh.events import ButtonClick
from sklearn.model_selection import train_test_split

ROOT=Path(__file__).resolve().parents[1]
NAME='_neural_equation_tests'
spec=importlib.util.spec_from_file_location(NAME,ROOT/'__init__.py',submodule_search_locations=[str(ROOT)])
package=importlib.util.module_from_spec(spec);sys.modules[NAME]=package;spec.loader.exec_module(package)
engine=__import__(NAME+'.engine',fromlist=['*'])
worker=__import__(NAME+'.worker',fromlist=['*'])
ui=__import__(NAME+'.ui',fromlist=['*'])


def text_for(X,y,headers=None):
    X=np.asarray(X)
    if X.ndim==1: X=X[:,None]
    headers=headers or [f'x{i+1}' for i in range(X.shape[1])]+['target']
    stream=io.StringIO();writer=csv.writer(stream);writer.writerow(headers)
    writer.writerows([*r,t] for r,t in zip(X,y))
    return stream.getvalue()


def linear_data():
    x=np.linspace(-2,2,300)
    return engine.prepare_data(engine.parse_csv(text_for(x,2*x+1)),['x1'],'target')


LINEAR=dict(hidden_layers=(8,),activation='identity',solver='lbfgs',alpha=0,max_iter=1000,equation_degree=1,seed=42,test_fraction=.2)
QUADRATIC=dict(hidden_layers=(32,32),activation='tanh',solver='lbfgs',alpha=1e-6,max_iter=2000,equation_degree=2,seed=42,test_fraction=.2)


class ParserConfigTests(unittest.TestCase):
    def test_selected_cleaning_unselected_columns_and_infinity(self):
        table=engine.parse_csv(' x , y , ignored\n'+'\n'.join(f'{i},{2*i},text' for i in range(25))+'\nmissing,4,inf\n2,NaN,hello')
        data=engine.prepare_data(table,['x'],'y')
        self.assertEqual(data.dropped,2);self.assertEqual(len(data.y),25)
        inf=engine.parse_csv('x,y\n'+'\n'.join(f'{i},{i}' for i in range(20))+'\ninf,broken')
        with self.assertRaisesRegex(ValueError,'infinity'): engine.prepare_data(inf,['x'],'y')
        with self.assertRaisesRegex(ValueError,'infinity'): engine.prepare_data(engine.parse_csv('x,y\n'+'\n'.join(f'{i},{i}' for i in range(20))+'\n1e9999,2'),['x'],'y')

    def test_parser_boundaries_and_unsafe_input(self):
        valid=text_for(np.arange(20),np.arange(20))
        self.assertEqual(len(engine.parse_csv(('\ufeff'+valid).encode()).rows),20)
        invalid=['',valid.replace('x1,target','x1,x1'),valid.replace('x1,target',',target'),valid+'1,2,3\n',valid+'\x00', 'x,y\n"unclosed,2', 'a,b\n'+'1,2\n'*19, 'a,b\n'+'1,2\n'*5001, 'a,b\n'+' '*5_000_001, b'\xff', ','.join(str(i) for i in range(101))+'\n']
        for text in invalid:
            with self.subTest(case=str(text)[:40]),self.assertRaises(ValueError): engine.parse_csv(text)

    def test_selection_constants_and_insufficient_rows(self):
        table=engine.parse_csv(text_for(np.arange(20),np.arange(20)))
        for features,target in (([],'target'),(['x1','x1'],'target'),(['target'],'target'),(['unknown'],'target')):
            with self.assertRaises(ValueError):engine.prepare_data(table,features,target)
        with self.assertRaisesRegex(ValueError,'constant'):
            engine.prepare_data(engine.parse_csv(text_for(np.ones(20),np.arange(20))),['x1'],'target')
        with self.assertRaisesRegex(ValueError,'usable'):
            engine.prepare_data(engine.parse_csv('x,y\n'+'nope,1\n'*20),['x'],'y')

    def test_config_bounds_and_solver_parameters(self):
        for key,values in dict(hidden_layers=['',[],[1,2,3,4],[257],[True]],activation=['bad'],solver=['bad'],alpha=[-1,np.nan,11],learning_rate=[0,2],max_iter=[0,2001,1.5,True],test_fraction=[0,.5],equation_degree=[0,5],seed=[-1,2**32,True]).items():
            for value in values:
                with self.subTest(key=key,value=value),self.assertRaises(ValueError):engine.validate_config({key:value})
        with self.assertRaises(ValueError):engine.validate_config({'unknown':1})
        seen=[]
        real=engine.MLPRegressor
        def factory(**kwargs):seen.append(kwargs);return real(**kwargs)
        with patch.object(engine,'MLPRegressor',side_effect=factory):
            engine.fit_model(linear_data(),{**LINEAR,'solver':'adam','learning_rate':.02,'max_iter':2})
        actual=seen[0]
        self.assertEqual(actual['learning_rate_init'],.02)
        self.assertEqual(actual['loss'],'squared_error')
        self.assertEqual(actual['hidden_layer_sizes'],(8,))
        self.assertEqual(actual['tol'],1e-6)
        self.assertFalse(actual['early_stopping']);self.assertFalse(actual['warm_start'])
        self.assertEqual(actual['n_iter_no_change'],20);self.assertEqual(actual['max_fun'],20000)


class ScienceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=linear_data();cls.result=engine.fit_model(cls.data,LINEAR)

    def test_predeclared_linear_fixture(self):
        r=self.result
        self.assertGreaterEqual(r['test_r2'],.9999);self.assertLessEqual(r['test_rmse'],.02)
        self.assertGreaterEqual(r['fidelity_r2'],.99999)
        self.assertAlmostEqual(r['coefficients'][0],1,delta=.02)
        self.assertAlmostEqual(r['coefficients'][1],2,delta=.02)

    def test_train_scalers_and_held_out_perturbation(self):
        r=self.result;idx=np.array(r['train_idx']);test=np.array(r['test_idx'])
        self.assertEqual(set(idx)&set(test),set());self.assertEqual(set(idx)|set(test),set(range(300)))
        np.testing.assert_allclose(r['scaler_state']['x_mean'],self.data.X[idx].mean(axis=0))
        np.testing.assert_allclose(r['scaler_state']['x_scale'],self.data.X[idx].std(axis=0))
        np.testing.assert_allclose(r['scaler_state']['y_mean'],[self.data.y[idx].mean()])
        np.testing.assert_allclose(r['scaler_state']['y_scale'],[self.data.y[idx].std()])
        y=self.data.y.copy();y[test]+=100
        altered=engine.PreparedData(self.data.X,y,self.data.features,self.data.target,0,self.data.row_indices)
        a=engine.fit_model(altered,LINEAR)
        np.testing.assert_allclose(r['predictions'],a['predictions'],atol=1e-12)
        self.assertEqual(r['scaler_state'],a['scaler_state'])
        self.assertGreater(a['test_rmse'],90)

    def test_repeatability_and_independent_metrics_and_polynomial(self):
        r=self.result;again=engine.fit_model(self.data,LINEAR)
        np.testing.assert_allclose(r['predictions'],again['predictions'],atol=1e-12)
        pred=np.array(r['predictions']);y=self.data.y;idx=np.array(r['test_idx'])
        errors=y-pred
        np.testing.assert_allclose(r['residuals'],errors)
        self.assertAlmostEqual(r['test_rmse'],(sum(float(errors[i])**2 for i in idx)/len(idx))**.5,places=12)
        r2=1-sum(float(errors[i])**2 for i in idx)/sum(float(y[i]-y[idx].mean())**2 for i in idx)
        self.assertAlmostEqual(r['test_r2'],r2,places=12)
        manual=[]
        for row in self.data.X:
            value=0
            for coef,powers in zip(r['coefficients'],r['powers']):
                term=coef
                for x,power in zip(row,powers):term*=float(x)**power
                value+=term
            manual.append(value)
        np.testing.assert_allclose(manual,r['surrogate_predictions'],atol=1e-12)
        nn=pred[idx];eq=np.array(manual)[idx]
        fidelity=1-sum(float(a-b)**2 for a,b in zip(nn,eq))/sum(float(a-nn.mean())**2 for a in nn)
        self.assertAlmostEqual(r['fidelity_r2'],fidelity,places=12)
        self.assertIsNone(engine._r2(np.ones(3),np.zeros(3)))
        # Format with 17 significant digits retains executable coefficients.
        expression=r['equation'].split(' = ',1)[1].replace('^','**')
        displayed=[eval(expression,{'__builtins__':{}},{'x1':float(x[0])}) for x in self.data.X]
        np.testing.assert_allclose(displayed,manual,atol=1e-12)

    def test_predeclared_quadratic_fixture(self):
        x=np.linspace(-2,2,300);y=.5*x*x-1.2*x+.7
        data=engine.prepare_data(engine.parse_csv(text_for(x,y)),['x1'],'target')
        r=engine.fit_model(data,QUADRATIC)
        self.assertGreaterEqual(r['test_r2'],.995);self.assertLessEqual(r['test_rmse'],.08)
        self.assertGreaterEqual(r['fidelity_r2'],.995)
        np.testing.assert_allclose(r['coefficients'],[.7,-1.2,.5],atol=.08)

    def test_multifeature_and_loss_semantics(self):
        X=np.random.default_rng(4).uniform(-1,1,(400,3));y=1+2*X[:,0]-.5*X[:,1]+X[:,2]**2
        data=engine.prepare_data(engine.parse_csv(text_for(X,y)),['x1','x2','x3'],'target')
        r=engine.fit_model(data,{**LINEAR,'activation':'tanh','hidden_layers':(16,), 'equation_degree':2})
        self.assertEqual(r['curve_x'],[]);self.assertEqual(r['loss'],[])
        self.assertTrue(np.all(np.isfinite(r['predictions'])))
        adam=engine.fit_model(self.data,{**LINEAR,'solver':'adam','max_iter':5})
        self.assertEqual(len(adam['loss']),5)


class WorkerUITests(unittest.TestCase):
    def test_real_worker_result_and_failure(self):
        for payload,expected in ((dict(csv=text_for(np.arange(30),2*np.arange(30)+1),features=['x1'],target='target',config=LINEAR),True),(dict(csv='bad',features=[],target='x',config=LINEAR),False)):
            done=threading.Event();messages=[]
            job=worker.WorkerJob(payload,lambda m:(messages.append(m),done.set())).start()
            self.assertTrue(done.wait(30))
            job.thread.join(2)
            self.assertEqual(messages[0]['ok'],expected)
            self.assertIsNotNone(job.process.poll())

    def test_worker_timeout_and_cancel(self):
        done=threading.Event();messages=[]
        job=worker.WorkerJob({},lambda m:(messages.append(m),done.set()),timeout=.000001).start()
        self.assertTrue(done.wait(10));job.thread.join(2)
        self.assertFalse(messages[0]['ok']);self.assertIn('timeout',messages[0]['error'])
        self.assertIsNotNone(job.process.poll())
        job2=worker.WorkerJob({},lambda m:self.fail('Cancelled job must not publish'))
        job2.cancel();job2.start();job2.thread.join(3)
        self.assertIsNone(job2.process)

    def test_cancel_running_process_reaps_it_without_publication(self):
        # Import startup alone is enough to keep this child alive while cancelling.
        messages=[]
        job=worker.WorkerJob({},messages.append).start()
        deadline=time.monotonic()+3
        while job.process is None and time.monotonic()<deadline: time.sleep(.005)
        self.assertIsNotNone(job.process)
        job.cancel();job.thread.join(5)
        self.assertFalse(job.thread.is_alive())
        self.assertIsNotNone(job.process.poll())
        self.assertEqual(messages,[])

    def test_two_documents_upload_solver_busy_success_and_failure(self):
        class FakeJob:
            instances=[]
            def __init__(self,payload,done):self.payload=payload;self.done=done;self.cancelled=False;self.instances.append(self)
            def start(self):return self
            def cancel(self):self.cancelled=True
        a,b=Document(),Document()
        with patch.object(ui,'WorkerJob',FakeJob):
            ui.build_document(a);ui.build_document(b)
            self.assertFalse(set(a.models)&set(b.models))
            def model(doc,name):return doc.select_one({'name':name})
            model(a,'solver').value='adam'
            self.assertFalse(model(a,'learning_rate').disabled)
            model(a,'solver').value='lbfgs';self.assertTrue(model(a,'learning_rate').disabled)
            uploaded=base64.b64encode(text_for(np.arange(30),2*np.arange(30)+1,['new_feature','new_target']).encode()).decode()
            model(a,'upload').set_from_json('value',uploaded)
            self.assertEqual(model(a,'target').value,'new_target')
            self.assertEqual(model(b,'target').value,'target')
            button=model(a,'train');button._trigger_event(ButtonClick(model=button))
            self.assertTrue(button.disabled);self.assertIn('Training',model(a,'status').text)
            button._trigger_event(ButtonClick(model=button));self.assertEqual(len(FakeJob.instances),1)
            job=FakeJob.instances[-1]
            table=engine.parse_csv(job.payload['csv']);data=engine.prepare_data(table,job.payload['features'],job.payload['target'])
            r=engine.fit_model(data,LINEAR)
            job.done(dict(ok=True,result=r))
            for callback in list(a.session_callbacks):
                if callback.__class__.__name__=='NextTickCallback':
                    a.remove_next_tick_callback(callback);callback.callback()
            self.assertEqual(len(model(a,'observations').data['x']),30)
            self.assertEqual(len(model(a,'nn_curve').data['x']),250)
            self.assertIn('NN test R²',model(a,'metrics').text)
            self.assertEqual(len(model(b,'observations').data['x']),0)
            old_metrics=model(a,'metrics').text
            model(a,'alpha').value=.1
            self.assertIn('pending',model(a,'status').text)
            button._trigger_event(ButtonClick(model=button))
            FakeJob.instances[-1].done(dict(ok=False,error='Controlled failure'))
            for callback in list(a.session_callbacks):
                if callback.__class__.__name__=='NextTickCallback':
                    a.remove_next_tick_callback(callback);callback.callback()
            self.assertEqual(model(a,'metrics').text,old_metrics)
            self.assertIn('failed',model(a,'status').text)


if __name__=='__main__':unittest.main()
