# Technical plan - Neural Equation Finder

Run: `neural-equation-20261030-01`  
Producing role: `stem-architect` (native subagent, explicit role/skill assignment)  
Status: ready for implementation; compatibility, thresholds, browser behavior, and timing remain unverified.

## Package and shell

Create `modules/neural-equation-finder/` with standalone `engine.py`, session-local `ui.py`, a subprocess worker, metadata, requirements, tests, and README. Add `presentation: "dashboard"` to metadata handling and render a dedicated compact dashboard shell. The sole active module should open directly from `/`; keep `/modules/neural-equation-finder/`, Bokeh `/lesson/neural-equation-finder`, health, loopback binding, and clean two-endpoint lifecycle.

Add exact candidate `scikit-learn==1.9.1`, then regenerate the installed closure after a real Python 3.14/macOS arm64 install. Scikit-learn 1.8 release notes explicitly document CPython 3.14 support, but only the actual install/import/tests establish this environment. Record `sklearn.show_versions()`.

## Engine contracts

Expose `parse_csv`, `prepare_data`, `validate_config`, `fit_model`, `evaluate_polynomial`, and `format_equation`. Engine imports must not start a server or create Bokeh models.

CSV rules:

- At most 5 MB decoded, 5,000 rows, and 100 columns; 20-row minimum.
- Strict UTF-8 or UTF-8 BOM, headers required, unique nonempty stripped headers, consistent fields, no NUL.
- One target and one-to-four distinct features; target cannot overlap.
- Empty, NaN, or unparseable selected values drop their row. Explicit infinity/overflow rejects the selection with row/column context.
- At least 20 usable rows; reject constant selected and training columns/target and any nonfinite intermediate.

Split once with deterministic `train_test_split`. Fit separate `StandardScaler` instances on X train and y train only. Fit `MLPRegressor` only on standardized training arrays and inverse-transform predictions.

Controls:

| Control | Default | Validation |
| --- | ---: | --- |
| Hidden layers | `32,32` | 1-3 layers, 1-256 units |
| Activation | `tanh` | identity, logistic, tanh, relu |
| Solver | `lbfgs` | lbfgs, adam, sgd |
| L2 alpha | `.0001` | finite, 0-10 |
| Learning rate | `.001` | 1e-6 to 1; only adam/sgd |
| Max iterations | `1000` | 1-2000 |
| Test fraction | `.2` | .1-.4 |
| Equation degree | `2` | 1-4 |
| Seed | `42` | 0 to 2^32-1 |

Use squared error, `tol=1e-6`, `early_stopping=False`, `warm_start=False`, and `n_iter_no_change=20`. For lbfgs bound `max_fun=20000`. Capture convergence warnings. Stochastic solver loss is labeled `Training objective, standardized target`; lbfgs reports no curve.

## Polynomial surrogate

Apply `PolynomialFeatures(degree, include_bias=True)` to original-unit training inputs. Fit float64 least squares from this design matrix to the trained NN's original-unit predictions. Retain `powers_`, coefficients, rank, and condition information. Use those exact powers for executable evaluation and formatting. Display safe aliases `x1` through `x4` and an escaped mapping to original headers. Count all terms and reject above 100.

Report NN test R2/RMSE against observed targets and equation fidelity R2 against NN predictions on test inputs. Residual is observed minus NN prediction. A constant reference makes R2 unavailable. Equation card wording: `Polynomial surrogate - Approximates the neural network; fidelity compares equation and NN predictions.` Neither metric establishes a governing law.

## Worker and committed state

Run each fit in a local subprocess launched with the same interpreter and JSON input/output. Uploaded content is never unpickled. One worker per Bokeh session; Train disables immediately, controls lock, and busy elapsed status appears before results. A background monitor communicates with the process; only next-tick Bokeh callbacks update widgets/sources. Publish all result state atomically.

Apply a 120-second operational timeout. Terminate/join on timeout or session destruction. Ignore stale worker results. Failure keeps the prior committed result and shows a compact error. Limit numerical-library threads to one in the worker. The first build may omit cross-session global admission if per-session/process bounds and host cleanup are verified; record this deviation explicitly.

## Sources, plots, and layout

Stable names: `upload`, `target`, `features`, `hidden_layers`, `activation`, `solver`, `alpha`, `learning_rate`, `max_iter`, `test_fraction`, `equation_degree`, `seed`, `train`, `status`, `metrics`, `equation`, `preview`, `observations`, `nn_curve`, `equation_curve`, `identity_line`, `residuals`, and `loss`.

One feature: observations plus 250-point NN and equation curves across the observed domain. Multiple features: actual-versus-NN-predicted train/test scatter and identity line. Residual plot uses predicted response versus observed-minus-predicted. Loss card is cleared/labeled unavailable for lbfgs.

Dashboard: restrained top bar, data/upload card, compact control card, metric tiles, large main figure, residual/loss cards, and full-width equation card. No lesson rail, assessment, quiz, or gallery prose. All Bokeh layouts use responsive sizing; preview/equation scroll internally; page width must fit 390px.

## Predeclared fixture gates

- Linear: 300 points x in [-2,2], y=2x+1; `(8,)`, identity, lbfgs, alpha 0, max_iter 1000, degree 1, seed 42, split .2. Require NN R2 >= .9999, RMSE <= .02, fidelity >= .99999, slope/intercept within .02.
- Quadratic: same x, y=.5x^2-1.2x+.7; `(32,32)`, tanh, lbfgs, alpha 1e-6, max_iter 2000, degree 2. Require NN R2 >= .995, RMSE <= .08, fidelity >= .995, coefficients within .08.
- Multifeature: seeded 400x3 bounded data, y=1+2x1-.5x2+x3^2; require finite independent evaluation and correct plot mode.
- Stress: seeded 5,000x4 bounded data; record completion or explicit timeout with no partial state.

Measure MLP fit time separately from total pipeline and user-visible time. Record rows/features, solver, requested/actual iterations, Python, sklearn/numerical-library versions, architecture, warnings, thread limit, and hardware. No expected duration is stated in advance.

## Acceptance task map

NE-01 parser/real upload; NE-02 split/scaler/leakage/repeatability; NE-03 actual constructor and solver-specific UI; NE-04 independent original-unit metrics; NE-05 independent powers/coefficient evaluation; NE-06 fixed fixture thresholds; NE-07 browser busy/commit/plot transitions; NE-08 desktop/390px screenshots and overflow; NE-09 two-session isolation; NE-10 fresh install/discovery/WebSocket/lifecycle; NE-11 independent claim review; NE-12 measured timing and complete context.

Builder should implement numerical contracts and fixtures first, then subprocess execution and dashboard state. QA must independently verify uploads, science, worker failure/timeout, actual browser callbacks, isolation, layout, lifecycle, and claims.
