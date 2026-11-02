# Module brief: RL Gridworld Lab

## Request and audience

Build a simple reinforcement-learning module named `reinforcement-learning` so the user can learn by interacting with it. Add a home screen that lists all platform modules. Use the existing platform template and shared Flask/Bokeh host.

Proposed audience: introductory undergraduate learners who know averages and basic probability but have not studied reinforcement learning. Keep the lesson compact and avoid advanced or decorative features.

## Scientific contract

The learner should understand the loop state → action → reward → next state and see how tabular Q-learning changes an action value. Use a fixed deterministic 4×4 grid with start, goal, and hazard. Actions are up/right/down/left. Hitting a wall leaves the agent in place. Each ordinary move rewards −0.05, goal rewards +1, and hazard rewards −1. An episode terminates at goal or hazard and truncates after 40 steps.

Use seeded epsilon-greedy tabular Q-learning:

`Q(s,a) ← Q(s,a) + α [r + γ max Q(s′,a′) − Q(s,a)]`

The future term is zero for terminal transitions. Q values initialize to zero. Evaluation freezes the learned table and uses a greedy policy.

## Learner experience

Use the existing lesson page shell. Provide a visible 4×4 board, policy arrows/Q values, a one-transition explanation, and a small learning curve. Controls: step one training transition, train a bounded batch, reset Q, alpha, gamma, epsilon, episode count, and seed. Show success rate or training outcomes without claiming optimality from one episode. Include three questions with answers in module metadata.

The platform root must show a module gallery containing both Neural Equation Finder and RL Gridworld Lab. The current index template may be reused and lightly improved. Do not create a custom scheduling or agent UI.

## Execution constraints

- Work in `modules/reinforcement-learning/` and `runs/rl-gridworld-20261101-01/`.
- CPU only; standard library plus existing NumPy/Bokeh/Flask environment.
- At most 500 training episodes per click and 40 steps per episode.
- Keep callbacks synchronous only because the bounded tabular workload must be measured as fast; add no worker process unless measurement shows it is needed.
- Deterministic map only in v1. No Gymnasium dependency, SARSA, neural networks, replay buffers, animation framework, editable maps, or multi-agent RL.
- One Builder/QA repair cycle after the initial build.
- Preserve the existing Neural Equation Finder module and unrelated user changes.

## Acceptance criteria

| ID | Required behavior | Verification | Mandatory | Role |
| --- | --- | --- | --- | --- |
| RL-01 | Grid transitions, rewards, termination, truncation, and wall behavior match the brief | Independent engine tests | Yes | QA |
| RL-02 | A hand-calculated nonterminal and terminal Q update matches the engine | Numeric tests | Yes | QA |
| RL-03 | Same seed/config reproduces a training trace and reset clears Q/history | Engine/UI tests | Yes | Builder/QA |
| RL-04 | Board, policy/Q display, step, train, and reset interactions work in a live browser | Browser interaction | Yes | QA |
| RL-05 | Lesson explains core concepts and supplies at least three questions with feedback | Metadata/content review | Yes | Planner/QA |
| RL-06 | Root home screen lists and links both installed modules | Flask/browser check | Yes | Builder/QA |
| RL-07 | Two Bokeh sessions own separate Q tables and interaction state | Document/session test | Yes | QA |
| RL-08 | Setup commands, dependency versions, bounded workload, and measured runtime are recorded | Test log/benchmark | Yes | Builder/QA |

## Assumptions and unresolved issues

English learner-facing text matches the existing platform. The fixed map and exact UI layout can be chosen by Planner/Architect as long as it remains readable and gives the learner a meaningful safe-versus-risky choice. Human review is still required for instructional quality.
