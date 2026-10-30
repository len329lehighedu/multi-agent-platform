# Linear regression pilot

Explore one-feature ordinary least squares with an intercept, noise, residuals, and held-out test error. Designed for introductory undergraduates with algebra and graph-reading prerequisites; faculty review is pending.

From the repository root, use the shared environment and launcher:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r modules/linear-regression/requirements.txt
.venv/bin/python scripts/serve.py
```

Open `http://127.0.0.1:8080/modules/linear-regression/`. Both the Flask shell and the Bokeh server at port 5006 must be reachable by the browser. This is a local development app. Shared launcher/lifecycle verification is recorded in the run's QA evidence, separately from this module's construction checks.

Use the noise, sample-count, and seed controls, then click **Generate and fit**. Edits are pending until this button commits a run. Metrics retain the configuration of the plotted run. Train rows are circles; test rows are triangles. The fitted line uses training rows only. The dashed line is the known generating relationship `y = 2x + 1`. Residuals are `y − prediction`, and separate train/test MSE averages their squares.

Default data: 100 evenly spaced dimensionless x values on [0,10], Gaussian noise σ=1, seed 42, 75 training/25 test rows. Noise is restricted to [0,5], n to integer [20,300], and seeds to integer [0,4294967295]. The generator draws standard-normal noise before permuting row indices; with the same seed and n, changing σ keeps draws and split fixed. Changing n can change the realization. Zero noise recovers slope 2/intercept 1 within numerical tolerance. For fixed seed and n, the exactly linear generating truth means residuals scale with σ and both train/test MSE scale with σ², apart from floating-point roundoff: doubling σ quadruples MSE. Comparisons across different random realizations, seeds, or splits need not be monotonic in noise. Training and test errors have no guaranteed ordering.

`engine.py` is independent of Bokeh. `Dataset` contains aligned finite one-dimensional arrays `x`, `y`, `standard_noise` plus disjoint/exhaustive integer `train_idx`, `test_idx`. `fit_and_evaluate` rejects malformed partitions and rank-deficient training designs. It returns coefficients, predictions/residuals for every row, and separate MSEs. No preprocessing, uploads, uncertainty estimates, or neural training are involved.

Run module checks from the repository root:

```sh
.venv/bin/python -m unittest discover -s modules/linear-regression/tests -v
```

The tests use an independent centered-sums regression oracle, held-out response perturbation, zero-noise recovery, seed/noise comparisons, invalid inputs, Bokeh callbacks, and two independent Documents. Actual browser interaction, narrow viewport rendering, and two browser sessions require separate QA; Document checks alone do not prove those behaviors.

Implementation evidence and source adaptation are in `runs/mvp-completion-20261030/regression-build-report.md`. The existing SINDy sources were inspected for patterns and left unchanged; this module is newly authored and is not an approved corpus exemplar.
