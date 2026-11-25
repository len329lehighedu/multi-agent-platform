---
name: intake-and-scoping
description: Turn a user request into a task_spec with testable acceptance criteria; decide when a question is allowed.
owner: project_manager
---
# Intake and scoping

Produce a `task_spec` that the Researcher, Builder and Tester can work from without reading the chat.

**Stack is fixed:** Bokeh only (plots, inputs and short in-app descriptions). HTML description pages and Flask are disabled for now. Default capabilities are `train`, `test`, `predict`. Do not reopen the stack.

**Objectives** are observable ("explain why a fitted equation does or does not generalize"), not "understand X". One to three objectives.

**Tags** drive which reference material later agents receive. Choose only the ones that truly apply.

**Acceptance criteria** (3 to 8). Each is atomic, observable and has an ID (`AC1`...) and one verification method: `unit_test`, `ui_contract_test`, `browser_check`, `scientific_oracle`, `manual`. Always include criteria for: (a) a scientific correctness check using `scientific_oracle`; (b) invalid input shows a visible error and never crashes; (c) all tabs build and every control callback runs; (d) description pages match the controls. Never write a criterion you cannot map to a verification method.

**Questions.** Ask at most ONE question, and only if the answer changes the data source, the required output, or an acceptance criterion. Otherwise record an assumption in `assumptions` and continue. Never ask about methods, packages or layout.

**Budget.** Set `constraints.max_train_seconds` from the audience (interactive learners: 20 or less) and `budget.max_repair_cycles` to 2 unless the user said otherwise.

Do not choose the algorithm. If the user named one, record it as a constraint in `constraints.notes`.

Never change a number the user stated (a threshold, a range, a default) on your own. If it looks unreachable or inconsistent, that is the one question to ask, with the reason and a proposed value; do not move it into assumptions.
