# HTTP API contract

Prefix: `/api/v1`

The foundation is synchronous and local. Long-running agent work will later return jobs and stream events without changing the run/message resource shapes.

## Health

`GET /health`

## Agent catalog

`GET /agents` returns public agent IDs, display names, and skill IDs. System
prompts are intentionally not part of the browser-facing response.

## Runs

`POST /runs`

```json
{"goal":"Build an interactive heat-transfer module","created_by":"minh"}
```

`GET /runs` lists runs. `GET /runs/{run_id}` returns one complete snapshot.

## Conversation

`POST /runs/{run_id}/messages`

```json
{"content":"Use SI units and target sophomore learners","target_agent":"learning_planner"}
```

The target is optional. The orchestrator remains responsible for final routing.

`POST /runs/{run_id}/chat` accepts `{"content":"..."}` and returns HTTP 202.
The first call starts the planning workflow; if the run is `awaiting_user`, the
content is the answer and the workflow resumes. Work runs in a background thread.
A finished or already-working run returns 400. The workflow produces a plan only.

`POST /runs` also accepts an optional `"provider"` (`openai` or `replay`);
`GET /config` lists available providers and the default.

## Events

`GET /runs/{run_id}/events/stream?after=0` is a server-sent event stream
(`event: run_event`, `id` = sequence; resumes from `Last-Event-ID`). It sends an
`event: end` and closes when the run is no longer `active` (paused, finished or
failed); reopen it from the last sequence after the next user message.

Workflow event types: `workflow.started`, `handoff.requested`, `agent.started`,
`agent.completed`, `question.asked`, `workflow.paused`, `question.answered`,
`handoff.returned`, `workflow.completed`, `agent.failed`.

`GET /runs/{run_id}/events?after=0`

Events have monotonically increasing sequence numbers. Future SSE delivery will use the same sequence for resume.

## Workflow transition

`POST /runs/{run_id}/transitions`

```json
{"stage":"planning","reason":"Intake is complete"}
```

This endpoint is an internal/development surface until authorization rules are implemented.

## Error shape

```json
{"error":{"code":"invalid_request","message":"goal is required"}}
```
