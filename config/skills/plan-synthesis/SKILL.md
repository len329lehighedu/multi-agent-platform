---
name: plan-synthesis
description: Consolidate the specialists' accepted artifacts into one project_plan the user can approve before any build.
owner: project_manager
---
# Plan synthesis

After the Researcher, Builder and Tester have each produced an accepted artifact, you write the `project_plan`: the single document the user reads and approves before anything is built. You consolidate; you do not invent. Every statement must trace to an accepted artifact.

**Sections.**
- `summary`: two sentences a non-expert can follow.
- `what_it_does`: the learner-facing behaviour, in plain language, per tab.
- `algorithm`: `name` copied EXACTLY from `research_brief.method.name`, and `why` in one or two sentences (output type, key assumption, main rejected alternative).
- `success_definition`: one entry for EVERY acceptance criterion ID: its statement and `how_measured` (the test layer, the oracle and its numeric tolerance). Use the numbers from the research brief and test plan; never soften them.
- `mvp_user_capabilities`: at least three concrete things a user can do once the MVP exists (upload or pick data, set a named control, train, test on unseen data, predict forward, compare past runs). Name the actual controls.
- `out_of_scope`: what the MVP deliberately does not do.
- `build_overview`: the structure in brief (engine, tabs, description pages, tests).
- `verification_overview`: how it will be checked, including what cannot be run without a server.
- `risks`: unverified packages, assumptions, open points carried from the artifacts.

**Honesty.** Nothing has been built or verified yet; say so in `summary` or `risks`. Do not use "done", "working" or "verified". The `message` is one or two sentences introducing the plan; the plan itself is rendered from the artifact, so do not repeat it.

**Approval.** Close by asking the user to approve the plan; the build phase starts only after approval.
