"""Validated tabular regression pipeline, independent of Bokeh and servers."""
import csv
from dataclasses import dataclass
import io
import math
import os
from numbers import Integral, Real
import platform
import time
import warnings
import numpy as np
from sklearn import __version__ as sklearn_version
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

MAX_BYTES = 5_000_000
DEFAULTS = dict(hidden_layers=(32,32), activation="tanh", solver="lbfgs", alpha=.0001,
                learning_rate=.001, max_iter=1000, test_fraction=.2, equation_degree=2, seed=42)


@dataclass(frozen=True)
class Table:
    headers: tuple
    rows: tuple


@dataclass(frozen=True)
class PreparedData:
    X: np.ndarray
    y: np.ndarray
    features: tuple
    target: str
    dropped: int
    row_indices: np.ndarray


def parse_csv(content):
    if not isinstance(content, (str,bytes)):
        raise ValueError("Upload CSV text or UTF-8 bytes.")
    try:
        raw = content.encode("utf-8") if isinstance(content,str) else content
        if len(raw)>MAX_BYTES:
            raise ValueError("CSV exceeds the 5 MB decoded limit.")
        text=raw.decode("utf-8-sig")
    except UnicodeError as exc:
        raise ValueError("CSV must be valid UTF-8.") from exc
    if "\x00" in text:
        raise ValueError("CSV contains a NUL character.")
    try:
        reader=csv.reader(io.StringIO(text,newline=""),strict=True)
        header=next(reader,None)
        if header is None:
            raise ValueError("CSV needs a header and 20–5,000 data rows.")
        headers=tuple(x.strip() for x in header)
        if not 2<=len(headers)<=100 or any(not x for x in headers) or len(set(headers))!=len(headers):
            raise ValueError("Use 2–100 unique, nonempty column headers.")
        rows=[]
        for i,row in enumerate(reader,start=2):
            if len(rows)>=5000:
                raise ValueError("CSV exceeds 5,000 data rows.")
            if len(row)!=len(headers):
                raise ValueError(f"Row {i} has {len(row)} fields; expected {len(headers)}.")
            rows.append(tuple(row))
    except csv.Error as exc:
        raise ValueError(f"Malformed CSV: {exc}") from exc
    if len(rows)<20:
        raise ValueError("CSV needs at least 20 data rows.")
    return Table(headers,tuple(rows))


def prepare_data(table, features, target):
    features=tuple(features)
    if not 1<=len(features)<=4 or len(set(features))!=len(features) or target in features:
        raise ValueError("Choose 1–4 distinct features and a separate target.")
    if any(x not in table.headers for x in features+(target,)):
        raise ValueError("Selected columns must exist in the uploaded CSV.")
    columns=[table.headers.index(x) for x in features+(target,)]
    kept=[]; indices=[]
    for i,row in enumerate(table.rows):
        values=[]; missing=False
        for name,col in zip(features+(target,),columns):
            try:
                value=float(row[col])
            except (ValueError,TypeError):
                missing=True
                continue
            if math.isinf(value):
                raise ValueError(f"Row {i+2}, column {name}: infinity or numeric overflow is not supported.")
            if math.isnan(value):
                missing=True
            values.append(value)
        if not missing:
            kept.append(values); indices.append(i)
    if len(kept)<20:
        raise ValueError(f"Only {len(kept)} usable rows; at least 20 are required.")
    values=np.asarray(kept,dtype=np.float64)
    for j,name in enumerate(features+(target,)):
        if np.all(values[:,j]==values[0,j]):
            raise ValueError(f"Selected column {name} is constant.")
    return PreparedData(values[:,:-1],values[:,-1],features,target,len(table.rows)-len(kept),np.asarray(indices))


