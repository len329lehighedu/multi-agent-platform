---
name: stem-build-module
description: Orchestrates the project's specialist agents to design, build, and verify a STEM learning module from a brief or natural-language request using the module corpus.
---

# Build a STEM module

Work from the platform directory. Read `AGENTS.md`, `docs/usage.md`, and the user request supplied with this skill. Use `templates/module-brief.md` to normalize a brief without overriding the user's choices. For an existing run, inspect its artifacts and resume rather than starting over.

Create a unique `runs/<run-id>/`, save `brief.md`, and initialize `run.json` from `templates/run-manifest.json`. Set actual timestamps, requested module directory, model/runtime information where available, resource limits, and assumptions. Do not overwrite an existing run or module. Default to two repair cycles after the initial build; use a user-specified limit when supplied. Missing limits on costly work must be resolved before training.

Dispatch these roles through the runtime's subagent tool, sequentially. In Codex use the custom role if available; otherwise assign a native subagent the matching `agents/<role>.md`, `AGENTS.md`, and explicit skill paths. In Claude Code use the generated `.claude/agents/` roles. Record which mode actually ran:

1. `stem-learning-planner`: pass the brief, run ID, corpus catalog, and requested output. Save the returned `learning-spec.md` and handoff.
2. `stem-architect`: pass the brief, learning spec, relevant corpus paths, and constraints. Save returned `technical-plan.md` and handoff. Require input/output contract, acceptance IDs, algorithm/package rationale, adaptation table, and benchmark plan where relevant.
3. `stem-builder`: pass the accepted specifications, exact module/run directories, and criteria. Require `build-report.md` and actual module files. Record the handoff.
4. `stem-qa-reviewer`: pass specifications, module paths, and build report. Require `qa-report.md` and evidence. Record the handoff.

After each stage, inspect output against the design's stage gate, record artifact paths and status, and persist `run.json`. Save role-returned text with attribution; do not claim the role wrote a file itself when the orchestrator saved it. Use `templates/handoff.md` for each transition and `templates/qa-report.md` for verification.

Return defects to Builder and then QA for up to the configured repair limit. Send specification conflicts to Architect; preserve existing findings and versions. Stop with needs-review or blocked status when unresolved mandatory criteria, unavailable runtime/tools, exhausted budget, or repair limits prevent completion. Human review is required for scope/correctness ambiguity, not every routine stage transition.

Do not simulate missing subagent execution by writing all stage artifacts and reporting a multi-agent run. Record actual agent execution and skill-loading evidence supported by the runtime. An agent saying it used a skill is weaker than a trace; label the evidence type. Keep unavailable evidence explicit.

Finish with paths to the module, specifications, QA report, run record, exemplar adaptations, measurements, and limitations. Set `ready-for-review` only when all mandatory criteria have passed. Human acceptance is separate; do not mark a module an approved exemplar without review.
