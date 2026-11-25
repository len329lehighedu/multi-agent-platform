# Module Foundry

API-first multi-agent development environment for building reviewable STEM learning modules.

This repository is being rebuilt as a product that next year's cohort can use through a chat interface. A user creates a run, talks with specialist agents, reviews decisions, watches implementation and QA progress, and receives a module workspace plus traceable evidence.

The current foundation provides:

- persistent runs, messages, stages, and event history;
- an HTTP API for a future web chat client;
- a framework-neutral model-provider interface;
- an agent catalog loaded from versioned repository configuration;
- isolated per-run workspace directories;
- explicit, validated workflow transitions;

The developer console at `/` shows the orchestrator handing work to the Planner, Architect, Builder and QA agents, with a live graph, stage tracker and event timeline. The Project Manager, Researcher, Builder and Tester each return a validated artifact, and the Project Manager ends with one consolidated plan: what the module does, the algorithm, how success is defined, and what you can do with the MVP. This slice produces a plan only; no agent writes code or runs tools yet. The Project Manager may pause the run to ask you one question. See [docs/process.md](docs/process.md).

## Architecture

```text
Web chat / cohort UI
        │ HTTP + event stream
        ▼
Module Foundry API
        │
        ├── run store
        ├── orchestrator state machine
        ├── agent catalog
        ├── model-provider adapter
        └── workspace manager
                │
                ▼
        isolated module workspace
```

See [architecture.md](docs/architecture.md), [product-vision.md](docs/product-vision.md),
[agent-contract.md](docs/agent-contract.md), and [api-contract.md](docs/api-contract.md).

## Run locally

The first API adapter uses the already verified Flask dependency. The domain and orchestration packages do not depend on Flask.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
PYTHONPATH=src .venv/bin/python -m module_platform
```

The API listens on `http://127.0.0.1:8080` by default. Open it to use the console.

Providers (the server picks one with `MODULE_FOUNDRY_PROVIDER`; the default is `replay`):

- `claude` — live calls; needs `CLAUDE_API_KEY` and `CLAUDE_MODEL` (the strong model, for example
  `claude-sonnet-5-5`) in the ignored `.env`. Optional: `CLAUDE_MODEL_FAST` (default
  `claude-haiku-5-5`), `CLAUDE_MODEL_STRONG`, `CLAUDE_BUDGET_USD` (total stop, default 90),
  `CLAUDE_MODULE_BUDGET_USD` (per project, default 1.00), `CLAUDE_THINKING_FAST=on` (thinking is
  off for fast models), `CLAUDE_EFFORT_FAST` / `CLAUDE_EFFORT_STRONG`. Spend is at `/api/v1/spend`.
- `openai` — live calls; needs `OPENAI_API_KEY` (and optional `OPENAI_MODEL`) in the ignored `.env`.
- `replay` — a recorded run from `config/replay/demo.json`; works offline, useful as a demo fallback. Set `REPLAY_DELAY` (seconds, default 1.2) to pace it.

Create a run:

```bash
curl -X POST http://127.0.0.1:8080/api/v1/runs \
  -H 'Content-Type: application/json' \
  -d '{"goal":"Build an interactive heat-transfer module"}'
```

## Verify

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

## Repository map

```text
apps/web/                 developer console (workflow viewer)
config/agents/            role prompts + manifest (skills, model tier)
config/skills/            16 role-owned skills, loaded by the orchestrator
config/schemas/           artifact schemas (task_spec, research_brief, ...)
config/replay/            recorded agent responses for offline demos
docs/                     product, architecture, and API decisions
src/module_platform/      API-independent orchestration core + Flask adapter
tests/                    foundation acceptance tests
var/                      local run state and workspaces (ignored)
```

Deferred work is tracked in [docs/deferred-decisions.md](docs/deferred-decisions.md).

