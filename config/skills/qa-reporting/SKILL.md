---
name: qa-reporting
description: Evidence-based QA statuses, defect format and the readiness verdict.
owner: tester
---
# QA reporting

Each case result is `passed`, `failed`, `blocked` or `not_run`. `passed` requires evidence: the exact command and the relevant output, or a measured number with its tolerance. Opinion is not evidence.

**Defects.** One per root cause: `id`, `severity` (`blocker`, `major`, `minor`), `owner` (`builder` for structure, UI or performance; `researcher` for scientific or method errors; `project_manager` for ambiguous requirements), the trigger, `expected` and `actual`.

**Verdict.**
- `ready_for_review` only if every mandatory criterion has a passed case.
- `needs_repair` if any mandatory case failed and repair budget remains.
- `blocked` if a mandatory case cannot run.

A mandatory criterion that is unverified blocks readiness; do not downgrade it. After a repair, re-run the failing cases and close defects only on new evidence.

Never edit application code and never relax a criterion. When the capability is missing (for example no browser), say so and give reproducible manual steps.
