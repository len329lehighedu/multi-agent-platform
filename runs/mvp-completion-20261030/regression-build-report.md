# Linear regression Builder handoff

Run: mvp-completion-20261030. Role: regression Builder, explicitly dispatched by orchestrator. Status: implemented and ready for independent QA; browser acceptance remains unverified by Builder. Write scope: only `modules/linear-regression/**` and this report. No shared files or original SINDy sources changed. No further agents invoked and no packages installed.

## Inputs and skills actually read

Read `AGENTS.md`, `agents/stem-builder.md`, the current `learning-spec.md` and `technical-plan.md`, `docs/design-proposal.md`, `corpus/catalog.json`, and `corpus/sindy.md`. Explicitly read all five named skill files under `.agents/skills/`: `stem-module-examples`, `stem-scientific-python`, `stem-bokeh-interaction`, `stem-flask-bokeh`, and `stem-learning-ui`. This was explicit file access, not automatic preloading/discovery.

Read original SINDy `/Users/ngoleminh/STEM VISUALIZATION/SINDy/main.py`, `flask_app.py`, `tabs/test_tab.py`, `templates/index.html`, and relevant opening scientific-engine code in `engine/sindy_model.py`. SHA-256 checks matched the catalog:

| Source | SHA-256 |
| --- | --- |
| main.py | a4deadff78f043416ddbfd1634fb21631132b75f46919aee9901601256e770c8 |
| flask_app.py | 75197232df61d396882b4e00e4ed0ccb7b43fc8b99a059a39f5f75917c603354 |
| tabs/test_tab.py | a8bd20c5c412222ab8c66f8ec96c9e5bc75e62bd66959dc64276ad415fb08b86 |
| templates/index.html | 48de669bc657c1e78fd6fd9795dd710322cf93bcae9cb3f0d52468724fde053f |
| engine/sindy_model.py | 4c1b457f6626f95e07e19474b94ebcfb36f30f5c3dbe09d18b27f2d278a1a57b |

These are source observations, not rendered usability evidence or license clearance. The implementation is newly authored; no source distribution was copied.

## Implementation and adaptation

Implemented `engine.py`, `ui.py`, `module.json`, `__init__.py`, module README, requirements referencing the shared lock, and independent unittest tests. `module.json` uses the shared shell's `question`/`answer` schema for three revealable feedback questions. Consulted shared runtime/schema without modifying it.

| Requirement | Exemplar source / observed pattern | Adaptation and reason | Verification |
| --- | --- | --- | --- |
| Scientific/input contract | engine/sindy_model.py separates scientific work from layout | Pure NumPy two-coefficient OLS and seeded synthetic data; finite aligned arrays and valid partition checks; no time-series preprocessing | Centered-sums oracle, invalid inputs, rank-deficiency tests |
| State and interaction | main.py creates engine/storage within build_app; test_tab.py local callbacks/status | Every model/source/closure lives inside build_document; explicit Generate commits controls and retains committed metric configuration | Two distinct Documents and callback tests |
| Held-out evidence | tabs/test_tab.py separates unseen-data diagnostics | Fixed random train/test split, fitting only training rows, prediction/residual and separate MSE for each partition | Perturb only held-out y and verify unchanged coefficients |
| Presentation/layout | templates/index.html explains science around embedded workspace | Module metadata feeds shared Flask shell; vertically stacked responsive plots; circles/triangles, labeled true/fitted lines, residual baseline | Source/Document inspection; browser layout check pending |
| Assessment and result interpretation | HTML lesson fragments + test-tab explanatory intent | Three targeted questions; residual sign, zero-noise recovery, generalization; no fixed finite-sample error ordering claim | Metadata/content review; faculty review pending |
| Runtime | flask_app.py embeds Bokeh in Flask | Uses root-owned shared loader/launcher and lock; <=300-row synchronous NumPy calculations are bounded | Unit construction and compute benchmark here; launcher/WebSocket QA separate |

Scientific API: `generate_data(noise=1.0, sample_count=100, seed=42)` returns Dataset; RNG draws standard-normal noise before split permutation. The first floor(.75*n) permuted rows train. `fit_and_evaluate` uses only train rows in NumPy `lstsq` and requires rank 2. Residual=y−prediction; MSE=mean(residual²). It rejects malformed shapes/indices, nonfinite values, empty/duplicate/overlapping/nonexhaustive partitions, and nonfinite computed output.

UI models: sliders `noise`/`sample_count`; integer NumericInput `seed`; button `generate`; `status`, `metrics`; named `observations`, `residuals`, `fit_line`, `true_line` sources. Control edits mark pending and retain committed plots/metrics until Generate. Input errors retain prior results and explain correction. Both plots use separate shape/color legends for train/test; residual baseline is zero. Plot sizing is vertical/stretch_width with minimum width 280; actual viewport acceptance awaits browser evidence.

## Commands and actual results

Executed from `/private/tmp/stem-platform-completion-20261030`:

```sh
/private/tmp/stem-platform-venv-20261030/bin/python -m unittest discover -s modules/linear-regression/tests -v
```

