# Codex setup smoke: ready for review

The current Codex desktop session executed four actual native subagents sequentially: Planner → Architect → Builder → QA. Each received the shared AGENTS.md, canonical role, explicit skill paths and prior-stage artifacts. Existing SINDy source influenced the new fixture's input validation.

The smoke produced fixture/projectile.py and independent QA evidence. Eight numerical test methods passed; five platform setup tests passed. No implementation repair cycle was required. See qa-report.md and verification/execution.log for scope, commands and results, plus run.json, execution-evidence.json and handoff documents for provenance.

The platform now has shared role/skill sources and generated Codex/Claude adapters. AGENTS.md is the sole instruction file; there is no CLAUDE.md. Claude can explicitly load it with its documented prompt-file flag when available.

Verified execution mode: native Codex delegation with explicit role/skill file assignment. This does not establish automatic nested-project discovery, runtime-preloaded skills, or selection of generated custom-agent TOML. A local CLI discovery inspection failed with Operation not permitted; Claude was unavailable. Persisted dispatch summaries are labeled parent-authored records, not raw trace exports.

This small numerical fixture is not the full Flask/Bokeh pilot. Application dependency compatibility, UI/browser behavior, two-browser session isolation, training timings, learning effectiveness, and productivity improvement remain unverified. Human acceptance and exemplar promotion remain pending.
