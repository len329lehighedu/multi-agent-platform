# Current platform usage

The active application is now the single `neural-equation-finder` dashboard. The projectile and linear-regression source modules were removed on October 30, 2026; references below to the original pilots describe historical setup-smoke context. For current run, CSV, browser, and interpretation steps use [the Vietnamese testing guide](testing-guide.vi.md) and `runs/neural-equation-20261030-01/`.

For running the dashboard, automated/browser tests, and the advisor demo, start with [the complete walkthrough](testing-guide.vi.md). Shared hosting is implemented in `stem_platform/runtime.py`; `scripts/create_module.py` still creates a runnable lesson-style starter.

# Using the platform with Codex or Claude Code

## Check shared configuration

From the platform directory, using Python 3.11 or newer:

```bash
python3 scripts/sync_runtime.py --check
python3 scripts/check_setup.py --runtime codex --require-runtime
```

The checker verifies canonical roles/skills, generated adapter consistency, TOML structure, source paths/hashes, and CLI presence. It makes no model calls. For Claude availability use `--runtime claude`; its absence is optional for Codex users. Python 3.14 is installed locally, but each generated module still needs its own dependency verification.

After changing `agents/*.md`, `agents/claude-tools.json`, or `.agents/skills/`, regenerate adapters:

```bash
python3 scripts/sync_runtime.py
```

Do not edit generated `.codex/agents/`, `.claude/agents/`, or `.claude/skills/` directly. The checker detects drift. No global Codex/Claude configuration or user account is changed.

## Codex desktop: current session

This chat began in the parent SINDy workspace. Ask Codex to read `multi-agent-platform/AGENTS.md` and the workflow skill at `multi-agent-platform/.agents/skills/stem-build-module/SKILL.md`, then explicitly delegate the named canonical roles using the available subagent tools. Pass the platform root and each relevant skill path to each agent.

This explicit mode does not depend on newly created nested skills appearing automatically in the current chat's skill catalog. Record actual role assignments and skill reads, rather than labeling them automatic preloads. Saved execution evidence for the setup smoke lives under `runs/setup-smoke-codex-20261030-01/`.

## Codex in a new project session

Open this folder as the working project in the desktop app, or launch the installed CLI here:

```bash
codex -C "/absolute/path/to/multi-agent-platform"
```

Verify AGENTS.md, eight project skills, and the four `stem-*` custom roles are exposed by the client. In CLI/IDE skill selectors, use `$stem-build-module`; a natural-language request can also select the workflow. If a new skill is absent, restart the session and recheck directory discovery. CLI presence alone is not a live discovery test.

Example request:

> Use $stem-build-module with briefs/projectile-motion.md. Delegate Planner, Architect, Builder, and QA using the shared roles. Record actual subagent execution and checks. Do not claim browser criteria passed without browser evidence.

If custom-role discovery is unavailable but native subagents work, use explicit role/skill file assignment and label that mode. Do not simulate a multi-agent run by writing all artifacts in the main conversation.

## Claude Code, when available

Use an approved installation and authenticated account. From this directory:

```bash
claude --append-system-prompt-file AGENTS.md
```

The flag supplies the shared instructions without a CLAUDE.md file. Verify roles with `/agents`, skills, and warnings before use. Then invoke `/stem-build-module` with a brief or natural-language request. This adapter has not been executed locally because Claude Code is unavailable.

## Setup smoke scope

Run a bounded four-stage exercise before a complete pilot: Planner inspects an actual exemplar; Architect consumes the learning spec; Builder implements a tiny numerical fixture in the run directory; QA independently checks it. Save stage responses, explicit role/skill read evidence, handoffs, and limitations. No Flask/Bokeh UI is built by this smoke, and full pilot browser criteria remain not-run.

For a complete module, use `templates/module-brief.md`. Outputs belong in `modules/<module-id>/`; records belong in `runs/<run-id>/`. Final reports distinguish automated checks, browser evidence, blocked work, and human acceptance.

## Add examples and feedback

Use `corpus/module-card-template.md` and register source paths, review status, revision, and SHA-256 hashes in `corpus/catalog.json`. Agents learn design and implementation patterns from the examples in context. For neural equation discovery, define the required equation representation, method/packages, data handling, plots, training budget, and benchmark evidence specifically for the request.

Record human feedback as proposed changes with supporting evidence. Generated work is not automatically an approved exemplar. If moving the platform into a standalone repository, update relative source pointers deliberately and recheck access and hashes.
