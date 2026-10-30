# QA report

## Context

Run `mvp-completion-20261030`; staging root `/private/tmp/stem-platform-completion-20261030`. Independent dispatched reviewer `/root/mvp_qa`, 2026-10-30. Reviewed current learning specification, technical plan, both Builder reports and modules, shared runtime/scaffold/HTML/CSS, and projectile brief. Explicitly read `AGENTS.md`, canonical `agents/stem-qa-reviewer.md`, and all three named skills (`stem-module-examples`, `stem-lesson-design`, `stem-module-verification`) as files. This is evidence of explicit instruction access and execution, not automatic runtime role/skill discovery.

Also read design proposal, corpus catalog/case study, original SINDy `main.py`, `tabs/test_tab.py`, `flask_app.py`, `templates/index.html` (relevant excerpts). Independently checked these four originals against catalog hashes; all match (`qa-observations.json`). Reviewed source only; no original-app runtime claim. Source adaptation: per-session state from `main.py` becomes per-Document models; unseen-data distinction in `test_tab.py` becomes train-only OLS and held-out metrics; Flask/template embedding becomes metadata-driven shared shell. Shared scaffold cleanly separates engine and UI. Both Builder reports supply additional adaptation traces; independently inspected code corroborates these central patterns.

Environment actually used: `/private/tmp/stem-platform-venv-20261030/bin/python`, CPython 3.14.0, NumPy 2.4.1, Bokeh 3.8.2, Flask 3.1.2, macOS arm64 CPU. No dependency installation or implementation edit by QA. Exact command:

```sh
/private/tmp/stem-platform-venv-20261030/bin/python runs/mvp-completion-20261030/independent-science-tests.py
```

Result: eight newly authored independent test groups pass, 0.729 s (`qa-independent-tests.log`). These use component-velocity Newtonian oracles across 40 projectile settings, discrete kinematics, custom non-generator regression data/centered sums, held-out poisoning, 18 seed/count combinations, validation cases, Document callbacks/isolation, and independent CSV adaptation checks. They do not import or use Builder tests as the oracle. Additional Flask test-client route/source-hash observations are in `qa-observations.json`; test-client HTTP is not actual embedded browser verification.

## Criterion results (final: all 18 mandatory pilot criteria pass)

Every criterion below is mandatory. `not-run` includes partial source/Document evidence but remains unaccepted until the required actual runtime observation arrives.

| Criterion ID | Mandatory? | Status | Method/evidence | Limitation |
| --- | --- | --- | --- | --- |
| PM-01 | yes | pass | Final-root `fresh-environment.json` and `clean-install-and-final-tests.log`: environment absent before venv creation; locked install/pip check/numerical and browser suites all exit0; lifecycle/partial failure tests pass | Local CPU macOS Python3.14 environment; deployment excluded |
| PM-02 | yes | pass | Independent component dynamics/scaling tests, 40 settings including 20/30; tolerances 1e-12 arrays, 1e-11 summaries, 1e-9 derivative | Closed-form idealized assumptions |
| PM-03 | yes | pass | `browser/results.json`, reviewed `scripts/test_browser.py`: visible keyboard sliders drive server-backed source/metrics, zero/horizontal/vertical states | Chrome 156 local loopback; no captured primary-page console or JS page errors |
| PM-04 | yes | pass | Zero/vertical/horizontal/bounded inputs, finite grid arrays, useful rejection checks | Browser representation assessed separately |
| PM-05 | yes | pass | Metadata/Flask content and desktop/mobile screenshot inspection: units/objectives/assumptions and three correct revealable questions | Faculty/learning effectiveness review separate |
| PM-06 | yes | pass | Browser suite uses two contexts; first-session changes leave second speed/angle/source unchanged; independent Document tests corroborate | Local browser contexts |
| PM-07 | yes | pass | Reviewed desktop 1366×1000 and narrow 390×844 screenshots; suite exercises controls, checks no horizontal overflow/clipped canvases | Long vertical mobile page; tested viewport range only |
| PM-08 | yes | pass | Spec/plan, Builder adaptation reports, actual explicit reviewer dispatch/read trace and source hashes | Final complete-stage artifact assembly belongs to root; no automatic discovery inference |
| LR-01 | yes | pass | Same verified fresh final-root environment and shared hosting lifecycle as PM-01; both pilots exercised by final browser suite | Local development scope |
| LR-02 | yes | pass | 18 seed/count combinations preserve draws/split across sigma; split exhaustive/disjoint with floor(.75n) | Seeded CPU synthetic generator |
| LR-03 | yes | pass | Arbitrary custom data centered-sums oracle; held-out y poisoned by row-varying large values leaves coefficients/training MSE exactly unchanged | No preprocessing implemented or required |
| LR-04 | yes | pass | Independently computed predictions, signed residuals and train/test mean squared residuals | Floating-point tolerances documented in test |
| LR-05 | yes | pass | 18 zero-noise combinations recover 2/1 within 1e-12; MSE below 1e-24 | Training x varies |
| LR-06 | yes | pass | Visible sliders, seed input, actual Generate button; pending data unchanged, zero-noise recovery then n300/sigma5 updates residual/observations/line/metrics (`browser/results.json`, test source) | Local browser/server |
| LR-07 | yes | pass | Corrected text visible in refreshed desktop/mobile screenshots; shapes/units/true and fit lines/residual baseline/three feedback questions checked; QA-LR-01 closed | Human curriculum acceptance pending |
| LR-08 | yes | pass | Invalid controls, partition types/coverage, shape/nonfinite/rank cases reject | Numerical engine API scope |
| LR-09 | yes | pass | Two browser contexts preserve independent controls/data; desktop/mobile source and screenshot review plus no-overflow/canvas bounds assertions | Same viewport/local scope as PM-07 |
| LR-10 | yes | pass | Same shared loader/shell/lock/scaffold; traceable explicit reads/adaptations and second module | No matched productivity claim or automatic discovery established |

