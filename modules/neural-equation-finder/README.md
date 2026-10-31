# Neural Equation Finder

A local CSV regression dashboard. A scikit-learn neural network predicts a scalar target; a separate polynomial surrogate approximates the trained network. Strong neural prediction quality or surrogate fidelity does not establish a governing law.

From the platform root, using its locked Python 3.14 environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r modules/neural-equation-finder/requirements.txt
.venv/bin/python scripts/serve.py --module neural-equation-finder
```

Open `http://127.0.0.1:8080/modules/neural-equation-finder/`. The root-owned dashboard integration also opens the sole active module from `/`. Flask and Bokeh both need to be reachable from the browser; Flask HTTP success alone does not prove the live Bokeh connection. Local CPU execution only.

The built-in 300-row quadratic sample opens without training. Upload a CSV, select one target and 1–4 input features, adjust the controls, and click **Train neural network**. A session runs one subprocess at a time. Controls lock while training, and a busy elapsed timer appears. Results commit together; failure preserves previous results. Edits mark prior results pending/stale. The operational timeout is 120 seconds, not a predicted duration. Session destruction and host exit terminate child workers.

CSV contract: UTF-8 (BOM accepted), at most 5,000,000 decoded bytes, 20–5,000 raw rows, and 2–100 columns. Stripped headers must be unique and nonempty; all rows must have the header's field count. NUL characters, malformed CSV, and invalid UTF-8 are rejected. In selected columns, missing/NaN/unparseable values drop the row and are counted. Explicit infinity/overflow rejects the selection with row/column context, even if another selected cell is missing. Unselected cells do not affect usable-row counts. At least 20 usable rows are required; constant selected or training-only features/targets are rejected. No categorical encoding, unit inference, time ordering, classification, differential-equation discovery, or multiple targets are supported.

Training uses a deterministic shuffled split (test fraction .1–.4, seed 0–4294967295). Feature and target `StandardScaler`s fit training rows only. The MLP uses squared error, 1–3 layers of 1–256 units, identity/logistic/tanh/relu activation, lbfgs/adam/sgd solver, L2 alpha 0–10, 1–2,000 iterations, tolerance 1e-6, no early stopping/warm start, and 20 no-improvement iterations for stochastic solvers. lbfgs has max_fun=20000. Learning rate (1e-6–1) applies to adam/sgd; its control is disabled for lbfgs. Convergence warnings and actual iterations are reported. Loss curves are standardized training objectives, including regularization; lbfgs has no curve.

The degree 1–4 polynomial is fitted to **NN predictions on original-unit training inputs**, using float64 least squares. It is not fitted to held-out observed targets. Display aliases x1–x4 map to escaped CSV headers. The dashboard rounds coefficients to four significant digits for readability; exact powers and coefficients remain in the result and drive evaluation. A maximum of 100 terms is enforced (the current four-feature, degree-four bound produces 70). Rank/condition are reported; correlated or badly scaled original features can make coefficients unstable. No uncertainty or causal interpretation is provided.

NN test R²/RMSE compare predictions with observed held-out targets in original target units. RMSE has target units; R² is dimensionless. Equation fidelity R² compares polynomial and NN predictions on held-out inputs. A constant reference makes R² unavailable. Residuals are observed minus NN predicted. One input produces observations plus 250-point NN/equation curves across the observed domain; multiple inputs produce actual versus predicted scatter and an identity line. Circle/triangle shapes distinguish train/test rows. Preview/equation content scrolls inside its card.

`engine.py` exposes `parse_csv`, `prepare_data`, `validate_config`, `fit_model`, `evaluate_polynomial`, and `format_equation`; it creates no servers/Bokeh models. `worker.py` exchanges JSON with a same-interpreter subprocess, never unpickles uploads, and limits numerical library threads to one. Monitor threads never touch Bokeh models; document callbacks publish results. Each session owns its data, controls, worker, generation token, and committed result. There is no cross-session global admission queue; simultaneous sessions can consume multiple CPU workers.

Run verification and the explicit bounded benchmark separately:

```sh
.venv/bin/python -m unittest discover -s modules/neural-equation-finder/tests -v
.venv/bin/python modules/neural-equation-finder/tests/benchmark_fixtures.py
```

Predeclared fixtures: clean linear 300×1, identity/(8,), lbfgs/alpha0/degree1 must reach NN R²≥.9999, RMSE≤.02, fidelity≥.99999, coefficient errors≤.02. Clean quadratic 300×1, tanh/(32,32), lbfgs/alpha1e-6/degree2 must reach NN R²≥.995, RMSE≤.08, fidelity≥.995, coefficient errors≤.08. Both use seed42, test=.2, and max_iter1000/2000 respectively. Independent metrics, coefficient evaluation, leakage, reproducibility, cleaning, worker cancellation/timeout, and Document isolation are tested. Real browser upload, WebSocket, viewport, browser-session isolation, clean install, and host lifecycle require separate QA evidence. Full measured results and source adaptations are in `runs/neural-equation-20261030-01/build-report.md`. No fixed runtime is promised.
