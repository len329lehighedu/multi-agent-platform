# Learning Specification: RL Gridworld Lab

- Run: `rl-gridworld-20261101-01`
- Module: `reinforcement-learning`
- Presentation: `lesson`
- Status: ready for Architect
- Audience: introductory undergraduates with basic probability and arithmetic; no calculus, neural-network, Gymnasium, or prior RL knowledge required

## Scientific contract

Use a fully observed deterministic 4×4 grid, indexed in row-major order:

```text
. . . G
. . . .
. . H .
S . . .
```

Start `(3,0)`, goal `(0,3)`, hazard `(2,2)`. Actions are up, right, down, and left. A wall action leaves the agent in place. Ordinary transitions reward `−0.05`, goal `+1`, hazard `−1`. Entering the goal or hazard terminates; 40 actions truncates. Q initializes to zero. Training uses seeded epsilon-greedy tabular Q-learning; evaluation freezes Q and acts greedily. Terminal transitions use future value zero.

`Q(s,a) ← Q(s,a) + α [r + γ max Q(s′,a′) − Q(s,a)]`

Training should choose uniformly among tied maxima using the seeded RNG. Greedy evaluation should use the fixed action order up, right, down, left. This lesson makes no claim of general or optimal behavior.

## Objectives

| ID | Learner can… | Evidence |
| --- | --- | --- |
| LO-1 | Identify state, action, reward, and next state in one transition. | Step one transition and read the highlighted board/update. |
| LO-2 | Explain nonterminal and terminal Q updates, including zero terminal future value. | Inspect an update and answer Question 1. |
| LO-3 | Explain how α, γ, and ε affect learning without changing the environment. | Reset, change one control, retrain, and answer Questions 2–3. |
| LO-4 | Judge a policy from repeated outcomes rather than one success. | Read the curve/evaluation and answer Question 4. |

## Lesson sequence

1. **Predict:** identify the start, goal, hazard, possible actions, and a plausible route.
2. **Observe:** step one training transition and show state, selected action, exploratory/greedy choice, reward, next state, old Q, target, TD error, and new Q.
3. **Train:** run 1–500 episodes synchronously, retaining the current Q table and starting a fresh episode for a batch.
4. **Explain:** inspect policy arrows, Q values, return curve, outcome counts, and a fixed greedy evaluation. State that one goal episode does not establish reliability or optimality.

## Controls and outputs

Controls: **Step one training transition**, **Train episodes**, **Reset Q**, α `[0,1]` default `.3`, γ `[0,1]` default `.95`, ε `[0,1]` default `.2`, episodes integer `[1,500]` default `100`, seed nonnegative integer default `42`. A new step after termination/truncation starts another episode. Reset clears Q, histories, counters, current episode and recreates the RNG from the displayed seed. Changing settings does not silently erase learned Q; status asks the learner to reset for a controlled comparison.

Required outputs: readable board with symbols/text plus color; policy arrow and maximum Q per nonterminal cell; four action Q values for the current state; complete last-update explanation; distinct terminal/truncated status; episode-return curve with labeled axes; goal/hazard/truncation counts; greedy evaluation with Q frozen and exploration off; status identifying exploratory versus greedy actions; root gallery with both installed modules.

## Misconceptions

- Reward is one transition's signal; Q estimates cumulative future reward for a state-action pair.
- γ weighs the future estimate; it does not change immediate rewards.
- ε randomizes the training agent's action; the environment remains deterministic.
- An arrow or one successful episode does not prove optimality.
- Truncation is the step limit, distinct from hazard termination.
- A new episode keeps learning; **Reset Q** clears learning.

## Assessment with feedback

1. **A goal transition has old Q=0.20, α=0.5, reward +1. What future term and new Q are used?** Future value is zero because the goal is terminal. `Qnew = 0.20 + 0.5(1 − 0.20) = 0.60`.
2. **What does increasing γ change?** It increases the weight on estimated future state value in nonterminal updates; rewards and movement do not change.
3. **Why can ε>0 help when all Q values start at zero?** Exploration tries actions that tied or incomplete estimates might miss, producing evidence that separates their values. The trace still depends on seed and tie handling.
4. **One episode reaches the goal. Does that prove a reliable or optimal policy?** No. Inspect repeated greedy evaluations and the policy/Q table; the lesson reports outcomes without inferring optimality from one success.

## Acceptance mapping

| Criterion | Required evidence |
| --- | --- |
| RL-01 | Independent ordinary, wall, goal, hazard, and truncation transition tests. |
| RL-02 | Hand-calculated nonterminal and terminal Q-update tests. |
| RL-03 | Same-seed trace reproduction and complete reset-state inspection. |
| RL-04 | Live browser evidence for board, policy/Q display, update breakdown, step, train, reset. |
| RL-05 | Objectives, explanations, misconceptions and at least three feedback questions present. |
| RL-06 | Root gallery shows working links to both modules. |
| RL-07 | Two documents/sessions isolate Q, RNG, episode and history. |
| RL-08 | Versions, bounds and measured 500×40 maximum-work timing recorded. |

## Exemplar adaptations

| Requirement | Exemplar | Adaptation | Verification |
| --- | --- | --- | --- |
| Lesson shell | `corpus/sindy.md`, SINDy `templates/index.html` at catalog revision `d58a9a9b…` | Short single-page predict–observe–explain flow | Desktop/narrow browser review |
| Assessment | SINDy questions fragment; scaffold `module.json` | Four compact RL questions in metadata | Metadata and browser checks |
| Session state | SINDy `main.py`; `stem_platform/runtime.py` | Create Q, RNG, episode, history inside `build_document` | Two-document isolation test |
| Scientific separation | Scaffold engine/UI and SINDy engine pattern | Pure transition/Q functions in `engine.py` | Independent engine tests |
| Controls/diagnostics | SINDy train tab; current neural module UI | Reduce to RL controls, one board, update panel and curve | Browser interactions |
| Gallery | `stem_platform/runtime.py` and existing index | Preserve neural module and add valid lesson metadata | Root/link checks |
| Runtime | SINDy synchronous-callback limitation | Permit synchronous work only after measuring bounded 500×40 load | Benchmark/UI check |

Deferred: slippery movement, editable maps, manual play, SARSA, neural networks, Gymnasium, animation framework, multi-agent RL, background workers, and measured learning-gain claims. Human instructional review remains pending; there are no blocking architecture questions.