## Findings

**QA-LR-01 — instructional, medium, repaired and independently rechecked.** Trigger: hold sample count and seed fixed, change sigma from 1 to 2. Expected: distinguish this controlled comparison from comparisons changing realizations/splits. Actual: `modules/linear-regression/module.json` and final UI paragraph state finite-sample error need not increase monotonically with noise, without qualifying the changed-realization condition. In this exact model, the true line lies in the OLS design space and the held-out rows retain the same noise draws/split. Residuals therefore scale with sigma, and both errors scale as sigma squared (roundoff aside). Independent observed ratios are approximately 4 for train and test (`qa-observations.json`). Recommendation: say fixed seed/n gives MSE proportional to sigma squared; nonmonotonic comparisons can occur when realization/split changes. Preserve correct warning that training MSE need not be less than test MSE. Owner: Builder and learning-spec author (the ambiguity also occurs in the supplied spec). Reported promptly to root; no acceptance dilution or QA implementation edit.

Recheck: Builder corrected UI/metadata/README and root corrected the shared learning specification with an explicit defect record. QA read the corrected text and added independent sigma .7→2.1 checks at n=20,67,300, seed123: residuals multiply by 3 and MSE by 9. Eight QA test groups pass after repair. A first QA harness content assertion searched for literal English “sigma squared” while correct UI used “σ²”; that harness-only assertion was corrected without changing application criteria. Final repaired-code browser screenshots independently inspected: the qualified explanation is visible in assumptions and workspace. Browser recheck passes.

No engine correctness defect found in tested normal/boundary contracts. Original source licensing remains unverified as catalog states; no license clearance claimed. Separate claim-review fixture findings are in `claim-review-report.md`, and CSV extension review is in `csv-adaptation-review-report.md`.

## Performance

Eight QA test groups finished in 0.729 s; this is test-suite elapsed time, not learner-visible latency. Builder-reported local numerical benchmarks identify workload, versions, CPU, warmup/repeats and compute scope and do not promise browser latency. Neither pilot trains a neural network; epochs, GPU and training cancellation do not apply. Final browser suite elapsed 9.769 s for all scripted tasks, not per-control latency. Visible control interactions complete at both viewports; no precise browser round-trip timing is claimed. Lifecycle evidence reviewed and passes. No independent end-to-end timing measurement or productivity comparison is claimed.

## Recommendation

Both pilots are ready for human review: all 18 mandatory PM/LR criteria pass. QA-LR-01 is repaired and independently rechecked. Fresh final-root environment evidence closes the last setup criteria. Human curriculum acceptance, learning gains and promotion to approved corpus exemplar remain separate and unverified. Reviewer will update this matrix after receiving and checking the root's evidence.

## Final browser/lifecycle evidence review

Reviewed `execution-checks.json`, `all-tests.log` (14 shared +10 regression +8 projectile tests), `qa-independent-final.log`, `csv-adaptation-tests.log`, `pip-check.log`, `browser-command.log`, browser JSON and all four screenshot artifacts; read browser and lifecycle test source to assess assertions. Root executed browser automation; QA independently reviewed its evidence rather than claiming to have driven the browser. Final browser evidence uses restarted repaired-code server, Chrome 156.0.8078.74, visible controls, actual embedded Bokeh results and separate contexts; scientific and visual observations agree. Initial selector failure is retained in `browser/results-initial-selector-failure.json`; final suite passes. Shared suite log preserves productivity reader ResourceWarnings; root reports context-manager repair and stricter targeted rerun, unrelated to pilot acceptance. Final-location verification remains root-owned.

The CSV evaluation is a **numerical text parser extension only**. The broader uploaded-file UI and browser residual-comparison evaluation remains not implemented/not-run; it must not be reported completed because this narrowed fixture passes. Claim-review correctly rejects unsupported governing-equation recovery, held-out validity and training-time claims in the controlled fixture.

## Final setup closure

QA read `/Users/ngoleminh/Documents/multi-agent-platform/runs/mvp-completion-20261030/fresh-environment.json` and `clean-install-and-final-tests.log`. Environment did not preexist; Python3.14 venv creation, locked browser/runtime dependency installation, pip check, all32 shared/module tests, independent8, CSV9, setup check and final-location browser suite all exit0; server shutdown exit0. This is affirmative fresh-install evidence rather than inference from installed imports. Final-location browser suite elapsed14.808s, not per-action latency. PM-01/LR-01 now pass. Human approval, faculty suitability/learning gains, automatic role discovery, Claude execution, broader CSV upload UI and productivity reduction remain unverified/separate. No further tests or scope expansion after the user requested immediate reporting.