def validate_config(config=None, feature_count=1):
    supplied={} if config is None else dict(config)
    if set(supplied)-set(DEFAULTS):
        raise ValueError("Unknown training setting.")
    c={**DEFAULTS,**supplied}
    layers=c['hidden_layers']
    if isinstance(layers,str):
        try: layers=tuple(int(x.strip()) for x in layers.split(','))
        except ValueError as exc: raise ValueError("Hidden layers must be comma-separated integers.") from exc
    if not isinstance(layers,(tuple,list)) or not 1<=len(layers)<=3 or any(isinstance(x,(bool,np.bool_)) or not isinstance(x,Integral) or not 1<=x<=256 for x in layers):
        raise ValueError("Use 1–3 hidden layers with 1–256 units each.")
    c['hidden_layers']=tuple(int(x) for x in layers)
    for key,low,high in (('max_iter',1,2000),('equation_degree',1,4),('seed',0,2**32-1)):
        value=c[key]
        if isinstance(value,(bool,np.bool_)) or not isinstance(value,Integral) or not low<=value<=high:
            raise ValueError(f"{key} must be an integer from {low} to {high}.")
        c[key]=int(value)
    for key,low,high in (('alpha',0,10),('learning_rate',1e-6,1),('test_fraction',.1,.4)):
        value=c[key]
        if isinstance(value,(bool,np.bool_)) or not isinstance(value,Real) or not np.isfinite(value) or not low<=value<=high:
            raise ValueError(f"{key} must be finite and between {low} and {high}.")
        c[key]=float(value)
    if c['activation'] not in ('identity','logistic','tanh','relu') or c['solver'] not in ('lbfgs','adam','sgd'):
        raise ValueError("Choose a supported activation and solver.")
    if not 1<=feature_count<=4 or math.comb(feature_count+c['equation_degree'],c['equation_degree'])>100:
        raise ValueError("The polynomial must have at most 100 terms and 1–4 features.")
    return c


def evaluate_polynomial(X, coefficients, powers):
    X=np.asarray(X,dtype=np.float64)
    coefficients=np.asarray(coefficients,dtype=np.float64)
    powers=np.asarray(powers)
    if X.ndim!=2 or powers.ndim!=2 or powers.shape[1]!=X.shape[1] or len(coefficients)!=len(powers):
        raise ValueError("Polynomial dimensions do not agree.")
    if powers.dtype.kind not in 'iu' or np.any(powers<0):
        raise ValueError("Polynomial powers must be nonnegative integers.")
    with np.errstate(over='ignore',invalid='ignore'):
        result=np.prod(X[:,None,:]**powers[None,:,:],axis=2)@coefficients
    if not np.all(np.isfinite(result)):
        raise ValueError("Polynomial evaluation overflowed; rescale the data.")
    return result


def format_equation(coefficients,powers):
    parts=[]
    for coefficient,power in zip(coefficients,powers):
        factors=[f"x{i+1}"+(f"^{p}" if p!=1 else '') for i,p in enumerate(power) if p]
        parts.append(f"{float(coefficient):+.17g}"+('*'+'*'.join(factors) if factors else ''))
    return 'y = '+ ' '.join(parts)


def _r2(reference,prediction):
    if np.all(reference==reference[0]): return None
    score=1-float(np.sum((reference-prediction)**2)/np.sum((reference-np.mean(reference))**2))
    return score if np.isfinite(score) else None


