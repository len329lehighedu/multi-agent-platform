# RL Gridworld Lab

A compact lesson about the reinforcement-learning loop and tabular Q-learning. The fixed 4 × 4 world has a start, goal, and hazard. Learners can step one transition, train 1–500 episodes, inspect the changed Q value and policy, and compare training outcomes with a frozen 100-episode greedy evaluation.

From the platform root, using the locked environment:

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
.venv/bin/python scripts/serve.py --module reinforcement-learning
```

Open `http://127.0.0.1:8080/modules/reinforcement-learning/`. To see the home gallery with every installed module, omit `--module`:

```bash
./run.sh
```

The browser connects to both Flask on port 8080 and Bokeh on port 5006. Stop the host with `Ctrl+C`.

## Scientific rules

- States are the 16 grid cells; actions are up, right, down, and left.
- Movement is deterministic. A wall action leaves the agent in its cell.
- Ordinary moves reward −0.05, reaching the goal +1, and entering the hazard −1.
- Goal and hazard terminate an episode. Other episodes truncate after 40 actions.
- Q starts at zero and uses seeded epsilon-greedy tabular Q-learning.
- Terminal transitions have zero future value. A truncation still bootstraps, because the time limit is separate from environment termination.
- Evaluation uses a fixed greedy tie order, freezes Q, and turns exploration off.

This small experiment reports observed outcomes. It does not establish that one learned policy is optimal or generalizes to another environment.

## Verify

```bash
.venv/bin/python -m unittest discover -s modules/reinforcement-learning/tests -p 'test_*.py' -v
.venv/bin/python modules/reinforcement-learning/tests/benchmark.py
```

The engine uses NumPy. The UI and shared host use Bokeh and Flask from `requirements.lock.txt`; no Gymnasium or worker process is required.
