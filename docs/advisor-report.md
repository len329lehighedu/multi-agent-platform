# Advisor handoff: STEM module platform MVP

Prepared for Minh, Raghu and faculty reviewers, October 30, 2026. Human acceptance and curriculum approval remain pending.

The platform now has a runnable local Flask/Bokeh/HTML scaffold and two implemented lessons: projectile motion and linear regression. This addresses the original problem of repeatedly building scientific calculations, interactive plots, learning content, web integration and verification from scratch. The evidence demonstrates a working local implementation and reuse across two topics; it does not establish reduced human development effort or improved student learning.

The final operational project root is `/Users/ngoleminh/Documents/multi-agent-platform`. Execution evidence records the actual build and test staging root, `/private/tmp/stem-platform-completion-20261030`, and environment `/private/tmp/stem-platform-venv-20261030`. Those historical paths should remain in logs. A fresh .venv was created and dependencies installed at the operational root; all suites and browser checks were rerun there successfully. See fresh-environment.json and clean-install-and-final-tests.log. Historical staging paths remain evidence of where earlier commands ran.

## What was implemented

The shared host, `stem_platform/runtime.py`, validates module metadata, loads each lesson package and provides a Flask gallery and lesson pages. A single local process owns two loopback endpoints: Flask on port 8080 and Bokeh on port 5006 by default. The browser connects directly to the embedded Bokeh application using its WebSocket. Signal handling closes both services; a partial Bokeh startup failure releases the Flask port. This is a local development host.

Each module separates pure scientific calculations (`engine.py`), session-specific Bokeh controls and plots (`ui.py`), and learning objectives, assumptions and questions (`module.json`). Shared HTML/CSS is in `web/`. `templates/module-scaffold/` contains a runnable coefficient-exploration starter; `scripts/create_module.py` copies it under a validated new module ID and refuses to overwrite an existing module. `scripts/serve.py` launches the gallery or selected modules. `scripts/test_all.py` runs shared and pilot automated suites.

The workflow uses an orchestrator plus Learning Planner, Architect, Builder and QA Reviewer roles. Persistent learning specifications, technical plans, Builder reports and QA records make handoffs reviewable. Actual native Codex subagents executed explicit role assignments and read their named skills as files. CLI prompt inspection at the new root confirms AGENTS.md and all eight skill names are exposed. Automatic custom-role selection and live Claude execution remain unverified; configuration files alone are not evidence of those capabilities.

The corpus provides source-backed examples in context. Agents inspected the SINDy catalog, case study and original sources, checked relevant hashes, and recorded adaptations. Examples include per-session state, separating scientific computation from UI, Flask/Bokeh embedding, and distinguishing fitting from unseen-data evaluation. The new lessons simplify the interaction for their own objectives rather than adopting SINDy's four-tab structure or scientific algorithm. This is contextual reuse and reasoning, not model-weight training. Original-source licensing remains unverified; the implementation does not claim license clearance for redistribution of SINDy sources.

## Concrete learner behavior

**Projectile motion:** learners change speed from 0–50 m/s and launch angle from 0–90 degrees. The trajectory, flight time, horizontal range and maximum height update immediately. The model uses constant gravity 9.81 m/s², no drag and equal launch/landing heights. It handles zero speed, horizontal and vertical launches explicitly. Three questions explain speed scaling, complementary angles and the limits of the assumptions. Plot axes have position units; their screen scales may differ.

**Linear regression:** learners choose noise standard deviation 0–5, 20–300 observations and an integer random seed, then press **Generate and fit**. Edits remain pending until that button commits the configuration. Synthetic observations follow `y = 2x + 1 + σz`; 75% of rows, rounded down, train an ordinary least-squares line with an intercept. Held-out rows never enter fitting. Plots show training/test observations, true/fitted lines and signed residuals; summaries show fitted coefficients and separate training/test MSE. Three questions explain residual signs, noiseless recovery and held-out evidence. With seed and sample count fixed, the same noise draws and split are reused: residuals scale with σ and MSE with σ², within floating-point roundoff.

A separate **CSV numerical adaptation fixture** parses in-memory text with exact `x,y` headers, 20–300 finite numeric rows and a seeded split, then calls the shipped regression engine. It demonstrates parser-to-engine reuse and numerical residual evaluation. It is not a browser upload control, file transport workflow or shipped CSV lesson. Its zero `standard_noise` field is a compatibility placeholder, not evidence that uploaded observations are noiseless.

## Verification and a real repair

Evidence lives in `runs/mvp-completion-20261030/`. The recorded environment is CPython 3.14.0, NumPy 2.4.1, Bokeh 3.8.2 and Flask 3.1.2 on macOS arm64 CPU. Exact dependency pins are in `requirements.lock.txt`; `pip-check.log` records the dependency consistency check. Verified support applies to this recorded environment, not every Python/platform combination.

| Evidence | Recorded result | Meaning and limit |
| --- | --- | --- |
| `all-tests.log` | 32 passing tests: 14 shared/setup/evaluation tests, 10 regression tests and 8 projectile tests | Includes real endpoint startup/shutdown, partial-startup cleanup, generated scaffold, numerical oracles, validation and Python Document interactions. It is not solely a browser test. |
| `csv-adaptation-tests.log` | 9 passing fixture tests | CSV parsing, boundaries, finite data, seeded partitions and reuse of shipped regression engine; no upload UI claim. |
| `qa-independent-final.log` | 8 passing independent QA test groups | Component-dynamics projectile checks, custom-data regression oracles, held-out response poisoning, noise scaling, validation, Document isolation and independent CSV checks. These supplement Builder tests. |
| `execution-checks.json` | Exit code 0 for main tests, CSV tests, final independent QA, dependency check and browser command | Process-level success; detailed logs define actual scope. |
| `browser/results.json` | Five browser check groups passed | Gallery; visible controls and session isolation for both lessons; responsive layout/feedback; captured browser errors. |
| `browser/*-desktop.png`, `browser/*-mobile.png` | Four screenshots | Actual inspection at 1366×1000 and 390×844, with no recorded horizontal overflow or clipped canvases. |

