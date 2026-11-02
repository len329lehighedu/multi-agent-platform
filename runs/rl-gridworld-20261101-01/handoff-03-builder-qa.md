# Stage handoff

- Run/task ID: `rl-gridworld-20261101-01` / builder
- Producing role and execution: native `stem-builder` subagent `/root/rl_builder`
- Receiving role: `stem-qa-reviewer`
- Status: ready
- Inputs: accepted brief, learning spec and technical plan
- Outputs: `modules/reinforcement-learning/`, `runs/rl-gridworld-20261101-01/build-report.md`, gallery wording and root README update
- Criteria: RL-01 through RL-08
- Checks executed: RL tests 6/6; full regression platform 15/15, neural 13/13, RL 6/6; setup 0 errors; compileall and diff check pass; five-repeat benchmarks recorded
- Measured median: 20,000 Q updates 0.087386 s; 500 training episodes 0.051949 s; Bokeh callback plus evaluation/publication 0.053614 s
- Checks not run: live browser/WebSocket, narrow viewport and two real browser sessions
- Next action: QA independently checks science and performs mandatory browser checks; defects return to Builder within one repair cycle
