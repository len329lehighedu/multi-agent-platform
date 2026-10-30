# Current MVP verification

Final independent QA accepts all18mandatory pilot criteria for human review. A fresh environment was created at the relocated Documents root; 32main tests,9CSV adaptation tests,8independent QA groups, dependency check and actual browser suite passed there. See [final QA](../runs/mvp-completion-20261030/qa-report.md), fresh-environment.json and clean-install-and-final-tests.log in that run.

CLI prompt inspection at the relocated root exposed AGENTS.md and all8project skill names; custom role names were not present in that inspection. Actual subagent execution used explicit role/skill assignment. Claude remains unavailable.

The historical numerical smoke below remains provenance, not the current application acceptance boundary.

# Setup verification

Date: October 30, 2026

## Shared runtime integration

- AGENTS.md is the only project instruction file; CLAUDE.md was removed at Minh's request.
- Four canonical roles and eight canonical skills generate Codex TOML roles and Claude role/skill adapters.
- `python3 scripts/sync_runtime.py --check`: passed, no adapter drift.
- `python3 scripts/check_setup.py --runtime codex --require-runtime`: passed, four roles/eight skills, source hashes consistent, Codex CLI available.
- Five standard-library setup tests passed: current configuration, shared-skill adapter refresh, unknown skill, source-hash drift, and missing case study.
- YAML parsing passed for all 24 shared/generated role/skill Markdown files; Codex TOML files parsed with Python tomllib.
- Local Markdown links and code fences passed checks.

Exact setup commands/results are saved in `../runs/setup-smoke-codex-20261030-01/setup-checks.txt`.

## Live Codex smoke — passed within declared scope

A four-stage native-subagent smoke is recorded under `../runs/setup-smoke-codex-20261030-01/`. All four roles returned successfully; independent QA passed SM-01–04 for the numerical smoke with eight test methods and no implementation repairs. Human acceptance remains pending. This is explicit role/skill assignment in the current desktop session, which started from the parent SINDy directory.

The smoke produces a tiny standard-library numerical fixture, not a Flask/Bokeh application. Stage outputs, handoffs, source adaptation, actual commands/results, input hashes, and evidence limitations are saved. The parent chat contains actual native subagent tool activity. Persisted role IDs and dispatch summaries are parent-authored records, not raw trace exports.

## Discovery and tooling limitations

- Local CLI version: `0.163.0-alpha.10.2`. Desktop host version and exact inherited model version were not independently queried or overridden.
- `codex -C <platform-root> debug prompt-input` failed with `Operation not permitted` in the restricted execution environment. No model call was made. Automatic nested-project discovery and custom-role selection remain unverified; this failure does not prevent native delegation in the active desktop session.
- Claude Code is not installed on the checked PATH. Its generated adapter is statically checked only. The documented launcher explicitly loads AGENTS.md using `--append-system-prompt-file`.
- The skill-creator bundled Python validator was previously attempted but could not import PyYAML. No dependency was installed; standard YAML parsing plus local configuration checks were used instead. Neither is a substitute for runtime behavior evaluation.

## Still outside verified scope

No complete pilot application, Flask/Bokeh dependency compatibility, embedded browser interaction, UI responsiveness, two-browser session isolation, training benchmark, learning-effectiveness result, or productivity improvement has been established. Native explicit skill-file reads are not automatic skill-preload evidence.
