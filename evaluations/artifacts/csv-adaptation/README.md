# CSV adaptation evaluation fixture

This isolated extension evaluates **in-memory CSV text ingestion and scientific residual evaluation** for the shipped linear-regression pipeline. It does not implement a browser upload control or rendered residual comparison, and it is not an approved corpus module. The shipped module is unchanged.

`csv_adapter.py` exports:

- `parse_csv(text, seed=42) -> Dataset`
- `fit_csv(text, seed=42) -> (Dataset, RegressionResult)`

The header must parse as exactly `x,y` in that order, with 20–300 data rows. Each row must contain exactly two finite numbers. Row order is preserved; blank rows, missing/extra columns, duplicate/wrong headers, malformed quoting, nonnumeric cells, and NaN/infinities are rejected. Numeric whitespace is accepted by Python's float parser. Normal CSV quoting and CRLF line endings are supported. Scientific units are supplied by the caller; no normalization or time-series fields are imposed.

An integer seed in [0,4294967295] generates a deterministic row permutation; the first floor(0.75*n) indices train and the rest test. This uses a direct permutation and does not promise the same split as the synthetic generator, which consumes noise draws first. CSV provides no known generating-noise array: `Dataset.standard_noise` contains zero compatibility placeholders, not an estimate that the observations are noiseless.

The adapter imports `Dataset` and `fit_and_evaluate` from the shipped `modules/linear-regression/engine.py`. It contains no OLS implementation. The returned result exposes predictions, signed residuals `y − prediction`, and separate train/test MSE. The shipped engine validates rank and fits training rows only.

Run from the repository root:

```sh
/private/tmp/stem-platform-venv-20261030/bin/python -m unittest discover -s evaluations/artifacts/csv-adaptation/tests -v
```

Evidence and scope limits: `runs/mvp-completion-20261030/csv-adaptation-report.md`.
