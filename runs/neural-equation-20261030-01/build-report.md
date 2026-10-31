# Builder handoff: Neural Equation Finder

Run: neural-equation-20261030-01. Status: implementation complete, numerical/worker/Document checks passed, ready for independent QA. Browser and shared-host acceptance remain separate. Builder wrote only `modules/neural-equation-finder/**` and this report, using apply_patch. Original SINDy, old modules, runtime, templates, and dependency locks were not edited. No agents were delegated and no packages installed by Builder.

## Actual instruction/source access

Explicitly read AGENTS.md, agents/stem-builder.md, the five assigned stem-module-examples/scientific-python/bokeh-interaction/flask-bokeh/learning-ui skill files, the scientific equation-discovery reference, and current brief/learning-spec/technical-plan. Read current runtime/lesson template, corpus/catalog.json and corpus/sindy.md. This is explicit file access, not an automatic role/skill-loading claim.

Inspected original SINDy `engine/check_datafile.py` and `tabs/train_tab.py` upload callback/decoding/validation patterns; existing context also supplied original per-session main.py, test_tab.py held-out diagnostics, Flask/template shell, and scientific-engine separation. Checked SHA-256 of the two specifically reused upload sources; both match the catalog:

- engine/check_datafile.py: 79ee0bb486c3217963785a103feea964d6385f6d25441c9e4b566a72e1ac76af
- tabs/train_tab.py: 5c22e645d6fa28cb72c9232b84262c4be1e6327f48aea8a22d7ff4ecb5d31b35

| Requirement | Observed exemplar pattern | Adaptation and reason | Verification |
| --- | --- | --- | --- |
| Upload/data handling | SINDy byte guard, base64 FileInput callback, strict trajectory validation | Guard encoded/decoded byte limits, parse strict UTF-8 CSV, validate selected numeric columns; drop missing/unparseable rows, reject explicit infinity. Do not impose time-series monotonicity. Callback uses value only, avoiding SINDy's filename timing dependency. | Parser/selection tests; real browser upload pending |
| Scientific output | SINDy separate scientific engine and held-out diagnostics | MLP predictor plus original-unit polynomial surrogate with fidelity distinct from NN quality; no symbolic law claim | Independent metrics/powers evaluation, controlled fixtures, leakage tests |
| Session state | SINDy build_app creates engine/storage locally | All dashboard sources, controls, data, worker and committed state inside build_document | Two-Document tests; live browser isolation pending |
| Expensive computation | SINDy synchronous fit limitation | Same-interpreter JSON subprocess; background monitor; next-tick-only publication; busy lock, timeout/cancel, generation tokens | Real worker success/error/timeout/active cancellation; Document busy/success/error tests |
| Layout and learning content | Existing HTML explanatory shell and diagnostic plots | Compact metadata dashboard, responsive data/config/metric/plot/equation cards; no visible quiz/lesson rail. Root owns shell integration. | Construction passes; rendered desktop/390px acceptance pending |
| Runtime | Separate Flask shell/Bokeh connection | Uses root-owned loader/launcher/lock, no module server side effects | Import/Document construction passes; clean setup and actual lifecycle pending |

Source inspection does not establish usability or license clearance. Implementation is newly authored, not a copied distribution or approved exemplar.

## Implemented contracts

Files: engine.py, worker.py, ui.py, module.json (`presentation: dashboard`), requirements.txt referencing root lock, __init__.py, README, tests/test_module.py, and tests/benchmark_fixtures.py.

Engine API implements bounded CSV parsing, selected-column cleaning and constant checks, all configuration ranges, deterministic shuffled split, training-only X/y standardization, configured squared-error MLP, original-unit prediction/residual/MSE/R², polynomial fit to training NN predictions, held-out fidelity, executable powers/coefficient evaluation and 17-digit equation formatting. Polynomial rank/condition and complete configuration/model/scaler arrays are retained. Undefined constant-reference R² returns null/unavailable. Nonfinite intermediates/results fail instead of being published.

Worker exchanges JSON only. One process runs per session; operational timeout is 120 seconds. Controls disable immediately; a periodic document callback updates busy elapsed status while a background monitor waits. Only next-tick callbacks mutate Bokeh after completion; sources/metrics/equation/config commit under a document hold. Failure retains prior committed data. Session destruction invalidates generations and cancels workers; host atexit cancels registered jobs. Pipes close and child processes are reaped on timeout, cancellation, and errors. Numerical-library environment thread counts are set to one before worker import. Cross-session admission is deliberately omitted as permitted by the plan; multiple sessions may run one worker each, so this is not a multi-user resource scheduler.

All stable names from the plan are implemented. One-feature plots distinguish observations, NN, and polynomial; multiple features switch to actual/predicted plus identity. Residuals use NN prediction on x and observed-minus-NN on y. lbfgs loss is empty/labeled unavailable. Shape/color legends identify train/test. Preview and equations scroll internally; browser width acceptance is not inferred from source construction.

## Actual verification

Initially sklearn was absent; Builder reported that immediately and did not attempt tests. Root then installed dependencies. Observed `sklearn.show_versions()`:

```text
Python 3.14.0, macOS-26.1-arm64-arm-64bit-Mach-O, processor arm
scikit-learn 1.9.1; NumPy 2.4.1; SciPy 1.18.1; joblib 1.6.0
threadpoolctl 3.7.0; pandas 3.1.0; narwhals 2.28.0; pip 25.2
OpenMP enabled; direct main-process show_versions reports 8 libomp threads.
Workers set OMP/OPENBLAS/MKL/VECLIB/NUMEXPR thread environment counts to 1.
```

