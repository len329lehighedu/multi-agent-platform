# Technical Plan: RL Gridworld Lab

- Run: `rl-gridworld-20261101-01`
- Status: ready for Builder
- Scope: deterministic 4×4 tabular Q-learning lesson on the shared Flask/Bokeh host

## Boundaries and contract

`engine.py` owns pure grid transitions, seeded action selection, Q updates, episode training and greedy evaluation. `ui.py` owns document-local state, controls, callbacks and render data. `module.json` owns lesson metadata/assessment. The shared host owns discovery, home gallery and Flask/Bokeh lifecycle. No Gymnasium, worker, upload, stochastic movement or editable map.

State is `4 * row + column`; start `12`, goal `3`, hazard `10`. Actions are `(up,right,down,left)` with deltas `((-1,0),(0,1),(1,0),(0,-1))`. Ordinary reward is `-.05`, goal `1`, hazard `-1`, and maximum episode length is 40. A wall action stays in place. Goal/hazard arrival sets `terminated`; the 40th nonterminal action sets `truncated`. Terminal arrival on step 40 takes precedence. Stepping from a terminal state is invalid.

Use NumPy `float64` Q shape `(16,4)`. Records should expose transitions, exploratory/greedy decision, update terms, episode return/steps/outcome, and evaluation metrics. Training/evaluation share only Q; evaluation does not mutate Q or consume the training RNG.

## Engine API and semantics

```python
new_q_table()
transition(state, action, steps_taken)
choose_training_action(q, state, epsilon, rng)
greedy_action(q, state)
apply_q_update(q, transition, alpha, gamma)
train_episodes(q, rng, episodes, alpha, gamma, epsilon)
evaluate_greedy(q, episodes=100)
```

Validate finite α/γ/ε in `[0,1]`, episodes in `[1,500]`, state/action and Q shape. Training first draws `rng.random()`; below ε selects uniformly among all actions, otherwise uniformly among tied maximum actions using the same session RNG. Evaluation uses the first maximum in fixed up/right/down/left order.

For terminal transitions `future=0` and `target=reward`. Otherwise `future=max Q[next_state]` and `target=reward+gamma*future`. Truncation bootstraps because the time limit is not an environment terminal, then ends the episode. `train_episodes` begins each requested episode at state 12, mutates Q, consumes the supplied RNG, and returns summaries.

## Session and reset

Each `build_document(doc)` owns its Q, `default_rng(42)`, applied seed, current state/step/return/episode, history, last update, done flag and busy guard.

- Step continues the current episode; after done, the next step starts fresh while retaining Q.
- Batch discards a partial episode, starts complete episodes, retains Q, appends summaries and finishes at a fresh start.
- Reset recreates zero Q and RNG from the displayed seed, clears all history/counters/update and returns to start.
- α/γ/ε changes apply next action without erasing Q. Seed applies after reset. Settings changes mark comparisons uncontrolled/stale.

## Bokeh design

Named controls: `step_training`, `train_episodes`, `reset_q`, sliders `alpha`, `gamma`, `epsilon`, numeric `episodes` and `seed`. Use defaults `.3`, `.95`, `.2`, `100`, `42`.

The board source holds 16 cells, label/color/current marker/policy arrow/max Q and four action Q values. A square figure displays `S/G/H/A` plus color and hover values. Other named outputs show current action values, all last-update terms, episode-return history, outcome counts, 100-episode frozen greedy evaluation and status. Layout is a responsive board/control row above update/curve content.

Callbacks validate, use a busy guard, disable action buttons, perform bounded synchronous work, prepare updates, publish related changes under `doc.hold("combine")`, and restore controls in `finally`. Maximum training work is 500×40 transitions; evaluation is at most 100×40. Keep synchronous only if measured runtime is acceptable.

## Home gallery

Adding valid lesson metadata makes module discovery return two modules, so `/` already renders `index.html` rather than redirecting to the single dashboard. Verify both cards and module links. A small gallery intro edit to “Interactive STEM learning modules” is allowed. No Bokeh home tab is required.

## Packages

Reuse the locked Python/NumPy/Bokeh/Flask environment. NumPy supplies Q arrays and seeded `Generator`; Bokeh supplies per-session documents/widgets/plots; Flask supplies the existing gallery and lesson shell. Builder must record actual interpreter/package versions. No new scientific dependency is needed.

## Verification and benchmark

Independent tests cover ordinary/wall/goal/hazard/truncation, terminal-on-step-40 precedence, nonterminal update (`old=.2,reward=-.05,next=.4,α=.5,γ=.9 → target=.31,new=.255`), terminal update (`.2 → .6`), truncation bootstrap, tie rules, same-seed traces, reset and evaluation immutability.

Build two Bokeh documents, trigger named controls and verify isolation, update content, requested batch length, reset and settings warning. Flask tests verify gallery and links. Live browser checks board/Q/policy, step/train/reset/evaluation, WebSocket behavior, questions, narrow viewport and two sessions.

Record hardware/OS/versions, config/seed and five repetitions for: a controlled 20,000-update engine kernel; `train_episodes(500)` actual transition count; live 500-episode callback plus evaluation/render. Report observed times without advance promises.

## Files and criteria

| Files | Work | Criteria |
| --- | --- | --- |
| module metadata/README/requirements | lesson and setup | RL-05, RL-08 |
| `engine.py` | environment, Q learning, evaluation | RL-01..03 |
| `ui.py` | document state and interactions | RL-03, RL-04, RL-07 |
| module tests/benchmark | numeric, documents, gallery, timing | RL-01..03, RL-06..08 |
| gallery wording/project README if needed | home discovery and usage | RL-06, RL-08 |
| build report | actual commands/results/limitations | RL-08 |

Adapt the scaffold's pure engine/UI boundary, SINDy revision `d58a9a9b…` per-session state and lesson shell, current module named-model/testing patterns, and shared runtime/gallery. Do not modify Neural Equation Finder. Human instructional review remains pending.
