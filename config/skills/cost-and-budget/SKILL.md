---
name: cost-and-budget
description: Keep model spend low: minimal context, one question, bounded repairs, deterministic checks first.
owner: project_manager
---
# Cost and budget

Tokens are a budget you are accountable for.

- Pass each specialist only the artifacts it needs, never the chat history. Summaries replace full artifacts wherever a summary is enough.
- Do not restate earlier work in new messages. Messages to the user are at most 120 words.
- Ask the user at most one question per run, before the Researcher starts. Questions after that cost the most.
- Schema and consistency failures are fixed by one targeted repair request that lists exactly what failed. A second failure ends the run with a clear error.
- Prefer deterministic code to model judgment: validation, coverage checks and counting are code.
- Do not ask an agent to reconsider an accepted artifact. Change it only through a defect with an owner.
- Record usage per agent from the provider response. If a stage exceeds its expected size, say so in the summary instead of continuing silently.
