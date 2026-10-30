# Learning specification: both MVP pilots

Saved/condensed by orchestrator from actual /root/mvp_planner response. Explicit role/skill reads, no automatic loading claim. Audience assumption: introductory undergraduates, algebra and graph reading; projectile also basic trigonometry. English learner UI. Faculty review remains pending.

## Shared flow

Read assumptions → predict → change controls → inspect labeled plots and numbers → explain → reveal feedback. Reuse SINDy organization: independently testable engine, per-session Bokeh state, Flask HTML shell, learning content and questions. Inspected originals: main.py, flask_app.py, templates/index.html, tabs/test_tab.py; Planner reported hashes match catalog. Source inspection does not establish rendered usability.

## Projectile

Follow briefs/projectile-motion.md and PM-01–08 unchanged. Gravity 9.81 m/s², no drag, equal heights; speed 0–50 m/s and angle 0–90°, defaults 20/45. Speed/angle sliders update trajectory and time/range/maximum-height summaries; x/y axes in meters. Handle zero speed, horizontal/vertical launch and invalid inputs explicitly.

Objectives: explain speed scaling; complementary-angle range symmetry; limits of assumptions. Questions with feedback: (1) Doubling speed at fixed 30° doubles time and quadruples range/height. (2) At fixed speed, 30° and 60° have equal range, but 60° flies longer/higher. (3) Complementary-angle equality is not guaranteed with drag or unequal heights.

Acceptance: PM-01 clean environment/lifecycle; PM-02 independent analytical trajectory/summary checks; PM-03 real browser control updates; PM-04 edges/invalid data; PM-05 learning content/three feedback questions; PM-06 two sessions isolated; PM-07 desktop/narrow usability; PM-08 traceable stages/adaptation.

## Linear regression

One-feature ordinary least squares with intercept; synthetic dimensionless x/y. Defaults: n=100, x covers 0–10, true slope=2, intercept=1, Gaussian noise sigma=1, seed=42, train fraction=.75. Controls: sigma 0–5, n 20–300, integer seed, explicit Generate and fit button. Same seed/n must reuse standard-normal draws and split across noise comparisons. Changes in n can change realization; explain. Fixed true coefficients, no uploads, neural networks or symbolic discovery.

Fit only training rows. Show train/test scatter with different marker shapes, fitted and true generating lines, residual plot against x with zero baseline, fitted equation, counts/split and separate train/test MSE. Residual=y−prediction; MSE has squared response units. With fixed seed/n (same standard-normal draws and split), this exactly linear OLS experiment has residuals proportional to sigma and train/test MSE proportional to sigma squared, apart from roundoff. Across different seeds/realizations/splits, error comparisons need not be monotonic with sigma. There is no guaranteed train/test error ordering.

Objectives: interpret coefficients/residuals; relate noise to scatter without deterministic finite-sample claims; distinguish training fit from held-out evidence. Three questions/feedback: (1) A point above fitted line has positive residual. (2) Zero noise recovers slope 2/intercept 1 and near-zero errors within floating-point tolerance if training x varies. (3) Smaller training error alone does not prove better new-data performance; test rows remain outside fit and errors need not have fixed ordering.

Acceptance: LR-01 shared setup/lifecycle; LR-02 seeded disjoint/exhaustive split; LR-03 train-only OLS (alter held-out y and verify coefficients unchanged); LR-04 independently check residuals/MSE; LR-05 zero-noise recovery; LR-06 browser updates all plots/results; LR-07 labels/content/three feedback questions; LR-08 boundaries/invalid data; LR-09 two sessions and responsive viewport layout; LR-10 reuse/stages/evidence traceable.

## Limits

No deployment/auth/history/uncertainty bands or neural training. Faculty suitability/learning gains not validated. Prior numerical smoke does not accept either app. Productivity gains require matched human baseline data; do not infer them from completion.

## QA correction

Independent QA identified the original broad nonmonotonic-noise warning as imprecise for fixed-seed/n comparisons in this exact linear model. The specification and learner text were corrected to explain quadratic MSE scaling under controlled fixed draws/split. This is a documented instructional defect/repair, not a silent acceptance change.
