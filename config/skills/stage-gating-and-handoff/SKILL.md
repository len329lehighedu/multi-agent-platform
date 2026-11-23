---
name: stage-gating-and-handoff
description: Gate criteria between stages, handoff summaries, and defect routing.
owner: project_manager
---
# Stage gating and handoff

You advance a stage only when its artifact is valid and passes the deterministic checks. You do not re-judge the science.

**Handoff summary** (at most 60 words): decisions made, open risks, and what the next agent must do. Never paste the artifact into it.

**Gates.**
- Task spec: every criterion has a verification method; at most one open question.
- Research brief: oracle defined; every `scientific_oracle` criterion is covered; unverified packages listed as risks.
- Design: every criterion mapped; every UI-exposed hyperparameter has a control; train, test and predict are separate files.
- Test plan: every criterion has a case; at least one edge case; an independent oracle check.
- Project plan: every criterion has a success entry with a measurable how_measured; algorithm name matches the research brief.

No build starts without an accepted project plan and the user's approval.

**Routing defects** (later phases): science wrong or oracle failing goes to the Researcher; structure, UI or performance goes to the Builder; an ambiguous requirement goes to the user through one question. Respect `budget.max_repair_cycles`; when it is exhausted, stop with status `needs_review` and say what is unresolved.
