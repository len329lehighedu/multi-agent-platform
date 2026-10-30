"""Pure numerical contract: dimensionless x/y, seeded data, train-only OLS."""
from dataclasses import dataclass
from numbers import Integral, Real
import numpy as np

MAX_SEED = 2**32 - 1


@dataclass(frozen=True)
class Dataset:
    x: np.ndarray
    y: np.ndarray
    standard_noise: np.ndarray
    train_idx: np.ndarray
    test_idx: np.ndarray


@dataclass(frozen=True)
class RegressionResult:
    slope: float
    intercept: float
    predictions: np.ndarray
    residuals: np.ndarray
    train_mse: float
    test_mse: float


def _integer(value, name, low, high):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral) or not low <= value <= high:
        raise ValueError(f"{name} must be an integer from {low} to {high}.")
    return int(value)


def generate_data(noise=1.0, sample_count=100, seed=42):
    """Generate z before the split so changing sigma preserves draws and split."""
    if isinstance(noise, (bool, np.bool_)) or not isinstance(noise, Real) or not np.isfinite(noise) or not 0 <= noise <= 5:
        raise ValueError("noise must be finite and between 0 and 5.")
    n = _integer(sample_count, "sample_count", 20, 300)
    seed = _integer(seed, "seed", 0, MAX_SEED)
    rng = np.random.default_rng(seed)
    x = np.linspace(0, 10, n, dtype=np.float64)
    z = rng.standard_normal(n)
    order = rng.permutation(n)
    boundary = int(.75 * n)
    return Dataset(x, 2 * x + 1 + float(noise) * z, z, order[:boundary], order[boundary:])


def _validate(dataset):
    if not isinstance(dataset, Dataset):
        raise ValueError("Expected a Dataset.")
    arrays = []
    for name in ("x", "y", "standard_noise"):
        raw = np.asarray(getattr(dataset, name))
        if raw.ndim != 1 or raw.dtype.kind not in "fiu" or not np.all(np.isfinite(raw)):
            raise ValueError(f"{name} must be a finite one-dimensional numeric array.")
        arrays.append(raw.astype(np.float64))
    x, y, z = arrays
    n = len(x)
    if not 20 <= n <= 300 or len(y) != n or len(z) != n:
        raise ValueError("Aligned arrays must contain between 20 and 300 rows.")
    indices = []
    for name in ("train_idx", "test_idx"):
        idx = np.asarray(getattr(dataset, name))
        if idx.ndim != 1 or idx.dtype.kind not in "iu" or len(idx) == 0 or np.any(idx < 0) or np.any(idx >= n):
            raise ValueError(f"{name} must contain valid nonempty integer row indices.")
        indices.append(idx.astype(np.int64))
    train, test = indices
    joined = np.concatenate(indices)
    if len(joined) != n or not np.array_equal(np.sort(joined), np.arange(n)):
        raise ValueError("Train/test indices must be disjoint, exhaustive, and contain no duplicates.")
    return x, y, train, test


def fit_and_evaluate(dataset):
    x, y, train, test = _validate(dataset)
    design = np.column_stack((x[train], np.ones(len(train))))
    coefficients, _, rank, _ = np.linalg.lstsq(design, y[train], rcond=None)
    if rank != 2:
        raise ValueError("Training x must vary: the intercept/slope design is rank deficient.")
    slope, intercept = map(float, coefficients)
    predictions = slope * x + intercept
    residuals = y - predictions
    with np.errstate(over="ignore", invalid="ignore"):
        train_mse = float(np.mean(residuals[train] ** 2))
        test_mse = float(np.mean(residuals[test] ** 2))
    if not np.all(np.isfinite(predictions)) or not np.all(np.isfinite(residuals)) or not np.isfinite(train_mse + test_mse):
        raise ValueError("Numerical overflow: data magnitude is too large for finite results.")
    return RegressionResult(slope, intercept, predictions, residuals, train_mse, test_mse)
