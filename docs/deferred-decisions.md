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

## Agent execution

Builder and QA currently produce plans only. Tools, workspace command runner,
tests and preview are future slices (see architecture.md).
