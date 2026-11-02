# Reinforcement Learning module: research and proposed brief

Date: 2026-11-01. Status: research proposal; no module implementation or RL benchmark has been run.

## Recommendation

Build a beginner-friendly **RL Gridworld Lab** as a `lesson` module. A learner controls a small agent on a 4×4 board, then watches a tabular Q-learning agent learn the same task. Start with deterministic movement and a fixed map; offer stochastic movement as a second experiment. The central question is: **How can an agent learn which action to take from rewards received over repeated interactions?**

This assumes introductory undergraduate learners who know basic probability and averages but have not studied RL. The lesson should explain the Q update visually before exposing its notation. This is a proposed audience, not a confirmed requirement.

## RL in one page

At time `t`, a learner agent observes state `s_t`, chooses action `a_t` under policy `π`, and receives reward `r_{t+1}` and next state `s_{t+1}` from the environment. One complete attempt is an **episode**. The aim is to maximize expected cumulative reward, usually discounted by `γ`, rather than to maximize only the next reward. Exploration tries uncertain actions; exploitation chooses the action currently believed best. This is a sequential decision problem: actions can change future states and future reward opportunities. A policy is a mapping from states to actions or action probabilities. [Sutton and Barto, *Reinforcement Learning: An Introduction*, 2nd ed.](https://mitpress.mit.edu/9780262039246/reinforcement-learning/)

For this first module, the agent stores one value `Q(s,a)` for each grid cell and available action. With ε-greedy behavior, it takes a random action with probability `ε` and otherwise selects an action with the largest current Q value. After a transition it updates:

`Q(s,a) ← Q(s,a) + α [r + γ max_a′ Q(s′,a′) − Q(s,a)]`

For a terminal transition, the future-value term is zero. `α` is the update size, `γ` controls how much future rewards matter, and `ε` controls exploration. The bracketed expression is the temporal-difference error. A Q table is interpretable here because the state and action spaces are small. [Gymnasium's official FrozenLake Q-learning tutorial](https://gymnasium.farama.org/v1.3.0/tutorials/training_agents/frozenlake_q_learning/).

**RL agent versus project agents:** the on-screen RL agent is one learned decision maker that interacts with a simulated environment. The four development agents in `agents/` are specialized software-building roles. There is no multi-agent RL in this first lesson.

## Proposed scientific task and environment

| Item | Proposed starting contract |
| --- | --- |
| Board | Fixed 4×4 grid with start, goal, and one hazard; no user-edited map in v1 |
| State | Agent's cell index, 0–15; fully observed |
| Actions | Up, right, down, left; hitting a wall leaves the agent in place |
| Reward | Each move −0.05; goal +1; hazard −1; units are designed reward points, not physical units |
| Episode | Ends at goal or hazard; truncates after 40 actions; truncation is reported separately |
| Dynamics | Deterministic by default; optional slip probability for a later experiment |
| Training | Tabular Q-learning, seeded ε-greedy, Q initialized to zero; configurable episodes, α, γ, ε; fixed seed |
| Evaluation | Frozen learned Q table, greedy action selection, separate seeded episodes; report success rate, mean return, and mean steps conditional on success |

These rewards and map are **design choices**, not Gymnasium FrozenLake defaults. The map must have a reachable goal and a useful choice between a short risky route and a longer safe route, so a learner can reason about policy changes. The optional slip mode must define and display its transition probabilities; do not imply that an intended move always happens. Gymnasium's FrozenLake illustrates deterministic versus slippery movement, but its default reward is +1 at the goal and 0 elsewhere. [FrozenLake environment](https://gymnasium.farama.org/environments/toy_text/frozen_lake/).

The `reset`/`step` contract should follow Gymnasium semantics, including separate `terminated` and `truncated` flags. A time limit is not a goal or hazard. [Gymnasium environment API](https://gymnasium.farama.org/api/env/).

## Learning journey and appearance

The page should be a guided lesson with a prominent square board and a compact control column. On mobile, stack the board, controls, and results in that order. Use color plus symbols/text for start, goal, hazard, and current position, rather than color alone. Every chart needs labeled axes, tooltip or text summary, and an explanation of what a good result means.

```text
RL Gridworld Lab          What is the agent trying to learn?
┌──────────────────────┐  ┌─────────────────────────────┐
│ 4×4 board            │  │ 1. Play one episode         │
│ start • agent • goal │  │    arrows / reset           │
│ hazard • path trail  │  │ 2. Predict & train          │
│ policy arrows / heat │  │    ε, α, γ, episodes, seed   │
└──────────────────────┘  │    Step / Train / Reset Q   │
                          └─────────────────────────────┘
┌──────────────────────┐  ┌─────────────────────────────┐
│ One Q update         │  │ Learning curve              │
│ old Q → reward       │  │ success / return vs episode │
│ → future estimate    │  │ trained vs random baseline  │
│ → new Q              │  └─────────────────────────────┘
└──────────────────────┘
Evaluate policy: success rate, mean return, steps on successes; three short questions.
```

1. **Predict:** Play a few moves manually. Predict whether always moving toward the goal is safe, and why a future reward may justify a temporarily worse move.
2. **Observe:** Press **Step one training transition**. Highlight the current state/action, realized move, reward, old Q, target, temporal-difference error, and new Q. Distinguish an exploratory move from a greedy move.
3. **Experiment:** Train a bounded batch of episodes. Show policy arrows and visitation/Q heatmap changing alongside a learning curve. Compare ε=0 with ε>0 from a reset Q table using the same map and controlled seeds.
4. **Explain:** Evaluate the frozen policy on separate episodes. Ask whether one successful run proves the policy is reliable. Optionally turn on slip and rerun to see how uncertainty changes outcomes.

Suggested questions with feedback:

- **Why might ε=0 fail when all Q values start at zero?** It may never try a useful alternative under a fixed tie-breaking rule; exploration can discover it. The exact outcome depends on the tie rule and map.
- **What does γ change?** It changes the weight of future reward in the update; it does not change the environment's immediate reward.
- **Why evaluate with exploration off?** It measures the learned greedy policy; using ε>0 during evaluation mixes exploratory mistakes with policy quality. Report that training and evaluation use different action rules.
- **Does a higher training return in one seed prove the new settings are better?** No. Run several evaluation seeds and show variation.

Likely misconception: a green arrow or a single goal-reaching episode means the agent has learned an optimal policy. A policy diagram represents current estimates; success rate on repeated evaluation episodes provides stronger evidence. A deterministic shortest-path reference can check optimal behavior in the fixed map, and an exact dynamic-programming reference can check a small stochastic map if that extension is implemented.

## Scope choices

| Option | Value | Why now or later |
| --- | --- | --- |
| Tabular Q-learning gridworld | Every update and policy is inspectable | **First build** |
| SARSA comparison | Shows on-policy versus off-policy behavior, especially near hazards | Follow-up after Q-learning is correct |
| Deep Q-network / Atari | Introduces function approximation, replay, target networks, much longer training and less transparent behavior | Separate advanced module |
| Multi-agent RL | Adds joint state/action design and non-stationarity | Separate module, not needed to teach the core loop |

Gymnasium's Toy Text environments are intentionally small discrete tasks suitable for learning and debugging. [Toy Text overview](https://gymnasium.farama.org/main/environments/toy_text/). Cliff Walking is a good later comparison for risk-sensitive route behavior. [Cliff Walking environment](https://gymnasium.farama.org/environments/toy_text/cliff_walking/).

## How the development agents should interact when build is authorized

Use the existing sequential workflow, not a new orchestrator:

1. **Learning Planner** receives this note plus an approved brief; fixes audience, objectives, lesson sequence, feedback, and criterion IDs in `runs/<run-id>/learning-spec.md`.
2. **Architect** reads that spec and official RL/Gymnasium references; fixes transition/reward semantics, Q-learning/evaluation contracts, Bokeh interaction model, compute limits, and independent numerical oracles in `technical-plan.md`.
3. **Builder** creates `modules/reinforcement-learning/` with a pure Python environment/algorithm layer, session-local Bokeh UI, Flask-compatible metadata/HTML, dependencies, tests, and a build report. The existing `stem_platform` host should serve it.
4. **QA Reviewer** independently checks exact transition and Q updates, seeded reproducibility, terminal versus truncation behavior, learning/evaluation separation, live browser callbacks, two-session isolation, narrow viewport, and measured runtime. Defects go to Builder; design defects go to Architect.

The main conversation passes explicit paths, criteria, and handoff records between roles. A learner clicking **Train** does not call these development agents; it runs the module's RL training routine. No deployment is part of this proposal.

## Acceptance criteria for a later build

| ID | Criterion | Evidence to request |
| --- | --- |
| RL-01 | Transition and reward table matches the displayed rules, including walls, hazard, goal, and time limit | Independent unit/reference checks |
| RL-02 | A hand-calculated one-step Q update matches the engine, including terminal transitions | Numeric tests and step UI observation |
| RL-03 | Same configuration and seed reproduce training traces; changed settings mark previous results stale | Engine and UI checks |
| RL-04 | The learner can step, train, reset, inspect policy/Q values, and run a separate greedy evaluation | Real browser interaction evidence |
| RL-05 | Report success rate, mean return, and successful-episode length over declared episode counts and seeds; show a random baseline | Independent evaluation checks |
| RL-06 | Two browser sessions have isolated maps, Q tables, and progress | Two-session browser test |
| RL-07 | Lesson explains state, action, reward, episode, policy, exploration, Q update, and at least three questions with feedback | Instructional review |
| RL-08 | Startup, dependency versions, bounded work, and actual timing are recorded; no fixed training-time claim is invented | Clean setup and measured benchmark |

## Transfer from this repository's examples

| Requirement | Observed exemplar source | Adaptation and reason | Verification |
| --- | --- | --- | --- |
| Guided HTML plus live workspace | `corpus/sindy.md`; original SINDy `templates/index.html`, `main.py`, `flask_app.py` at catalog revision `d58a9a9b…` | Keep Flask/Bokeh split; use a shorter predict–observe–explain lesson rather than SINDy's four scientific tabs | Browser embedding, responsive review |
| Per-session learner state | Original SINDy `main.py`; current `modules/neural-equation-finder/ui.py` | Construct Q table, RNG, environment, and progress per Bokeh document | Two-session test |
| Clear controls and diagnostics | Original SINDy `tabs/train_tab.py`; current `modules/neural-equation-finder/ui.py` | Show RL-specific controls, policy arrows, Q update, returns and success instead of CSV/fit/residual controls | Interaction test and learner review |
| Pure scientific code and reproducibility | Current `modules/neural-equation-finder/engine.py` and `stem_platform/runtime.py` | Keep transitions/Q update independent of the UI; follow `build_document(doc)` and `module.json` contract | Numeric tests and launch smoke |

The SINDy original files were accessible for this review. The corpus card and original source establish code patterns; neither is evidence that the old UI is currently usable or performant. The currently generated neural module is implementation context, not an approved corpus exemplar.

## Decisions to confirm before the later build

The recommended defaults are: introductory undergraduate audience; 4×4 custom grid; English interface matching the current project; guided `lesson` presentation; tabular Q-learning only in v1; deterministic movement first, stochastic toggle second. Confirm or revise these in the build brief. The exact map, slip probabilities, training limits, and evaluation sample counts should be specified by the Planner/Architect and verified, rather than presented as measured facts now.
