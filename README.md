# STEM Module Multi-Agent Platform

A repository workflow for building interactive STEM/data science modules with agents, reusable skills, source-backed examples, Python, Bokeh, Flask and HTML.

The functional MVP has two runnable pilots, a reusable scaffold/host, shared Codex/Claude adapters, and recorded scientific/browser QA. Native Codex execution is verified through explicit role/skill assignment; live Claude execution and productivity gains are not established. Human acceptance remains pending.

## Run

```bash
cd /Users/ngoleminh/Documents/multi-agent-platform
./run.sh
```

Open http://127.0.0.1:8080. Ctrl+C closes both local endpoints. If an environment does not yet exist:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
./run.sh
```

The verified dependency target is CPython3.14.0/macOS arm64. This is a local development host, not a public deployment. Use `--port 8088 --bokeh-port 5018` with spaces after flag names if default ports are occupied.

## Review and test

- [Vietnamese walkthrough and testing guide](docs/testing-guide.vi.md) — understand the system, demo and verify it.
- [Advisor report in English](docs/advisor-report.md) — architecture, delivery, evidence and claim limits.
- [Current QA report](runs/mvp-completion-20261030/qa-report.md) and [evaluation report](evaluations/report.md).
- [Technical design](docs/design-proposal.md), [runtime setup](docs/runtime-decision.md), [usage](docs/usage.md).
- [Project instructions](AGENTS.md), canonical roles in agents/, canonical skills in .agents/skills/.

```bash
.venv/bin/python scripts/test_all.py
.venv/bin/python scripts/check_setup.py --runtime codex
.venv/bin/python scripts/sync_runtime.py --check
```

## Delivered components

| Component | Location |
| --- | --- |
| Projectile pilot | modules/projectile/ |
| Linear regression pilot | modules/linear-regression/ |
| Shared Flask/Bokeh host and HTML/CSS lesson shell | stem_platform/, web/ |
| Runnable starter generator | scripts/create_module.py, templates/module-scaffold/ |
| Four role specifications and eight skills | agents/, .agents/skills/ |
| Generated adapters | .codex/agents/, .claude/agents/, .claude/skills/ |
| Source-backed SINDy and provisional pilot examples | corpus/ |
| Run specs, handoffs, verification and screenshots | runs/mvp-completion-20261030/ |
| Numerical CSV extension and controlled claim-review fixtures | evaluations/artifacts/ |
| Matched-effort evaluation tool, no fabricated measurements | scripts/evaluate_productivity.py |

The project now lives independently under Documents and is not inside the SINDy checkout. The catalog points to the original SINDy source; that application's files were not modified. Historical smoke reports preserve their original paths as provenance. Edit canonical role/skill files then run `python3 scripts/sync_runtime.py`; generated adapters must stay synchronized.

Agents read examples in context and reason from the new brief; no model weights are trained. The two pilot case studies remain subject to human review. No neural-network equation-discovery module, CSV upload UI, public deployment, measured learning gain, or 30% productivity claim is included.