Executed from `/private/tmp/neural-equation-platform-20261030`:

```sh
/private/tmp/neural-equation-venv-20261030/bin/python -m unittest discover -s modules/neural-equation-finder/tests -v
```

Latest result: **13 tests passed**, unittest duration 2.535 seconds. Meaningful checks cover parser unsafe bounds/UTF-8/header/columns, selected cleaning and infinity rejection, constants/insufficient rows, configuration bounds and actual MLP constructor arguments, independent train-scaler mean/std, repeatability and held-out-target perturbation, independent original-unit residual/R²/RMSE, independent polynomial term multiplication and formatted-equation evaluation, fidelity denominator/reference, undefined R², both predeclared recovery fixtures, multifeature outputs, stochastic-vs-lbfgs loss behavior, real JSON worker success/failure, actual subprocess timeout and active cancellation/reaping, and distinct Documents with upload/solver/busy/duplicate prevention/success/failure/stale state.

An initial test run had a FileInput test-harness error because `.trigger` read an unset readonly value; changed the harness to the server-equivalent `set_from_json`. A ResourceWarning on a timeout exposed a pipe-cleanup gap, repaired by closing all streams and reaping any live process in `finally`; subsequent runs pass without that warning. These are pre-handoff build/debug iterations, not hidden passing evidence. No unresolved automated failures remain.

Executed explicit worker fixture benchmark (one run per fixture, no warm-up):

```sh
/private/tmp/neural-equation-venv-20261030/bin/python modules/neural-equation-finder/tests/benchmark_fixtures.py
```

All four workers completed successfully with no warnings, CPU-only, one numerical-library thread, Python/sklearn/hardware context above. Seed42 and test fraction .2 throughout. Linear uses (8,), identity, alpha0, degree1, requested1000 iterations. Quadratic uses (32,32), tanh, alpha1e-6, degree2, requested2000. Multifeature uses (32,32), tanh, alpha1e-6, degree2, requested1000; input RNG seed4. Stress uses (32,32), tanh, alpha.0001, degree2, requested1000; input RNG seed9. All use lbfgs/tol1e-6/max_fun20000. This is iterative numerical optimization, not fixed epochs.

| Fixture | Rows × inputs | NN test R² | Test RMSE | Equation fidelity R² | Actual iterations | MLP fit seconds | Pipeline seconds | Worker wall seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Linear | 300×1 | .9999999999997271 | .000001224607 | 1.0 | 5 | .001644333 | .007988166 | 1.629073292 |
| Quadratic | 300×1 | .999997331286 | .002478895293 | .999997334264 | 131 | .058123084 | .061613709 | 1.197173708 |
| Multifeature | 400×3 | .999995414921 | .002799340824 | .999995407658 | 268 | .092277000 | .097008458 | 1.159323500 |
| Stress | 5000×4 | .999997246885 | .002321657416 | .999997291984 | 458 | .882664958 | .891920959 | 2.001547541 |

Linear equation coefficients [intercept,slope]=[1.000001223755988,2.00000003011361], within .02. Quadratic [intercept,x,x²]=[.70004516849206,-1.2000171770014507,.49997471154811096], within .08. Both exceed predeclared NN/fidelity gates. Multifeature and stress use bounded uniform input and known polynomial responses; these establish finite scoped behavior, not recovery for arbitrary uploads. Stress completed rather than timing out.

Timing scopes: MLP fit wraps only nn.fit; pipeline starts before split/scaling and covers predictions/polynomial/curves; worker wall includes process startup/import/CSV processing/serialization/monitor completion. Browser/user-visible latency was not measured by Builder. These timings are observed local runs, not a fixed-duration promise or general capacity guarantee.

## Acceptance map and handoff limits

| Criterion | Implemented / verified here | Remaining QA |
| --- | --- | --- |
| NE-01 | Parser, cleaning, selectors and Document upload passed | Actual browser file upload and errors |
| NE-02 | Determinism, train-only scalers, held-out perturbation passed | Independent QA replication |
| NE-03 | Config validation/constructor and solver applicability/loss tests passed | Real browser control behavior |
| NE-04 | Independent held-out metrics/residual tests passed | Browser metric/plot consistency |
| NE-05 | Independent powers/coefficient/format/fidelity checks passed | Browser equation/mapping display |
| NE-06 | Both predeclared fixture gates passed; bounded multifeature/stress completed | QA independent checks |
| NE-07 | Named sources and Document busy/commit/failure paths passed | Real background browser transitions |
| NE-08 | Dashboard/no quiz metadata and responsive layout implemented | Desktop/390px screenshots and actual overflow |
| NE-09 | Separate Documents passed | Two actual browser sessions |
| NE-10 | Imports, construction, subprocess cleanup passed | Root clean installation/discovery/Flask/WebSocket/host lifecycle |
| NE-11 | Explicit NN/surrogate separation in UI/docs/metrics | Independent claim review |
| NE-12 | Local CPU fixture timings/context measured and recorded | Browser/user-visible latency if required |

Root owns integration of dashboard metadata, shell, removal of old modules, and exact dependency closure. Builder did not alter those to make construction pass. At implementation read time the old metadata validator required three questions; this module intentionally has none because user requires no quizzes, and root is explicitly handling dashboard integration. README documents startup and verification commands. No deployment, learning-gain, productivity, arbitrary-data recovery, approved-exemplar, or fresh-install claim is made by this handoff.
