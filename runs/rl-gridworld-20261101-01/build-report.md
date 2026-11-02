# Builder Report: RL Gridworld Lab

- Run: `rl-gridworld-20261101-01`
- Builder execution: native `stem-builder` subagent `/root/rl_builder`
- Status: ready for independent QA
- Module: `modules/reinforcement-learning/`
- Device: CPU, Apple arm64
- Seed/configuration used for reproducibility and benchmark: seed `42`, α `.3`, γ `.95`, ε `.2`

## Result

Implemented the fixed deterministic 4 × 4 Gridworld and seeded tabular Q-learning contract. The lesson provides a board with non-color symbols, greedy policy arrows and maximum Q values, one-transition stepping, bounded batch training, complete last-update terms, current-state action values, return history, outcome counts, frozen 100-episode greedy evaluation, reset, and settings guidance. Each Bokeh document creates its own Q table, RNG, current episode, history and widgets.

The platform root now renders a two-card home gallery for Neural Equation Finder and RL Gridworld Lab. The existing neural module was not edited.

No scientific-output conflict was found. The bounded synchronous strategy was retained after measurement; a worker would add complexity without serving this measured workload.

## Changed paths

- `modules/reinforcement-learning/__init__.py`
- `modules/reinforcement-learning/engine.py`
- `modules/reinforcement-learning/ui.py`
- `modules/reinforcement-learning/module.json`
- `modules/reinforcement-learning/README.md`
- `modules/reinforcement-learning/requirements.txt`
- `modules/reinforcement-learning/tests/test_module.py`
- `modules/reinforcement-learning/tests/benchmark.py`
- `web/templates/index.html`
- `README.md`
- `runs/rl-gridworld-20261101-01/build-report.md`

The `__init__.py` and requirements file came from `templates/module-scaffold`; requirements continue to reference the platform lock file. No new dependency was added.

## Acceptance criteria addressed

| Criterion | Implementation and Builder evidence | Builder status |
| --- | --- | --- |
| RL-01 | Pure `transition` covers ordinary moves, wall stays, goal/hazard termination, truncation and terminal-on-step-40 precedence; independent tests pass. | verified |
| RL-02 | `apply_q_update` exposes old Q, future, target, TD error and new Q; hand-calculated nonterminal `.255`, terminal `.6`, and truncation-bootstrap tests pass. | verified |
| RL-03 | Seeded tie/action/training traces reproduce; document reset restores zero Q, fresh seeded RNG, empty history and start state. | verified |
| RL-04 | Board, policy/Q display, step, train, reset, evaluation and publication callbacks are implemented; Bokeh document callback tests pass. Real browser interaction remains for QA. | implemented; document verified; browser not run |
| RL-05 | Four objectives, four assumptions/misconceptions, and four questions with feedback are present in lesson metadata and rendered by the shared shell. | verified by metadata/Flask tests; human review pending |
| RL-06 | Discovery returns both module IDs; root Flask response contains both titles and RL link; wording was updated for the gallery. | verified |
| RL-07 | Two independently built Bokeh documents share no models; mutating one leaves the other's board/history unchanged. | verified |
| RL-08 | Setup, rules, bounds, seed, versions and measured five-repeat timings are recorded here and in the module README/benchmark. | verified |

## Checks actually executed

1. `.venv/bin/python -m unittest discover -s modules/reinforcement-learning/tests -p 'test_*.py' -v`
   - Result: PASS, 6 tests in `0.506 s` on the final code.
   - Covers engine behavior, numeric oracle, seeded repeatability, input validation, two-document isolation, callback publication/reset, metadata and Flask gallery.
2. `.venv/bin/python scripts/test_all.py`
   - First sandbox run: 13 checks passed and 2 startup checks could not bind localhost (`PermissionError: Operation not permitted`). This was an environment restriction, not an application assertion failure.
   - Rerun with localhost binding allowed: PASS, all 15 platform tests, 13 Neural Equation Finder tests and 6 RL tests. The suite reports that both endpoints start and shut down cleanly.
3. `.venv/bin/python modules/reinforcement-learning/tests/benchmark.py`
   - Result: PASS; final figures below. Callback publication asserted a 500-point episode history after each repeat.
