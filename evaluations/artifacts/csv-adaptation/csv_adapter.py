"""Isolated numerical CSV-text evaluation fixture; no browser upload UI.

CSV observations have no known generating noise. Dataset.standard_noise is a
zero compatibility placeholder and must not be interpreted as inferred noise.
The shipped engine supplies all regression, residual, and MSE calculations.
"""
import csv
import importlib.util
import io
from numbers import Integral
from pathlib import Path
import sys
import numpy as np

_ENGINE_PATH = Path(__file__).resolve().parents[3] / "modules/linear-regression/engine.py"
_ENGINE_NAME = "_csv_adaptation_shipped_regression_engine"
if _ENGINE_NAME not in sys.modules:
    _spec = importlib.util.spec_from_file_location(_ENGINE_NAME, _ENGINE_PATH)
    _engine = importlib.util.module_from_spec(_spec)
    sys.modules[_ENGINE_NAME] = _engine
    _spec.loader.exec_module(_engine)
else:
    _engine = sys.modules[_ENGINE_NAME]
Dataset = _engine.Dataset
fit_and_evaluate = _engine.fit_and_evaluate


def parse_csv(text, seed=42):
    """Read exact x,y headers and 20–300 finite numeric rows, preserving order.

    A fresh RNG permutes row indices; first floor(.75*n) rows train. The
    scientific engine separately checks whether training x has sufficient rank.
    """
    if not isinstance(text, str):
        raise ValueError("CSV input must be an in-memory text string.")
    if isinstance(seed, (bool, np.bool_)) or not isinstance(seed, Integral) or not 0 <= seed <= _engine.MAX_SEED:
        raise ValueError(f"seed must be an integer from 0 to {_engine.MAX_SEED}.")
    rows = []
    try:
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        if next(reader, None) != ["x", "y"]:
            raise ValueError("CSV header must be exactly x,y in that order.")
        for number, row in enumerate(reader, start=2):
            if len(rows) == 300:
                raise ValueError("CSV must contain at most 300 data rows.")
            if len(row) != 2:
                raise ValueError(f"CSV row {number} must contain exactly two values.")
            try:
                values = tuple(float(value) for value in row)
            except (ValueError, OverflowError) as exc:
                raise ValueError(f"CSV row {number} must contain numeric x and y.") from exc
            if not all(np.isfinite(value) for value in values):
                raise ValueError(f"CSV row {number} must contain finite x and y.")
            rows.append(values)
    except csv.Error as exc:
        raise ValueError(f"Malformed CSV: {exc}") from exc
    if len(rows) < 20:
        raise ValueError("CSV must contain at least 20 data rows.")
    values = np.asarray(rows, dtype=np.float64)
    n = len(rows)
    permutation = np.random.default_rng(int(seed)).permutation(n)
    boundary = int(.75 * n)
    return Dataset(values[:, 0], values[:, 1], np.zeros(n, dtype=np.float64),
                   permutation[:boundary], permutation[boundary:])


def fit_csv(text, seed=42):
    """Return parsed Dataset and shipped RegressionResult, including residuals."""
    dataset = parse_csv(text, seed)
    return dataset, fit_and_evaluate(dataset)
