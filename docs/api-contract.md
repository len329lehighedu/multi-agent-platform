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
A finished or already-working run returns 400. The workflow ends with a project plan for approval and builds nothing.

`POST /runs` also accepts an optional `"provider"` (`claude`, `openai` or `replay`);
`GET /config` lists available providers and the default. The default is `replay` unless
`MODULE_FOUNDRY_PROVIDER` names another, so a paid provider is never used by accident.

## Projects

`POST /projects` `{"name": "..."}` creates a project (names are unique, case-insensitive, at most 80
characters). `GET /projects` lists projects with `run_count`, `versions` (completed builds), `files`
and their `runs`; `GET /projects/{id}` returns one. `POST /runs` accepts `project_id` (and an optional `provider`; the console no longer shows a provider picker, so the server default from `MODULE_FOUNDRY_PROVIDER` applies): the run is a
`module` run when the project has no module yet, otherwise a `feature` run on the existing module.
Runs without `project_id` keep their own private workspace. `DELETE /projects/{id}` permanently deletes the project, its module files and all its runs
(`{"deleted": true, "runs_removed": n}`); it returns 400 while any of its runs is working. Unknown
projects return 404 `project_not_found`.

## Approval, build and changes

`POST /runs/{run_id}/approve` (no body) starts the build after `plan.ready`; HTTP 202. It returns 400
when there is no plan, the plan was already approved, or the run is not waiting for review.

After `build.completed` or `build.failed`, `POST /runs/{run_id}/chat` is a change request for the
Builder (`revision.requested`). Before the plan is approved, chat returns 400.

`GET /runs/{run_id}/files` lists the module files; `GET /runs/{run_id}/files/{path}` returns one as
plain text. Events: `plan.approved`, `build.files_written`, `build.checks` (`passed`, `command`,
`output`, `round`), `build.completed`, `build.failed`, `revision.requested`, `revision.completed`,
`revision.failed`, `build.retried`. `build.checks` runs the module's unit tests and then loads
`main.py` as a Bokeh app, so API misuse that unit tests cannot see fails the build.

`POST /runs/{run_id}/retry` (no body, HTTP 202) runs the build again from the approved plan when it
stopped while the Builder was writing (a provider error such as an output limit). It returns 400 in
any other state. Event: `build.retried`.

## Live preview

The module is a Bokeh directory app whose entry file is `main.py`. The platform serves it with
`bokeh serve` as a subprocess on `127.0.0.1` (generated code never runs inside the platform process).

- `GET /projects/{id}/preview` returns `{"state", "url", "message", "log"}`; `state` is `running`,
  `stopped`, `failed` or `no_entry` (no `main.py`). `log` is the tail of the module log on failure.
- `POST /projects/{id}/preview` starts, or restarts so changed code is loaded, and waits until the
  module answers. Starts of one project are serialized.
- `DELETE /projects/{id}/preview` stops it. Deleting a project also stops its preview.

At most three previews run at once; the oldest is stopped first, and all stop when the platform exits.

## Spend

`GET /spend` returns `{"spend": {"total_usd", "budget_usd", "calls", "by_model", "by_project",
"module_budget_usd"}}`, or `{"spend": null}` when the Claude provider is not configured. Calls are
priced from real token usage and persisted in `var/spend.json`. A call is refused with a
`ProviderError` once the total reaches `CLAUDE_BUDGET_USD` (default 90) or one project reaches
`CLAUDE_MODULE_BUDGET_USD` (default 1.00).

## Events

`GET /runs/{run_id}/events/stream?after=0` is a server-sent event stream
(`event: run_event`, `id` = sequence; resumes from `Last-Event-ID`). It sends an
`event: end` and closes when the run is no longer `active` (paused, finished or
failed); reopen it from the last sequence after the next user message.

Workflow event types: `workflow.started`, `handoff.requested`, `agent.started`
(lists the skills loaded and the estimated prompt size), `agent.completed`,
`artifact.rejected`, `artifact.accepted`, `plan.ready`, `question.asked`,
`workflow.paused`, `question.answered`, `handoff.returned`, `workflow.completed`,
`agent.failed`.

`GET /runs/{run_id}/artifacts` returns the accepted artifacts by name
(`task_spec`, `research_brief`, `design_spec`, `test_plan`, `project_plan`).
See [process.md](process.md).

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
