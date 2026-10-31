# Advisor handoff: Neural Equation Finder iteration

Prepared for Minh, Raghu, and faculty review on October 30, 2026. Human acceptance remains pending.

## What changed

The two original pilot modules, projectile motion and linear regression, were removed from the active platform and corpus at Minh's request. Their historical run evidence remains under `runs/mvp-completion-20261030/` for audit. The platform now opens one module directly: **Neural Equation Finder**.

The shared HTML shell was simplified to match the supplied dashboard direction: light canvas, restrained navigation, white cards, compact controls and metrics, a prominent plot, and no visible lesson objectives, assumptions, quiz, or “what you learn” rail. A new `presentation: dashboard` module contract keeps future lesson modules possible without forcing teaching panels into data-science tools.

## Scientific behavior

The user uploads a UTF-8 CSV, selects one numeric target and one-to-four numeric inputs, configures a scikit-learn `MLPRegressor`, and trains explicitly. Feature and target scalers fit training rows only; a deterministic held-out split measures original-unit NN R², RMSE, and residuals.

The neural network is a numerical predictor and does not directly return a compact symbolic expression. The displayed equation is a separate polynomial surrogate fitted to the network's predictions on training inputs. Its fidelity R² is measured against neural predictions on held-out inputs. The UI and documentation state this distinction, so a high-fidelity equation is not presented as a recovered governing law.

The compact controls are hidden-layer sizes, activation, solver, L2 alpha, initial learning rate when the solver uses it, maximum iterations, test fraction, polynomial degree, and seed. Official scikit-learn documentation informed those choices. `lbfgs` is the default for this small-data local demo; `adam` and `sgd` remain available. Training uses an isolated JSON subprocess, one per browser session, with a 120-second operational timeout, process cleanup, and atomic result publication. The dashboard reports measured duration rather than a promised runtime.

## Data and plots

The CSV limit is 5 MB decoded, 20-5,000 rows, and 2-100 columns. Empty, NaN, or unparseable selected cells are dropped and counted; explicit infinity/overflow is rejected. Unselected text columns do not invalidate a row. The module rejects constant selected/training columns and nonfinite intermediate results.

With one input, the primary plot shows observations, the neural-network curve, and the polynomial-surrogate curve over the observed domain. With several inputs it switches to observed versus predicted target with an identity line. The second plot shows signed residuals. Stochastic solvers show their standardized training objective; `lbfgs` explicitly reports that no loss curve is exposed. A small data preview and metric tiles keep the workflow in one dashboard.

## Implementation and evidence

This run used the existing Planner → Architect → Builder → QA workflow with native Codex subagents given explicit canonical role and skill files. Persistent artifacts are under `runs/neural-equation-20261030-01/`.

The exact tested stack is CPython 3.14.0 on macOS arm64, scikit-learn 1.9.1, SciPy 1.18.1, NumPy 2.4.1, Bokeh 3.8.2, and Flask 3.1.2. The full closure is in `requirements.lock.txt`.

Builder verification includes strict CSV/config tests, train-only scaling and held-out leakage checks, independent metric/polynomial evaluation, deterministic repeats, real worker success/failure/timeout/cancellation, and independent Bokeh Documents. Predeclared clean fixtures passed:

| Fixture | NN test R² | RMSE | Equation fidelity R² | MLP fit | Worker wall |
| --- | ---: | ---: | ---: | ---: | ---: |
| Linear 300×1 | .9999999999997 | 1.22e-6 | 1.0 | .0016 s | 1.63 s |
| Quadratic 300×1 | .9999973 | .00248 | .9999973 | .058 s | 1.20 s |
| Multifeature 400×3 | .9999954 | .00280 | .9999954 | .092 s | 1.16 s |
| Stress 5,000×4 | .9999972 | .00232 | .9999973 | .883 s | 2.00 s |

These are local fixture measurements, not a guarantee for arbitrary uploads. Browser verification used Chrome/Chromium 156 against the real Flask/Bokeh/WebSocket app. It uploaded a CSV, changed visible controls, trained through the subprocess, checked plots/metrics/equation, verified two independent sessions, captured desktop 1366×1000 and mobile 390×844 screenshots, and found no page-level horizontal overflow or captured JavaScript error.

## Five-minute demonstration

```bash
cd "/Users/ngoleminh/Documents/multi-agent-platform"
./run.sh
```

Open `http://127.0.0.1:8080`.

1. Show that the root opens a single sparse dashboard with no lesson rail or quiz.
2. Train the built-in quadratic sample with defaults and point to separate NN test and equation-fidelity metrics.
3. Upload a small CSV, select target/features, and show that one-input and multi-input plots choose different honest views.
4. Change solver from `lbfgs` to `adam`; note that the learning-rate control becomes applicable and a training-objective curve is available.
5. Show the polynomial equation label and state that it approximates the neural network rather than proving a physical law.

## Claim boundaries and next review

The supported claim is a functioning local CSV-to-neural-regression dashboard with an explicit, measured polynomial surrogate and a reusable multi-agent build/QA record. The current fixtures do not establish performance on Minh's real data because those files were not supplied in this iteration. The module does not yet support categorical data, classification, time-series ordering, multiple targets, differential-equation discovery, uncertainty estimates, or symbolic-regression search.

This iteration does not prove learning gains, production readiness, deployment, automatic custom-role discovery, live Claude execution, or the proposed 30% reduction in human effort. The next meaningful review is to run representative user CSV files, record failures and requested UI changes, and decide whether true symbolic regression or differential-equation discovery is required beyond this neural-predictor-plus-surrogate scope.
