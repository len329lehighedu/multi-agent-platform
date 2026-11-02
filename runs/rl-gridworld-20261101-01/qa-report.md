# QA report: RL Gridworld Lab

## Context

- Run ID: `rl-gridworld-20261101-01`
- Module: `modules/reinforcement-learning/`
- Review date: 2026-11-01
- Reviewer execution: native `stem-qa-reviewer` subagent `/root/rl_qa`
- Workspace revision before uncommitted run changes: `e88ef3347663602faadc7619043cbe83740addcd`
- Specifications reviewed: `brief.md`, `learning-spec.md`, `technical-plan.md`, `handoff-03-builder-qa.md`, and `build-report.md`
- Exemplar reviewed independently: `corpus/catalog.json`, `corpus/sindy.md`, and original SINDy `main.py`, `flask_app.py`, and `templates/index.html` at catalog revision `d58a9a9b315273e2675216593a1a4bb86a57ccb4`
- Environment: macOS 26.1 arm64 CPU; CPython 3.14.0; NumPy 2.4.1; Bokeh 3.8.2; Flask 3.1.2
- Browser: Google Chrome through the connected browser QA surface; live local Flask `127.0.0.1:8080` and Bokeh `127.0.0.1:5006`

## Criterion results

| Criterion ID | Mandatory? | Status | Method | Evidence path or observation | Limitation |
| --- | --- | --- | --- | --- | --- |
| RL-01 | Yes | pass | Independent transition oracles | `.venv/bin/python runs/rl-gridworld-20261101-01/verification/test_rl_acceptance.py`: ordinary start-up move, left wall, goal, hazard, 40th-step truncation, and terminal-on-step-40 precedence passed. Four QA tests passed in 0.487 s. | Fixed deterministic map only, as specified. |
| RL-02 | Yes | pass | Hand calculation independent of implementation | QA oracle checked nonterminal `target=-.05+.9×.4=.31`, `new=.2+.5×(.31-.2)=.255`; terminal future `0`, target `1`, new `.6`; truncation bootstrap target `.31`. All passed. | None for accepted equations. |
| RL-03 | Yes | pass | Seeded engine comparison plus UI reset | Two independently initialized seed-42, 60-episode traces and Q tables were identical; evaluation left Q unchanged. A document was trained, reset with seed 99, then showed empty history and zero visible Q values. | Reproducibility applies to the locked versions and configuration recorded here. |
| RL-04 | Yes | pass | Live browser, Python callbacks, visual inspection | Board visibly showed `G`, `H`, `A · S`, arrows and max-Q labels. Hovering state 0 displayed state and four Q values. Step reported state 12 → down, reward −.05, old Q 0, target −.05, new Q −.015. A 500-episode click completed in 0.072 s and published 478 goal, 22 hazard, 0 truncation plus 100% frozen greedy evaluation. Reset restored zero Q/history. Python callback-driven changes prove the live Bokeh server connection was functioning; browser console had no errors. | Visual review used Chrome on this machine, not a cross-browser matrix. |
| RL-05 | Yes | pass | Metadata, rendered content and assessment review | Live lesson showed four observable objectives, deterministic/reward assumptions, alpha/gamma/epsilon explanation, warning against optimality claims, and four questions. Expanding Question 1 showed terminal future 0 and new Q .60. Content addresses reward-vs-Q, gamma, epsilon, truncation and reset misconceptions. | Human learning gains and faculty approval were not measured and remain separate from QA. |
| RL-06 | Yes | pass | Flask response and live gallery | Root browser page showed cards and working links for Neural Equation Finder and RL Gridworld Lab. Automated Flask check also passed. | None. |
| RL-07 | Yes | pass | Independent two-document test and two live browser tabs | QA test confirmed no shared Bokeh models; stepping/training one document left the other unchanged. In two live tabs, Tab 1 reported episode 1 step 1 and Q update while Tab 2 remained `Ready · seed 42 · zero Q table` with `0 completed`. | Both browser sessions used the same Chrome installation, but had distinct Bokeh server sessions. |
| RL-08 | Yes | pass | README/config review and repeated benchmark | Locked versions and launch commands are recorded. QA rerun measured five repetitions: 20,000-update kernel median 0.084294 s (0.083701–0.087064); 500 training episodes median 0.050549 s (0.049289–0.052323), 3,792 actual transitions and 20,000 allowed maximum; document callback plus evaluation/publication median 0.052684 s (0.052554–0.053391). Live 500-click status reported 0.072 s. | Callback microbenchmark runs a Bokeh document in process; the separate live observation covers browser-visible completion on localhost. These are measurements, not duration promises. |

## Exact verification evidence

### Independent acceptance tests

```text
$ .venv/bin/python runs/rl-gridworld-20261101-01/verification/test_rl_acceptance.py
test_q_update_oracles_calculated_directly ... ok
test_seeded_training_repeats_and_evaluation_is_read_only ... ok
test_transition_oracles_from_grid_coordinates ... ok
test_documents_are_isolated_and_reset_clears_visible_state ... ok
Ran 4 tests in 0.487s — OK
```

The independent source is `verification/test_rl_acceptance.py`. It uses constants and expected arithmetic from the accepted brief; it does not import Builder tests.

