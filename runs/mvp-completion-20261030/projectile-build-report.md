# Projectile Builder report

Status: implemented and unit-verified; ready for independent QA and root-owned browser/lifecycle verification. Builder modified only `modules/projectile/**` and this report. No delegation or package installation occurred.

## Explicit instruction and source reads

Read `AGENTS.md`, `agents/stem-builder.md`, `docs/design-proposal.md`, current run `learning-spec.md` and `technical-plan.md`, and `briefs/projectile-motion.md`. Explicitly read the five named skill files under `.agents/skills/`: stem-module-examples, stem-scientific-python, stem-bokeh-interaction, stem-flask-bokeh, stem-learning-ui. This records actual file reads, not automatic skill discovery/loading.

Read `corpus/catalog.json` and resolved its case study to `corpus/sindy.md`. Initial attempted `corpus/case-studies/sindy.md` did not exist; corrected using the catalog. Inspected original source under `/Users/ngoleminh/STEM VISUALIZATION/SINDy`: `main.py`, `flask_app.py`, `run.sh`, `tabs/test_tab.py`, `templates/index.html`, plus validation/scientific-layer excerpts in `engine/check_datafile.py` and `engine/sindy_model.py`. Observations are source-based; no original app browser or timing claim.

SHA256 checks for main.py, flask_app.py, run.sh, tabs/test_tab.py, templates/index.html matched catalog values respectively:

- `a4deadff78f043416ddbfd1634fb21631132b75f46919aee9901601256e770c8`
- `75197232df61d396882b4e00e4ed0ccb7b43fc8b99a059a39f5f75917c603354`
- `438c1990d546983143dae498c775d9655d3582e4ef92bc4a5439476e03fde96e`
- `a8bd20c5c412222ab8c66f8ec96c9e5bc75e62bd66959dc64276ad415fb08b86`
- `48de669bc657c1e78fd6fd9795dd710322cf93bcae9cb3f0d52468724fde053f`

## Implementation and criterion mapping

| Artifact | Behavior and criteria addressed |
| --- | --- |
| `modules/projectile/engine.py` | Frozen result dataclass; float64 aligned arrays; analytic SI summaries; finite real scalar validation and bounded integer samples 2–10001; exact vertical x/range zero; explicit zero duration. PM-02, PM-04. |
| `modules/projectile/ui.py` | Per-document speed/angle sliders; immediate Python callbacks update named trajectory CDS and metrics; status and invalid-input handling; units, hover, adaptive ranges, vertical responsive workspace and screen-scale explanation. PM-03/05/06/07 implementation. |
| `modules/projectile/module.json` | Title/subtitle, three objectives, four assumptions, three predict/explain questions with scientific feedback. PM-05. |
| `modules/projectile/tests/test_projectile.py` | Eight meaningful tests: independent Newtonian oracle at 20/30; scaling and complementary angles; grid/edge/finite data; malformed scalar and size boundaries; callback data and metrics changes; two Documents without shared state; lesson contract. PM-02/04; construction-level evidence for PM-03/05/06. |
| `modules/projectile/README.md`, `requirements.txt`, `__init__.py` | Root launcher instructions, locked dependency reference, engine/API boundaries and usage. PM-01/08 supporting artifacts. |

No shared runtime/web/scaffold file was edited. The launcher command is `.venv/bin/python scripts/serve.py --module projectile`. Actual process launch/readiness/shutdown remains root-owned.

## Exemplar adaptations

| Requirement | Exemplar source | Observed pattern | Adaptation/reason | Verification |
| --- | --- | --- | --- | --- |
| Session state | main.py build_app | Engine and storage instantiated per session | All widgets/sources/ranges/closures instantiated in build_document | Two Document test; browser session check pending |
| Scientific input/output | engine/check_datafile.py; engine/sindy_model.py | Early validation and engine/UI separation | Pure analytic trajectory with scalar domain and bounded arrays; no CSV/fitting dependencies | Independent oracle and malformed input tests |
| Controls, plots and diagnostics | tabs/test_tab.py | Controls drive labeled sources and metrics; visible validation status | Speed/angle directly update curve and three summaries; status reports immediate landing | Callback/source tests; browser pending |
| Layout and learning flow | templates/index.html | Explanatory HTML with separately embedded workspace | Metadata lesson content plus one vertical control/results/plot workspace; no irrelevant training/history tabs | Content checks; desktop/narrow rendering pending |
| Hosting | flask_app.py; run.sh | Flask HTML embedding separate Bokeh service; fixed sleep launcher | Uses root-owned shared host and readiness-aware lifecycle; module imports never launch servers | Root lifecycle verification pending |
| Assessment/presentation | templates/index.html and corpus description | Lesson guidance and questions around interactive plots | Three specific prediction/explanation questions and assumption limits in shared metadata shell | JSON check; human curriculum review pending |

No original source was copied wholesale. Exemplar licensing remains unverified as described by corpus; this report does not claim distribution clearance.

## Commands, failures and measured results

Environment command: `/private/tmp/stem-platform-venv-20261030/bin/python -c ...` imported NumPy/Bokeh/Flask and printed installed metadata. Actual interpreter: Python 3.14.0, Clang 16.0.0; NumPy 2.4.1, Bokeh 3.8.2, Flask 3.1.2. Existing provided virtual environment used; no install performed by this Builder.

Test command from project root:

```sh
/private/tmp/stem-platform-venv-20261030/bin/python -m unittest discover -s modules/projectile/tests -v
```

Initial result: six passed, two UI construction errors. Bokeh requires callback signature `(attr, old, new)` without defaults; corrected signature and explicit initial call. Final result: **8 tests passed**, 0.210 s, process exit 0. This is a natural defect/repair record, not an acceptance-criteria alteration.

Benchmark: CPU on `macOS-26.1-arm64-arm-64bit-Mach-O`, architecture arm64; exact CPU model not exposed by platform.processor() (reported `arm`). Warmed engine once, then timed 1000 independent calls each with speed50/angle45 using perf_counter. 201 samples: median 0.006792 ms, maximum 0.021875 ms. 10001 samples: median 0.024125 ms, maximum 0.033209 ms. Ten warmed Document constructions: median 8.718855 ms, maximum 9.167416 ms. These are local engine/document costs, not browser round-trip or rendering timings. Deterministic closed-form computation, no seed/training/GPU/epochs involved.

## Remaining checks and limitations

- PM-01 clean dependency installation and actual dual-service lifecycle: **not run by Builder**, root owns.
- PM-03 embedded browser controls/WebSockets/console: **not run by Builder**.
- PM-05 rendered instructional inspection: **not run by Builder**; source/content checks pass.
- PM-06 two live browser sessions: **not run by Builder**; two independent Python Documents tested.
- PM-07 desktop and narrow viewport usability: **not run by Builder**; stretch-width vertical layout and min_width280 implemented.
- PM-08 this report records role/skill/source reads, adaptation and repair; final staged acceptance belongs to root and QA.

Analytic maximum height remains correct for coarse sample grids omitting the apex. Both plot axes show meters, but their screen scales can differ; learner text says so. Frozen dataclass prevents field reassignment; returned arrays are fresh and mutable, with no global retained state. This pilot demonstrates implementation and local scientific checks; faculty acceptance, learning gains, deployment and productivity/cost improvement are unverified. Model usage/cost metrics unavailable to Builder.
