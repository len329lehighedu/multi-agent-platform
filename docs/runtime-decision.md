# Runtime decision: shared instructions with Codex and Claude adapters

Date: October 30, 2026

Decision: support Codex now and retain a Claude Code adapter for the team. AGENTS.md is the sole project instruction document. No CLAUDE.md is required or generated. Role definitions, skills, corpus, and run artifacts are shared; small adapters account for runtime differences. Models and reasoning settings inherit from the current session.

## Sources of truth

- `AGENTS.md`: project guidance and delegation rules.
- `agents/*.md`: canonical role responsibilities and required skills.
- `.agents/skills/`: canonical reusable skills, discovered by Codex when launched in the applicable directory.
- `.codex/agents/*.toml`: generated Codex custom-agent configuration.
- `.claude/agents/*.md` and `.claude/skills/`: generated Claude configuration/copies.
- `scripts/sync_runtime.py`: regenerate adapters after editing canonical files; `--check` detects drift without writing.

There are no model overrides, global configuration edits, permission bypasses, or enforced per-directory role sandboxes. Claude tools are configured in `agents/claude-tools.json`; Codex instructions request role behavior but do not enforce identical tool capabilities.

## Codex modes

1. Native session delegation: the parent assigns each available subagent the canonical role, AGENTS.md, explicit skill paths, and run inputs. This works in the current desktop session even though it began in the parent SINDy directory. It does not prove automatic discovery of newly created nested configuration.
2. Project discovery: start Codex with the platform directory as its working directory. Codex reads applicable AGENTS.md and `.agents/skills/`; current custom-agent files use `.codex/agents/*.toml`. Verify loaded names in the installed client before claiming custom-role selection.

The CLI present locally reports `0.163.0-alpha.10.2`. The desktop host version was not independently queried. The local `codex debug prompt-input` discovery inspection failed with `Operation not permitted` in the restricted execution environment. No model was called by that command. This does not imply that native delegation in the desktop session is unavailable.

## Claude Code mode

The documented launcher is:

```bash
claude --append-system-prompt-file AGENTS.md
```

This explicitly loads the shared guidance because renaming CLAUDE.md to AGENTS.md does not establish automatic Claude instruction loading. Generated role instructions also direct subagents to read AGENTS.md. No duplicate project instruction document is maintained. Claude is not on the checked PATH; its adapter remains statically verified only.

## Evidence and limits

The main conversation orchestrates stages through native tools. The workflow is prompt-driven, not a custom scheduling service or guaranteed state machine. Inspect saved artifacts and verification evidence at stage gates. Skill file reads are recorded separately from runtime-preload evidence. A successful setup smoke does not validate a complete application, browser interactions, or productivity claims.

Official documentation consulted October 30, 2026:

- [Codex AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Codex subagents and custom roles](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Codex local skills](https://learn.chatgpt.com/docs/build-skills)
- [Claude Code subagents](https://code.claude.com/docs/en/sub-agents)
- [Claude Code CLI prompt-file flag](https://code.claude.com/docs/en/cli-reference)