def fit_model(data,config=None):
    started=time.perf_counter()
    c=validate_config(config,data.X.shape[1])
    if data.X.ndim!=2 or data.y.ndim!=1 or len(data.X)!=len(data.y) or not 20<=len(data.y)<=5000 or not np.all(np.isfinite(data.X)) or not np.all(np.isfinite(data.y)):
        raise ValueError("Training data must have 20–5,000 aligned finite rows.")
    train,test=train_test_split(np.arange(len(data.y)),test_size=c['test_fraction'],random_state=c['seed'],shuffle=True)
    for values in (data.X[train],data.y[train,None]):
        if np.any(np.all(values==values[0],axis=0)):
            raise ValueError("A selected feature or target is constant in training rows.")
    sx=StandardScaler().fit(data.X[train]); sy=StandardScaler().fit(data.y[train,None])
    X=sx.transform(data.X); y=sy.transform(data.y[:,None]).ravel()
    if not np.all(np.isfinite(X)) or not np.all(np.isfinite(y)):
        raise ValueError("Standardization produced nonfinite values; rescale the input data.")
    nn=MLPRegressor(loss='squared_error',hidden_layer_sizes=c['hidden_layers'],activation=c['activation'],solver=c['solver'],alpha=c['alpha'],learning_rate_init=c['learning_rate'],max_iter=c['max_iter'],random_state=c['seed'],tol=1e-6,early_stopping=False,warm_start=False,n_iter_no_change=20,max_fun=20000)
    fit_start=time.perf_counter()
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter('always')
        nn.fit(X[train],y[train])
    fit_seconds=time.perf_counter()-fit_start
    pred=sy.inverse_transform(nn.predict(X)[:,None]).ravel()
    residual=data.y-pred
    poly=PolynomialFeatures(c['equation_degree'],include_bias=True)
    with np.errstate(over='ignore',invalid='ignore'):
        design=poly.fit_transform(data.X[train])
    if not np.all(np.isfinite(design)):
        raise ValueError("Polynomial design overflowed; rescale the data.")
    coefficients,_,rank,singular=np.linalg.lstsq(design,pred[train],rcond=None)
    surrogate=evaluate_polynomial(data.X,coefficients,poly.powers_)
    if not np.all(np.isfinite(pred)) or not np.all(np.isfinite(residual)):
        raise ValueError("The neural network produced nonfinite outputs.")
    rmse=float(np.sqrt(np.mean(residual[test]**2)))
    if not np.isfinite(rmse): raise ValueError("Test metric overflowed; rescale the data.")
    curve_x=[]; curve_nn=[]; curve_eq=[]
    if data.X.shape[1]==1:
        grid=np.linspace(float(data.X.min()),float(data.X.max()),250)[:,None]
        curve_x=grid[:,0].tolist()
        curve_nn=sy.inverse_transform(nn.predict(sx.transform(grid))[:,None]).ravel().tolist()
        curve_eq=evaluate_polynomial(grid,coefficients,poly.powers_).tolist()
        if not np.all(np.isfinite(curve_nn)): raise ValueError("Neural curve is nonfinite.")
    split=np.full(len(data.y),'train',dtype=object);split[test]='test'
    loss=getattr(nn,'loss_curve_',[])
    if not np.all(np.isfinite(loss)): raise ValueError("Training objective is nonfinite.")
    return dict(config=c,features=list(data.features),target=data.target,rows_used=len(data.y),rows_dropped=data.dropped,
                train_idx=train.tolist(),test_idx=test.tolist(),X=data.X.tolist(),y=data.y.tolist(),predictions=pred.tolist(),
                residuals=residual.tolist(),split=split.tolist(),test_r2=_r2(data.y[test],pred[test]),test_rmse=rmse,
                fidelity_r2=_r2(pred[test],surrogate[test]),surrogate_predictions=surrogate.tolist(),
                coefficients=coefficients.tolist(),powers=poly.powers_.tolist(),equation=format_equation(coefficients,poly.powers_),
                polynomial_rank=int(rank),polynomial_terms=len(coefficients),polynomial_condition=float(singular[0]/singular[-1]) if singular[-1]>0 and np.isfinite(singular[0]/singular[-1]) else None,
                curve_x=curve_x,curve_nn=curve_nn,curve_equation=curve_eq,loss=list(loss),iterations=int(nn.n_iter_),
                fit_seconds=fit_seconds,pipeline_seconds=time.perf_counter()-started,warnings=[str(w.message) for w in captured],
                scaler_state=dict(x_mean=sx.mean_.tolist(),x_scale=sx.scale_.tolist(),y_mean=sy.mean_.tolist(),y_scale=sy.scale_.tolist()),
                model_state=dict(coefs=[v.tolist() for v in nn.coefs_],intercepts=[v.tolist() for v in nn.intercepts_]),
                context=dict(python=platform.python_version(),sklearn=sklearn_version,numpy=np.__version__,hardware=platform.platform(),processor=platform.processor(),device='CPU',thread_limit=os.environ.get('OPENBLAS_NUM_THREADS','not enforced in direct engine calls')))
