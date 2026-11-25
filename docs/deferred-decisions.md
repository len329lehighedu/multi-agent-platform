# Deferred decisions

## Authentication and authorization (revisit at deploy time)

Not implemented. The console and `/api/v1` are open on localhost only.

Planned for deployment:

- Database-backed users and run store (replace `JsonRunStore`; the store boundary already exists).
- Google OAuth sign-in.
- Two roles: **developers** (console, agent invocation) and **viewers** (run released modules only).
- Do not expose this server beyond localhost until this is in place.

## Multi-developer collaboration on one project

Direction under discussion, not built: each run works on its own git branch/worktree,
changes arrive as a reviewable change set, merging into main needs human approval,
and runs declare the paths they will touch to avoid conflicts. Modules are released
as versioned tags that viewers run.

Refined proposal (Nov 2026), phased:

1. Now: one run = one isolated workspace with git snapshots (already true).
2. Module identity separate from runs. A module is one git repo; a new developer run forks a
   branch `dev/<user>/<run>` from main in its own worktree. Agents never write to main.
3. Proposal flow. A finished branch is "proposed": the console shows diff, test results and a
   live preview of the branch. Main only advances through a merge that passes tests and an
   owner's approval. Viewers run released tags only.
4. Conflicts. The SINDy layout (engine, one file per tab, one fragment per page) keeps most
   developers in different files. Every revision stores its request text, diff and commit, so
   when two branches touch the same file a merge agent receives both intents (not only the
   diffs), resolves, re-runs tests, and a human approves. Rebase on main before each build.
5. Advisory soft locks ("Alice is editing the Train tab") shown in the console; no hard locks.
6. Per-developer cost budgets, since each developer's agents bill separately.

Open questions for the professor: who approves merges, whether a module has a single owner,
and how many developers realistically work on one module at once (small numbers mean plain
git is enough; no real-time co-editing).

Implemented first step (Nov 2026): projects, one shared module workspace per project, feature runs
with a full plan loop, one writer per project at a time. Not yet: per-developer branches, merge
approval, and detection that a feature plan is stale because another run changed the module after
the plan was made (today the build simply runs on the current files).

## Live module preview

Implemented (Nov 2026): `PreviewManager` serves a project's module with `bokeh serve` as a subprocess
on 127.0.0.1 and the console embeds it in an iframe (Module tab). See api-contract.md, Live preview.
Still open: a reverse proxy mapping `/preview/<project>/` to the port when deployed, idle shutdown,
per-module environments (today one shared interpreter), and a real sandbox for generated code (it
currently runs with the platform user's permissions, so keep it on localhost until that exists).

## Editing module files in the console

Implemented (Nov 2026; see api-contract.md): an editor in the Files tab that saves through `PUT /runs/{id}/files/{path}`.
The route reuses the Builder's safeguards (safe relative path, allowed suffix, size limit) and takes the
project's single-writer claim, so it cannot overlap an agent run. A save writes the file, makes a git
snapshot (author is the developer, so the change is attributable and revertable), runs the same
checks as a build (unit tests and the Bokeh app load) and restarts the preview on success. A failed
check keeps the file but shows the output and offers "revert to the previous snapshot". Agents see the
edit automatically because their context is always read from disk. Open questions: whether a human
edit that fails checks may stay saved, and a diff view before saving.

## Agent execution

Builder and Tester run for real: files are written to the project workspace, tests and the Bokeh
app load run in a subprocess, and the preview serves the result. Open: OS-level sandboxing,
oracle and headless-browser checks so the Tester can show evidence for more than unit tests.

## Developer console layout after an MVP exists

Direction from the product owner; not built. Today the console is a workflow viewer
(chat, stage tracker, agent graph). Agent activity already lives inside the chat feed.

Target layout once a module has been built and compiled:

- **Center:** the live module preview, running in an isolated sandbox and embedded in
  an iframe with the `sandbox` attribute on its own origin (no shared cookies). Reload
  and desktop/tablet width toggles. Bokeh server starts on demand and stops when idle.
- **Left:** the chat, collapsible and expandable. Agent activity stays inline.
- **Build status strip:** evidence-based chips (compiled, tests passed of total, Flask and
  Bokeh up, WebSocket ok, repair cycles used). The preview unlocks only after the health
  check passes; on failure show the log tail instead of a blank frame.
- **Acceptance criteria board:** one row per criterion from the project plan with status
  `passed`, `failed`, `blocked` or `not_run`, the owner of any defect, and a link to the
  evidence. A criterion without evidence is never shown as passed.
- **Secondary tabs:** Files (tree and diff), Tests, Logs, Timeline, Cost (token usage per
  agent, already recorded in events).
- **Actions:** report an issue from the preview (selection, note and screenshot become a
  defect routed to the Builder or Researcher), send a failed criterion to the Builder,
  and one primary action, approve and release, enabled only when every mandatory
  criterion has passed.
- **Versions:** each run is a branch; choose between versions (v1, repair 1, ...) and
  compare diffs. Release creates a versioned module for viewers.
- **Mobile:** regions become tabs.

Open questions for the product owner: does release publish to the parent site
automatically or after a manual review; should the teacher edit the HTML description
fragments in the console (a Description tab); who may approve and release.

Implementation order: (1) status strip and iframe preview with logs, (2) criteria board,
(3) files and diff, (4) report an issue from the preview.
