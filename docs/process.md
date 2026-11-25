# Platform process

No agent builds anything until a project plan exists and the user has approved it.
This document describes the planning phase that is implemented today and the
gate that the build phase will require.

## Roles

| Role | Owns | Artifact |
| --- | --- | --- |
| Project Manager | Scoping, routing, the final plan | `task_spec`, then `project_plan` |
| Researcher | Model, inputs, hyperparameters, algorithm, packages, scientific oracle | `research_brief` |
| Builder | File structure, train/test/predict separation, performance, plots, controls | `design_spec` |
| Tester | Test cases, edge cases, oracle checks (later: the QA report) | `test_plan` (later `qa_report`) |

Specialists never talk to each other. The Project Manager (orchestrator) passes
each one only the artifacts it needs, never the chat history.

## Planning phase

```text
user request
  → PM: task_spec      (at most one question to the user)
  → Researcher: research_brief
  → Builder: design_spec
  → Tester: test_plan
  → PM: project_plan   (the consolidated plan for the user)
  → user approves      (build phase starts only after this; not implemented yet)
```

Every artifact must pass two deterministic checks before the next step begins:

1. **Schema** (`config/schemas/*.json`): required fields, types, enums.
2. **Consistency** (`src/module_platform/artifacts.py`): every acceptance criterion
   is mapped by the design, covered by a test case and listed in the plan's success
   definition; every UI-exposed hyperparameter has a control; tabs have their own
   files; at most 5 plots per tab; an edge case and an oracle check exist; the plan
   names the Researcher's algorithm exactly.

A failure triggers one targeted repair request that lists exactly what failed. A
second failure fails the run. All of it is recorded as events.

## The project plan the user sees

Rendered by code from the `project_plan` artifact (no extra model tokens):
what the module will do, the algorithm and why, how success is defined (per
acceptance criterion, with the measuring test and tolerance), what the user can do
with the MVP, what is out of scope, how it will be built and verified, and the
risks. It always states that nothing has been built or run.

## Approval, build and changes

Nothing is built until the user approves the plan.

1. **Approve.** `POST /runs/{id}/approve` records `plan.approved` and starts the build. Chat is
   closed between `plan.ready` and approval.
2. **Build.** The Builder returns whole files as a `file_set` artifact. Code checks paths (relative,
   no `..`, allowed file types, size) and that every file in the design exists, then writes them to
   `<workspace>/module/` and snapshots them with git.
3. **Test.** The orchestrator runs the module's own `tests/` as a subprocess. No model tokens.
   A failure sends the real output and only the relevant files back to the Builder: at most two
   repair rounds. If it still fails the run ends in `needs_review` and never reports success.
4. **Verify.** The Tester reads the real test output and reports one result per planned case
   (`qa_report`). Cases the automated run did not exercise must be `not_run` with a reason.
   Code rejects a report with missing cases or a `ready_for_review` verdict next to failures.
5. **Summary.** Code renders the result for the user (per-case evidence, defects, what was not run).
6. **Changes.** After a build the chat accepts change requests (`build.completed`/`build.failed`
   open it). The Builder gets the current files and returns only the files it changes. Tests re-run
   with the same repair budget. If they cannot pass, the module is restored from a backup and
   `revision.failed` is recorded, so a bad edit never leaves a broken module.

Not yet: browser and screenshot checks, running the Flask/Bokeh app, plan feedback before approval,
undo of an applied revision, and a cheaper triage step that selects files for large modules.

## Bokeh-only modules (HTML disabled for now)

Generated modules are Bokeh apps only. HTML description pages, the Flask shell that served them and
`templates/` are disabled: the Builder's design cannot use the `flask` or `template` roles, code
rejects designs that list `flask_app.py`, `templates/` or any `.html` file, and a file set cannot
write `.html` files. Descriptions live inside each tab as a short Bokeh `Div`. Re-enable by adding the
roles back to `config/schemas/design_spec.json`, `.html` to `ALLOWED_SUFFIXES` in `artifacts.py`,
and restoring the removed lines in the Builder skills.

## Projects and features

A project is a named container for one module. Its runs share one module workspace
(`<data>/workspaces/projects/<project_id>/module`); each run keeps its own artifacts and chat.

- The first run in a project builds the module (`kind: module`).
- Every later feature is a new run (`kind: feature`) and goes through the same loop as the first
  build: scope, research, design, tests, plan, user approval, build, verify. Planning agents are told
  the module already exists, receive its file list and the goals of earlier builds, and design only
  the addition. Code skips the "engine/ must exist" rule for features but still requires tests.
- The Builder receives the existing files (all of them, or only the touched, engine and test files
  when the module is large), and the whole test suite runs, so a feature cannot silently break
  earlier work. If it cannot pass after repairs, the module is restored and the run ends with
  `build.failed` (`rolled_back: true`).
- Small edits after a build (layout, labels, colours) remain "changes" on the same run, with no new
  plan. The composer offers an explicit choice: change this module, or new feature (plans first).
- Only one run per project may write to the module at a time. Agents only receive their project's
  files and artifacts.

## Skills and cost

Skills live in `config/skills/<name>/SKILL.md`, are owned by one role, and are
loaded by the orchestrator, not requested by the agent. Reference material loads
only when a task tag requires it. Run
`PYTHONPATH=src .venv/bin/python -m module_platform.skills` to see prompt sizes.
Agents have a model tier (`fast` or `strong`) in `config/agents/manifest.json`. With Claude, `fast`
is `CLAUDE_MODEL_FAST` (default Haiku) and `strong` is `CLAUDE_MODEL` (Sonnet); today the Project
Manager is `strong` and the Researcher, Builder and Tester are `fast`. With OpenAI use
`OPENAI_MODEL_FAST` and `OPENAI_MODEL_STRONG`.

Every Claude call is priced from its real usage and added to `var/spend.json`; the total budget and
the per-module budget stop further calls with a readable error (see api-contract.md, Spend).
Measured on the first live runs: a small module with a cross-validation feature cost about $0.15.

## Generated module contract

- The entry file is `main.py`, a Bokeh directory app; the platform previews it with `bokeh serve`.
- Tests use `unittest`. After they pass, the platform loads `main.py` as a Bokeh app; a callback
  with the wrong signature or a removed Bokeh class fails the build and goes to the repair loop.
- The Builder must not loosen a test to make it pass. A criterion that cannot be reached is
  reported in `notes` so a human decides.
- A build that stops while the Builder is writing can be retried from the approved plan
  (`POST /runs/{id}/retry`) without planning again. A build that wrote files but failed its tests
  is kept, and the developer sends a change request.