### Module and platform regression

```text
$ .venv/bin/python -m unittest discover -s modules/reinforcement-learning/tests -p 'test_*.py' -v
Ran 6 tests in 0.346s — OK

$ .venv/bin/python scripts/test_all.py
Platform: 15/15 passed
Neural Equation Finder: 13/13 passed
RL Gridworld Lab: 6/6 passed
All automated non-browser suites passed.

$ python3 scripts/check_setup.py
Configuration: 4 roles, 8 skills; 0 error(s)

$ git diff --check
PASS (no output)
```

The first non-escalated local server attempt could not bind localhost (`Operation not permitted`). The same documented server command was then run with localhost binding permitted and printed `READY http://127.0.0.1:8080/ (Bokeh 5006)`. This was a sandbox constraint, not an application failure.

### Live browser observations

1. `/` rendered the home heading and both module cards; the RL card navigated to `/modules/reinforcement-learning/`.
2. The lesson shell rendered objectives, model assumptions, experiment and four assessment items.
3. The embedded Bokeh content appeared after connection. Board symbols and policy/value labels were visible; hovering a cell displayed State, Up, Right, Down and Left values.
4. **Step one transition** caused a server-side Python callback and changed status, the board Q value, and the full update breakdown.
5. **Train episodes** with 500 produced 500 completed outcomes, updated policy/Q values, the return plot and frozen evaluation.
6. **Reset Q** restored zero values, empty outcome history and the initial evaluation.
7. At a 390×844 viewport, `innerWidth=390`, `clientWidth=390`, `scrollWidth=390`; controls and board stacked into one readable column. The viewport override was reset after the check.
8. Two live tabs demonstrated distinct state: changing Tab 1 did not change Tab 2. Both browser consoles contained zero captured errors.

## Findings

No implementation, scientific, visualization, instructional or performance defect was found against RL-01 through RL-08.

### Scientific

- Transition semantics and Q-learning arithmetic match the accepted deterministic Gridworld contract.
- Evaluation is read-only and distinguishes the fixed greedy tie rule from seeded epsilon-greedy training.
- The displayed claim is appropriately limited to observed outcomes; it does not claim optimality or generalization.

### Implementation and integration

- Flask discovery, lesson routing, Bokeh embedding, callback operation, shutdown-capable host and session isolation passed.
- The existing Neural Equation Finder regression suite remained green.

### Visualization and interaction

- Color is supplemented by `S/G/H/A`, terminal labels, arrows and numeric Q values.
- Desktop and 390 px layouts were readable with no page-level horizontal overflow.
- Hover tooltips, action values, update terms, outcomes, curve and evaluation were present.

### Instructional

- The sequence supports predict → step → train → explain and maps each objective to a visible interaction or question.
- Four questions include feedback; the lesson explicitly addresses the main accepted misconceptions.
- Faculty review and learner testing remain pending; content QA does not establish measured learning effectiveness.

### Exemplar adaptation check

| Requirement | Exemplar evidence inspected | Adaptation observed | QA conclusion |
| --- | --- | --- | --- |
| Per-session state | SINDy `main.py` constructs engine/storage inside `build_app()` | RL creates Q, RNG, episode and history inside `build_document()` | Appropriate; independently verified in documents and browser tabs. |
| Flask/Bokeh embedding | SINDy `flask_app.py` documents direct browser-to-Bokeh WebSocket | Shared runtime embeds `/lesson/reinforcement-learning` and allows Flask origins | Appropriate; live Python callbacks worked. |
| Lesson shell | SINDy HTML combines explanatory content and Bokeh workspace | Shared lesson template places objectives/assumptions beside one focused lab | Simpler and suitable for the requested beginner scope. |
| Browser evidence | SINDy case study warns source inspection is insufficient | QA ran live desktop, narrow, hover, callbacks and two-session checks | Weakness from the exemplar was addressed. |

## Performance

- Device: Apple arm64 CPU; macOS 26.1.
- Interpreter/packages: CPython 3.14.0; NumPy 2.4.1; Bokeh 3.8.2; Flask 3.1.2.
- Configuration: seed 42, alpha .3, gamma .95, epsilon .2, 500 episodes, maximum 40 steps per episode.
- Stopping rule: goal/hazard termination or 40-step truncation.
- Repeat count: five for each scripted workload; no warm-up discarded.
- Controlled kernel: exactly 20,000 repeated Q updates, median 0.084294 s.
- Training: 500 complete episodes, 3,792 observed transitions per repeat, median 0.050549 s.
- In-process document callback: 500 episodes plus 100-episode greedy evaluation and model/source publication, median 0.052684 s.
- Live browser: status reported 0.072 s for the 500-episode callback; controls returned enabled and updated immediately after completion.
- Timeout/cancellation: intentionally absent for this bounded synchronous workload. The maximum allowed work is 20,000 training transitions plus 4,000 evaluation transitions; measured behavior supports the design on this machine.

## Recommendation

All mandatory criteria RL-01 through RL-08 passed with independent numerical and live browser evidence. The module is **ready for Minh's human review**.

Human acceptance, faculty review, measured learning effectiveness, deployment, and promotion into the approved corpus are separate decisions and were not performed in this QA stage.
