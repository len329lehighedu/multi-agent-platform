"""Explicit worker benchmark; not part of automatic unittest discovery."""
import importlib.util
import json
from pathlib import Path
import sys
import threading
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('benchmark_worker',ROOT/'worker.py')
worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)


def run(name,X,y,config):
    if X.ndim==1:X=X[:,None]
    features=[f'x{i+1}' for i in range(X.shape[1])]
    csv=','.join(features+['target'])+'\n'+'\n'.join(','.join(f'{v:.17g}' for v in [*x,t]) for x,t in zip(X,y))
    finished=threading.Event();messages=[]
    job=worker.WorkerJob(dict(csv=csv,features=features,target='target',config=config),lambda m:(messages.append(m),finished.set())).start()
    if not finished.wait(125):job.cancel();raise RuntimeError('Worker monitor failed to return')
    job.thread.join(3)
    message=messages[0]
    if message['ok']:
        r=message['result']
        message=dict(name=name,ok=True,**{key:r[key] for key in ('rows_used','config','test_r2','test_rmse','fidelity_r2','coefficients','iterations','fit_seconds','pipeline_seconds','worker_seconds','warnings','context')})
    else:message['name']=name
    print(json.dumps(message),flush=True)


if __name__=='__main__':
    x=np.linspace(-2,2,300)
    run('linear',x,2*x+1,dict(hidden_layers=[8],activation='identity',solver='lbfgs',alpha=0,max_iter=1000,equation_degree=1,seed=42,test_fraction=.2))
    run('quadratic',x,.5*x*x-1.2*x+.7,dict(hidden_layers=[32,32],activation='tanh',solver='lbfgs',alpha=1e-6,max_iter=2000,equation_degree=2,seed=42,test_fraction=.2))
    X=np.random.default_rng(4).uniform(-1,1,(400,3))
    run('multifeature',X,1+2*X[:,0]-.5*X[:,1]+X[:,2]**2,dict(hidden_layers=[32,32],activation='tanh',solver='lbfgs',alpha=1e-6,max_iter=1000,equation_degree=2,seed=42,test_fraction=.2))
    X=np.random.default_rng(9).uniform(-1,1,(5000,4))
    run('stress',X,1+2*X[:,0]-.5*X[:,1]+X[:,2]**2+X[:,3],dict(hidden_layers=[32,32],activation='tanh',solver='lbfgs',alpha=.0001,max_iter=1000,equation_degree=2,seed=42,test_fraction=.2))