Browser automation used Chromium 156.0.8078.74 and the real local Flask page on port 8088. It operated visible controls, checked projectile edge cases, regression pending/commit behavior and zero-noise recovery, compared separate browser contexts, revealed feedback and exercised narrow-screen controls. No captured JavaScript page errors or primary-page console errors were reported. Suite duration is test execution time, not a learner-latency or productivity benchmark. An initial selector failure is preserved separately in `browser/results-initial-selector-failure.json`; the corrected harness produced the passing `results.json`.

Independent QA found a substantive instructional defect, **QA-LR-01**: the initial warning said errors need not increase monotonically with noise without qualifying that seed/sample count can change. In this generator, fixed seed and sample count preserve the draws and split, so doubling σ quadruples both MSE values. The Builder corrected metadata, UI explanation and README; the learning specification was corrected too. Added metamorphic and independent tests verify the scaling. The warning about comparisons across different realizations remains appropriately qualified. This repair shows a real review-and-correction cycle rather than merely a collection of passing tests.

The final independent QA report accepts all 18 mandatory PM/LR criteria for human review. Fresh final-location environment creation, pinned installation, dependency check, all32main tests, independent8groups, CSV9tests and browser suite passed; both endpoints shut down cleanly. QA-LR-01 is closed. Human curriculum acceptance remains separate.

Two behavioral evaluations complement the pilots. `claim-review-report.md` rejects an isolated intentionally misleading fixture that claims equation recovery from hardcoded prediction, supplies only training error and promises unmeasured timing. `csv-adaptation-report.md` and its independent review demonstrate the narrower numerical extension. Neither fixture is silently promoted into an approved corpus exemplar.

## Five-minute demonstration

Prepare the environment before the meeting:

```sh
cd /Users/ngoleminh/Documents/multi-agent-platform
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
.venv/bin/python scripts/serve.py
```

Open `http://127.0.0.1:8080/` after the READY message. If ports are occupied, use `--port 8088 --bokeh-port 5018` and open port 8088.

1. **First minute:** introduce the gallery and explain the common lesson structure: objectives, assumptions, exploration and feedback.
2. **Minutes 1–2:** open projectile motion. Compare 20 and 40 m/s at 30°: time doubles, range and height quadruple. Compare 30° and 60° at the same speed: equal range, different height/time. Reveal one answer and name the no-drag/equal-height assumptions.
3. **Minutes 2–4:** open regression. Set noise to zero and generate: slope/intercept approach 2/1 and both errors approach zero. Restore nonzero noise, generate, then change noise while preserving seed/count and generate again. Explain the σ² error scaling, residual sign and training-only fit. Point out that controls do not silently replace committed results before Generate.
4. **Final minute:** show the evidence table, QA-LR-01 repair and reusable scaffold. Explain that human curriculum review and a matched productivity study are the next decisions. Stop the server with Ctrl+C and observe the endpoint shutdown message.

## Files reviewers should inspect

Start with this report and `docs/usage.md` for setup, operating and testing instructions. Review `runs/mvp-completion-20261030/learning-spec.md`, `technical-plan.md` and `qa-report.md` for requirements and criterion-to-evidence mapping. The two Builder reports record provenance, adaptations, commands, measured compute scope and repairs. Inspect `stem_platform/runtime.py`, `web/`, `templates/module-scaffold/`, and the two `modules/` directories for implementation. Inspect `browser/results.json` and screenshots alongside test logs; a Flask HTTP response alone does not prove embedded interaction.

For a repeat verification, run `.venv/bin/python scripts/test_all.py`, the CSV fixture suite and `independent-science-tests.py` using their recorded commands, then follow the browser setup/command in `docs/usage.md`. Dependency installation and browser tooling are separate prerequisites. Preserve failures and not-run checks in the run record instead of replacing them with successful historical smoke results.

## Claims and decisions for advisors

The supported claim is that a reusable local scientific lesson scaffold and two topic-specific interactive pilots have been implemented and exercised, with explicit agent/skill assignment, numerical checks, actual browser evidence and an independently detected instructional repair. Earlier setup smoke remains historical evidence, not substitute application acceptance.

This work has not been deployed. It contains no neural equation-discovery module and does not show that a neural predictor yields symbolic governing equations. It does not train model weights, establish learning gains, prove production readiness or demonstrate automatic custom-role selection or live Claude support.

`productivity-status.json` records **zero matched task pairs** and status **insufficient-data**. The 30% effort-reduction target is a proposed evaluation threshold, not an achieved result. A useful follow-up is at least three matched task pairs with identical acceptance criteria, measured active human effort, elapsed time, corrections, quality and available usage/cost; setup and maintenance effort must be reported separately. Model usage/cost unavailable in this run must remain unavailable, not estimated as fact.

Minh and advisors should review audience suitability, scientific explanations, the final QA matrix and operational-root setup before human acceptance. Feedback should be saved as proposed corpus improvements. Neither generated lesson is yet an approved teaching exemplar solely because automated checks pass.
