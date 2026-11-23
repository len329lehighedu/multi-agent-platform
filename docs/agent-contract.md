# Agent runtime contract

The product presents one conversation, but specialist work is explicit and
traceable. The orchestrator supplies each invocation with:

- run ID, stage, goal, and relevant user decisions;
- the specialist's versioned prompt and selected skills;
- only the artifacts and conversation slices required for the task;
- a bounded tool grant and workspace path;
- an expected structured artifact schema.

Every response contains a user-facing message and optional structured artifacts,
questions, decisions, tool calls, usage, and evidence. The provider adapter only
normalizes model output; the orchestrator validates it and decides the next state.

Agents never hand off directly to another agent. They return control to the
orchestrator, which persists the result and makes the transition visible to the
user. This keeps retries, human checkpoints, repair budgets, and audit history out
of hidden prompt-to-prompt conversations.

## Context policy

Do not resend an entire run by default. Assemble context from the approved brief,
latest relevant artifacts, explicit decisions, unresolved questions, and a short
conversation window. Store provider usage per invocation so context size and cost
can be measured before retrieval or caching is added.

## Evidence policy

Model text is not proof that a command, test, browser interaction, scientific
check, or benchmark ran. Those claims require a corresponding tool result event.
Failures and unavailable capabilities are first-class outcomes.