4. `.venv/bin/python -m compileall -q modules/reinforcement-learning`
   - Result: PASS.
5. `python3 scripts/check_setup.py`
   - Result: PASS; 4 roles, 8 skills, 0 errors. Its scope is static local checks.
6. `git diff --check`
   - Result: PASS.

Live browser interaction, WebSocket inspection, narrow-viewport screenshot review and two real browser-session comparison were not run by Builder. They are mandatory QA work for RL-04/RL-07 before the run can be called complete.

## Measured benchmark

Measured on CPython `3.14.0`, macOS `26.1` arm64, CPU, NumPy `2.4.1`, Bokeh `3.8.2`, Flask `3.1.2`. Five repetitions each; no warm-up was removed.

| Workload | Observations | Median | Min–max |
| --- | ---: | ---: | ---: |
| Controlled Q-update kernel | 20,000 updates/repeat | `0.087386 s` | `0.085727–0.089502 s` |
| `train_episodes(500)` | 500 episodes; 3,792 actual transitions/repeat; 20,000 allowed maximum | `0.051949 s` | `0.051325–0.055597 s` |
| Bokeh train callback | 500 episodes plus 100-episode evaluation and model/source publication | `0.053614 s` | `0.053400–0.053978 s` |

These are observations from this machine, not duration promises. The measured callback path is sufficiently small for the plan's synchronous design.

## Exemplar adaptations

| Requirement | Inspected source | Observed pattern | Adaptation | Verification |
| --- | --- | --- | --- | --- |
| Scientific separation | `templates/module-scaffold/engine.py`, `ui.py` | Pure computation imported by a Bokeh builder | Expanded into a standalone Gridworld/Q engine while keeping UI session state separate | engine tests without Bokeh |
| Per-session state | SINDy `main.py` at catalog revision `d58a9a9b315273e2675216593a1a4bb86a57ccb4`; current neural `ui.py` | Engine/storage/widgets are constructed for each document | Q, RNG, episode and history are allocated inside `build_document` | two-document isolation test |
| Flask/Bokeh shell | SINDy `flask_app.py` and `templates/index.html`; shared `stem_platform/runtime.py` | Flask embeds a separately served Bokeh document; browser connects to both services | Reused shared lifecycle and lesson template; metadata drives discovery and assessment | full startup suite and Flask tests |
| Named controls/publication | current Neural Equation Finder UI/tests | Named Bokeh models support callback and session verification; related results publish together | Named RL controls/sources, busy guard and `doc.hold("combine")` publication | document callback tests |
| Learner flow | `corpus/sindy.md`, SINDy HTML, shared `lesson.html` | Explanatory shell surrounds an interactive workspace | Reduced to predict → step → train → explain with four feedback questions | metadata/content check; browser review pending |
| Gallery | shared runtime and existing `index.html` | Valid metadata is discovered automatically | Added valid lesson metadata and lightly revised gallery intro | root response lists both cards |

Original SINDy source was available and inspected at `/Users/ngoleminh/STEM VISUALIZATION/SINDy`. `check_setup.py` reported no catalog hash drift.

## Known limitations and deferred work

- Deterministic fixed map only; no slippery motion, editable map, SARSA, deep RL, replay buffer, Gymnasium, animation framework or multi-agent environment.
- The plot reports training returns and fixed greedy evaluation; it does not prove optimality or generalization.
- Changing α/γ/ε retains learned Q by design; the UI asks learners to reset before controlled comparisons.
- Batch training discards a partial stepped episode and starts complete episodes, matching the technical plan.
- Human instructional review is pending.
- Deployment was not requested or run.

## Builder → QA handoff

Run the mandatory live browser checks at `/` and `/modules/reinforcement-learning/`: confirm both gallery cards; visible `S/G/H/A` board cues; policy/Q hover and current action values; one-step update terms; 500-episode train publication; reset; frozen evaluation; questions; no page-level overflow at desktop and narrow viewports; WebSocket operation; and isolation across two browser contexts. Independently recheck RL-01/RL-02 rather than relying only on Builder tests. Any application defect should return to Builder within the one allowed repair cycle.
