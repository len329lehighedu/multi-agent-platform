# API-first architecture

## Design principles

1. **Domain first.** Runs, messages, events, stages, and transitions do not depend on Flask, a database engine, or a model vendor.
2. **Explicit orchestration.** Agent handoffs and repair loops are state transitions, not hidden prompt conventions.
3. **Provider portability.** A model provider implements one internal request/response interface.
4. **Workspace isolation.** Each run receives a bounded filesystem workspace; agents do not write into product source.
5. **Human participation.** Waiting for a user is a persisted state with an explicit question and resume path.
6. **Evidence over claims.** Tool calls, tests, browser observations, failures, and measurements are structured events.

## Components

### Web client

Renders chat, agent identity, run stages, questions, decisions, artifacts, preview, and QA status. It owns no API keys and no orchestration rules.

### HTTP API

Authenticates requests, validates payloads, exposes runs/messages/events/artifacts, and streams updates. The current Flask adapter is intentionally thin.

### Orchestrator

Owns the run state machine, context assembly, routing, retry/repair budgets, and provider/tool dispatch. It is the only component allowed to move a run between stages.

### Agent catalog

Loads versioned role prompts and skill references from `config/`. A run records the exact definitions and model configuration it used.

### Model provider

Translates the internal request into a vendor API call and normalizes text, structured output, tool calls, usage, latency, and provider errors. Provider adapters never decide workflow transitions.

### Run store

Persists run snapshots and append-only events. The foundation uses atomic JSON files; the interface is designed for a database adapter later.

### Workspace manager

Creates one directory per run for generated source, artifacts, logs, tests, and preview configuration. Container or worktree isolation can replace the local adapter without changing orchestration.

## Run lifecycle

```text
intake → planning → architecture → building → qa → review
                         ↑             │
                         └── repair ←───┘
```

Any active stage can become `awaiting_user`. Terminal outcomes are `ready_for_review`, `needs_review`, `failed`, or `cancelled`.

## Next implementation slices

1. Foundation domain/store/API — implemented in this restructure.
2. Provider adapter and encrypted configuration.
3. Background job runner plus server-sent events.
4. Tool permission model and workspace command runner.
5. Planner/Architect conversational checkpoints.
6. Builder and QA execution with preview lifecycle.
7. Web chat and run timeline.
8. Authentication, quotas, and deployment hardening.
