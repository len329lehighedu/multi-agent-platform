# Learning specification - Neural Equation Finder

Run: `neural-equation-20261030-01`  
Producing role: `stem-learning-planner` (native subagent, explicit role/skill assignment)  
Status: ready for architecture; implementation and acceptance not yet verified.

## Audience, purpose, and scope

The user is a developer or data-science learner who can identify numeric input and target columns. The task is practical exploration of uploaded tabular data through one concise dashboard: upload/select data, configure a neural regressor, train explicitly, and inspect predictions, diagnostics, and a polynomial approximation.

Required scientific distinction:

- `MLPRegressor` produces numerical predictions.
- A separate polynomial surrogate approximates the trained network in original feature/target units.
- NN test quality compares held-out observed targets with neural predictions.
- Equation fidelity compares surrogate predictions with neural predictions on held-out inputs.

Neither strong prediction quality nor strong surrogate fidelity establishes discovery of a governing law.

## Objectives kept in documentation

These guide design and QA but are not rendered as a lesson panel:

1. Select a scalar regression task from numeric CSV columns and see how unusable rows are handled.
2. Configure and train a neural regressor, then interpret held-out R2, RMSE, and signed residuals.
3. Distinguish an accurate neural predictor from a faithful polynomial approximation of that predictor.
4. Distinguish training loss, test quality, and surrogate fidelity.

## Minimal visible interface

Use short labels and contextual status only:

1. Top bar: Neural Equation Finder and compact upload action.
2. Data card: target/features, rows used/dropped, compact preview.
3. Controls: hidden layers, activation, solver, alpha, applicable learning rate, iterations, test fraction, polynomial degree, seed.
4. Metrics: NN test R2, NN test RMSE, equation fidelity R2, rows, iterations, and fit time.
5. Main plot plus residual and training-loss cards.
6. Equation card headed `Polynomial surrogate` with one sentence: `Approximates the neural network; fidelity compares equation and NN predictions.`

No instructional rail, assessment section, or “what you learn” card. Warnings stay compact. Wide previews/equations may scroll within cards; the page must not overflow horizontally.

## Interaction contract

The app opens with a built-in dataset and selectors ready. Results appear only after explicit training. Upload validates the CSV, updates selectors, and reports status. Hyperparameter changes mark committed results as stale. Train immediately exposes a busy state, prevents duplicate submission, and commits model, scalers, split, metrics, equation, plots, duration, and configuration atomically. A failure never publishes partial results. Separate Bokeh sessions keep independent datasets and models.

## Data and science contract

- UTF-8 CSV header required; reject empty/duplicate column names, malformed rows, explicit infinity/overflow, and unsafe size.
- Raw dataset: 20-5,000 rows and at least two columns.
- One target and one-to-four distinct features; target cannot be a feature.
- Missing, NaN, or unparseable selected cells are dropped and counted. Explicit infinities are rejected.
- At least 20 usable rows. Reject constant selected target/features after cleaning.
- Unselected columns do not affect selected-row usability.
- Deterministic shuffled split. Fit X and y scalers on training rows only. Fit the MLP only on standardized training data; predictions return to original target units.
- Handle solver-specific controls accurately. Report convergence warnings and actual iterations.
- Residual is observed minus neural prediction. RMSE uses target units; R2 is dimensionless and can be unavailable.
- Fit polynomial coefficients against NN predictions on training inputs in original units. Evaluate fidelity against NN predictions on held-out inputs. No held-out observed targets enter surrogate fitting.
- Display coefficients/powers consistently with executable evaluation and enough precision to remain meaningful.
- For one feature, plot observations, NN curve, and equation curve only across the observed domain. For multiple features, plot actual versus NN predicted with an identity line.
- Never fabricate a loss curve for a solver that does not expose one.

## Acceptance map

| ID | Required evidence |
| --- | --- |
| NE-01 | Parser and browser upload checks for headers, bounds, selected columns, cleaning policy, constants, and errors. |
| NE-02 | Repeated deterministic fits; train-only scaler oracle; held-out-target perturbation does not change learned fit. |
| NE-03 | Parameter-construction checks and browser applicability state for architecture, activation, solver, alpha, learning rate, iterations, and seed. |
| NE-04 | Independent held-out R2/RMSE/residual oracle in original units, including undefined R2. |
| NE-05 | Independent polynomial evaluation reproduces surrogate predictions; fidelity uses NN predictions. |
| NE-06 | Predeclared fixture settings and separate NN/fidelity thresholds for clean linear and nonlinear fixtures. |
| NE-07 | Real browser training updates preview, metrics, plots, legends, pending/busy state, and solver-specific loss state. |
| NE-08 | Desktop and 390px evidence; no page overflow; no lesson/quiz rail. |
| NE-09 | Two live browser contexts keep uploaded data, configuration, and results isolated. |
| NE-10 | Fresh Python 3.14 setup, unit tests, discovery, Flask/Bokeh/WebSocket, and clean lifecycle. |
| NE-11 | Dashboard and documentation call the equation a polynomial surrogate and make no unsupported law-discovery claim. |
| NE-12 | Measured timer scope and reproducibility context include rows, features, iterations, solver, Python, sklearn, and hardware. |

## Exemplar adaptations

The planner inspected cataloged SINDy patterns for upload validation, explicit training controls, per-document state, separate held-out evaluation, Flask/Bokeh embedding, and synchronous-fit limitations. The new module adapts those patterns to selected-column CSV validation, compact committed state, separated NN/fidelity metrics, and a bounded execution strategy. SINDy's algorithm, multi-tab teaching structure, and output representation are not transferred.

## Architecture handoff decisions

- Keep objectives and review prompts only in metadata/docs because the user explicitly excludes visible lesson content.
- Resolve the brief ambiguity as missing/unparseable-drop and explicit-infinity-reject.
- Fit the surrogate on training-input NN predictions and measure fidelity on untouched held-out inputs.
- Four features at degree four produce at most 70 terms including intercept; keep the 100-term check as future-proof validation.
- No fixed runtime promise. Architect must choose upload byte cap, split bounds, exact sklearn pin, background strategy, defaults, and fixture thresholds.
- User data were not provided; fixture success establishes only scoped functionality.
