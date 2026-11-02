# Data Science Multi-Agent Platform

The home screen now lists two interactive modules:

- **Neural Equation Finder**: upload a numeric CSV, train a neural regressor, and inspect held-out predictions plus a polynomial surrogate.
- **RL Gridworld Lab**: step through deterministic actions and rewards, train a seeded tabular Q-learning agent, and inspect its Q updates, policy, and repeated evaluation outcomes.

The neural network is a numerical predictor. The displayed equation is a separately fitted polynomial approximation of the network, with its own fidelity score. It is not automatically a recovered governing law.

## Run

Verified locally with CPython 3.14.0 on macOS arm64.

```bash
cd "/Users/ngoleminh/Documents/multi-agent-platform"
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
./run.sh
```

Open `http://127.0.0.1:8080` for the module gallery. Stop it with `Ctrl+C`.

## CSV contract

- UTF-8 CSV with a header, 20-5,000 rows, and 2-100 columns.
- Choose one target and one-to-four numeric input columns.
- Empty, NaN, or unparseable selected cells are dropped and counted; explicit infinity is rejected.
- Maximum decoded upload size is 5 MB.
- The built-in quadratic sample works without an upload.

The compact controls expose architecture, activation, solver, L2 regularization, learning rate where applicable, maximum iterations, test fraction, polynomial degree, and seed. Training runs in a bounded subprocess with a 120-second operational timeout. The dashboard reports measured duration rather than promising a fixed runtime.

## Verify

```bash
.venv/bin/python scripts/test_all.py
```

For the real browser suite, install the browser test dependencies, start the server, and run:

```bash
.venv/bin/python -m pip install -r requirements-browser.lock.txt
.venv/bin/python scripts/test_browser.py \
  --base-url http://127.0.0.1:8080 \
  --browser-executable "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
```

Run records for this build are in `runs/neural-equation-20261030-01/`. The previous projectile and linear-regression source modules were removed at the user's request; their historical evidence remains under `runs/mvp-completion-20261030/` as an audit record.

## Multi-agent workflow

Canonical roles are in `agents/`; canonical skills are in `.agents/skills/`. `AGENTS.md` is shared by Codex and Claude Code, while generated runtime adapters remain under `.codex/` and `.claude/`. This run used native Codex subagents with explicit role and skill files for Planner, Architect, Builder, and QA.

The project uses existing modules as in-context examples rather than model-weight training. SINDy remains the source-backed corpus example. Generated modules require human review before promotion into the approved corpus.
