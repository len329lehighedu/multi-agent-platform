# Neural Equation Finder brief

## Request and audience

Replace the two existing demonstration modules with one deeper data-science module. The user uploads a numeric CSV file and trains a neural-network regressor to learn the target from selected input columns. The UI should resemble the supplied dashboard layouts: sparse cards, strong visual hierarchy, minimal explanatory copy, and direct access to data, controls, plots, metrics, and the fitted equation.

Audience: developers and data-science learners who can identify input and target columns. No lesson prose or assessment panel is required in the visible UI.

## Scientific contract

- Input: UTF-8 CSV with a header, 20 to 5,000 rows, at least two numeric columns, one selected target, and one to four selected input features.
- Invalid/missing rows in selected columns are dropped and reported. Constant columns, duplicate selections, non-finite values, and insufficient usable rows are rejected.
- Model: scikit-learn `MLPRegressor`, trained on a deterministic train/test split. Input features and target are standardized from training data only.
- Neural-network output: numerical predictions. The network itself is a black-box regressor and is not described as a symbolic equation learner.
- Equation output: an explicit polynomial surrogate fitted to the trained neural network's predictions in original feature/target units. The module reports surrogate fidelity separately from neural-network test quality.
- Plots: one-feature data/NN/equation plot or multi-feature actual-vs-predicted plot; residual plot; training-loss plot when the selected solver exposes a loss curve; compact data preview.
- Metrics: test R2, test RMSE, equation fidelity R2, rows used/dropped, iterations, and measured fit time on the local machine.

## Learner experience

The module opens with a small built-in sample so it is immediately testable. The user can upload CSV, choose target/features, set a compact set of meaningful hyperparameters, train, and inspect results without navigating through lesson text. Visible controls: hidden-layer sizes, activation, solver, L2 alpha, learning rate when applicable, maximum iterations, test split, equation degree, and seed.

The dashboard follows the attached reference PDF's module/detail patterns: a restrained top bar, white cards on a light gray canvas, a large primary plot, a compact control card, small metric cards, and no “what you learn” or quiz sections.

## Execution constraints

- Local CPU only; no GPU assumption.
- Maximum 5,000 rows and four input features.
- Maximum 2,000 iterations, up to three hidden layers, and up to 256 units per layer.
- Polynomial degree 1 to 4; reject configurations producing more than 100 displayed terms.
- Training occurs on explicit button click. The UI must show a busy state and measured duration; it must not promise a fixed runtime.
- Python 3.14 environment already used by the platform. Add an exact compatible scikit-learn dependency.
- Two repair cycles maximum.

## Acceptance criteria

- NE-01 (mandatory, Builder/QA): Upload and parse a valid numeric CSV; update column selectors; report used/dropped rows; reject malformed or unsafe inputs with actionable messages.
- NE-02 (mandatory, Builder/QA): Deterministic split and train-only scaling prevent leakage; repeated runs with the same data/config/seed agree within numerical tolerance.
- NE-03 (mandatory, Builder/QA): `MLPRegressor` uses the selected architecture, activation, solver, regularization, learning-rate, iteration, and seed settings with solver-specific behavior handled correctly.
- NE-04 (mandatory, Builder/QA): Test R2/RMSE and predictions are computed on held-out rows; residuals equal observed minus predicted.
- NE-05 (mandatory, Builder/QA): The displayed polynomial equation predicts consistently with its coefficients; equation fidelity is measured against neural-network predictions and clearly distinguished from test R2.
- NE-06 (mandatory, Builder/QA): Built-in linear and nonlinear fixtures recover high-quality numerical fits and appropriate polynomial surrogate equations within documented tolerances.
- NE-07 (mandatory, Builder/QA): The plots and data preview update after training and the one-feature plot distinguishes observations, neural-network curve, and equation curve.
- NE-08 (mandatory, Builder/QA): Dashboard is concise, usable at desktop and narrow viewport widths, has no horizontal page overflow, and contains no lesson/quiz rail.
- NE-09 (mandatory, Builder/QA): Separate browser sessions do not share uploaded data, selected columns, model state, or results.
- NE-10 (mandatory, Builder/QA): Fresh setup, unit tests, runtime discovery, Flask/Bokeh embedding, and clean shutdown pass with the new single module.
- NE-11 (mandatory, Architect/QA): Documentation states that the neural network is predictive and the explicit equation is a polynomial surrogate; no symbolic-recovery claim is made without evidence.
- NE-12 (mandatory, Builder/QA): Fit duration is measured and labeled with rows, features, iterations, solver, Python, scikit-learn, and hardware context in the run evidence.

## Assumptions and unresolved issues

The first version supports scalar regression with numeric CSV columns. Classification, categorical encoding, time-series order, differential equations, multiple targets, unit inference, and true symbolic-regression search are outside this module. The user's own data files were not attached in this turn, so validation uses built-in and generated CSV fixtures.