Result: **9 tests passed**, 6.725 seconds reported by unittest (7.266 seconds shell wall time). Tests:

- Independent centered-sums coefficient oracle plus manual residual/prediction/MSE checks.
- Held-out y perturbation preserves slope/intercept/training MSE and changes test error.
- Zero-noise slope/intercept recovery and near-zero errors at n=20,100,300; max noise/seed acceptance.
- Reproducible arrays and disjoint/exhaustive seeded split; same seed/n preserves z and partition across sigma comparisons.
- Invalid control bounds/types, malformed aligned arrays, NaN/Inf, invalid partition shapes/dtypes/indices/coverage, rank deficiency.
- Pending control edits retain old sources/metrics; Generate updates observations, residuals, fitted line, counts, configuration, shape fields.
- Invalid seed preserves prior committed output with an error.
- Two independently built Documents share no model identities, and changing one does not alter the other.

Environment actually observed: CPython 3.14.0, NumPy 2.4.1, Bokeh 3.8.2; macOS 26.1 arm64 (platform processor reports arm). CPU NumPy OLS, one predictor plus intercept, n=300, sigma=5, seed=42; no architecture/epochs/GPU apply. Benchmark used 10 warm-up fits and 1000 timed iterations:

| Timing scope | Median | Maximum |
| --- | --- | --- |
| fit_and_evaluate only | 0.044166 ms | 0.063583 ms |
| generate_data + fit_and_evaluate | 0.064375 ms | 0.091333 ms |

Measured via `time.perf_counter` in a Python heredoc loading engine.py using importlib; these are local compute timings, not browser-visible latency. Total UI/render/network latency was not measured. No training-duration promise is made.

Documented startup: `python3 -m venv .venv`, `.venv/bin/python -m pip install -r modules/linear-regression/requirements.txt`, `.venv/bin/python scripts/serve.py`, then `http://127.0.0.1:8080/modules/linear-regression/`. Builder did not install dependencies or launch shared servers; root/QA own clean setup and lifecycle checks.

## Acceptance mapping and limits

| Criterion | Builder evidence / remaining work |
| --- | --- |
| LR-01 | Requirements/README integrate root-owned shared runtime; clean install and startup/shutdown not run here |
| LR-02 | Seeded split and reproducibility tests passed |
| LR-03 | Independent OLS and held-out perturbation tests passed |
| LR-04 | Manual prediction/residual/MSE oracle passed |
| LR-05 | Zero-noise boundary checks passed |
| LR-06 | Python Document callbacks update all required sources/metrics; actual server-backed browser action not run here |
| LR-07 | Units, labels, assumptions, objectives, three feedback questions implemented; faculty review pending |
| LR-08 | Bounds, invalid arrays/partitions and rank tests passed |
| LR-09 | Separate Documents passed; two actual browser sessions and desktop/narrow viewport checks not run here |
| LR-10 | Explicit skills/source/plan reading, source hashes, adaptation, commands and limitations recorded |

No failed tests remain after implementation. Browser usability, browser WebSocket interactions, clean dependency installation, launcher behavior, and actual two-browser sessions are explicitly not-run by Builder and must remain visible until separate QA. No claims about learning gains, matched human productivity, deployment readiness, or approved exemplar status.

## QA repair: qualify noise comparisons for a fixed realization

QA identified an instructional precision defect in the initial warning about nonmonotonic finite-sample errors. In this particular generator the true relationship is exactly linear. With x, standard-normal draws, and split fixed by seed/n, the linear OLS projection makes residuals proportional to sigma and both train/test MSE proportional to sigma squared (apart from floating-point roundoff). The initial broad warning was therefore misleading for the default controlled experiment.

Narrow repair changed `ui.py`, `module.json`, and module README to state this scaling explicitly (doubling sigma quadruples MSE) and restrict the nonmonotonic comparison caveat to different realizations/seeds/splits. The independent statement that test and training error have no guaranteed ordering remains. Existing assessment feedback did not make the incorrect monotonicity claim and remains appropriate. No engine behavior, shared specification, or runtime files changed.

Added the metamorphic `test_fixed_realization_residuals_and_mse_scale_with_sigma`: for (n,seed)=(20,0),(101,42),(300,4294967295), compare sigma=.5 with sigma=2; residuals must multiply by 4 and each MSE by 16 within numerical tolerance. This uses the mathematical scaling relation without duplicating the OLS implementation.

Executed:

```sh
/private/tmp/stem-platform-venv-20261030/bin/python -m unittest discover -s modules/linear-regression/tests -v
```

Result: **10 tests passed**, unittest time 1.207 seconds (shell wall time 2.322 seconds). The initial report's 9-test result remains historical evidence; this is the post-repair result. Browser checks were not repeated by Builder for this text-and-test repair; QA/orchestrator retain ownership of final browser acceptance. The repair supersedes the initial report's broad “no fixed finite-sample error ordering claim” language only as regards monotonicity in noise; no guarantee comparing training MSE with test MSE is introduced.
