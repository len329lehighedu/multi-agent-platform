# STEM module development workspace

Work from this directory. Follow the user's module request and read `docs/design-proposal.md` for project intent. For module-build and setup-smoke requests, delegate to the four project subagents defined in `agents/`; the main conversation orchestrates them sequentially as needed. For routine edits, use judgment about delegation. This is a prompt-driven workflow, not a custom scheduling service.

## Learn from the module corpus

Existing modules are the project's design and implementation examples. Start with `corpus/catalog.json` and the relevant case study; inspect original source before reusing a pattern. Record which examples influenced input/output, data handling, layout, interactions, and presentation. Adapt to the new requirements and improve weaknesses instead of cloning a module blindly. This is learning from examples in context, not model-weight training.

Use `python3 scripts/check_setup.py` to check local setup and reference drift. Corpus locations are resolved relative to the catalog file. The initial SINDy source is outside this directory, at the source root recorded in the catalog; read it only where the session permits. If source access is unavailable, report that limitation rather than claiming source inspection.

## Workflow

In Codex use `$stem-build-module`; in Claude Code use `/stem-build-module`, with a brief path or natural-language module request. The workflow skill defines dispatch, artifacts, and completion gates. Pass each subagent the run directory, task, acceptance criteria, and relevant reference paths explicitly; subagents do not receive the whole conversation automatically. Canonical role instructions live in `agents/`. Skills live in `.agents/skills/`. Claude adapters preload named skills; Codex role instructions explicitly request reading the relevant skill files.

Keep generated module code in `modules/<module-id>/` and run records in `runs/<run-id>/`. Treat the original SINDy application as read-only unless the user asks to change it. Role write scopes are conventions, not filesystem sandbox guarantees. Inherit the session's normal permissions; no configuration here bypasses them.

## Scientific and runtime claims

Choose methods and packages for the requested scientific output. A neural network predictor does not automatically return an interpretable equation. Define whether the user needs an explicit expression, a learned vector field, or a numerical prediction model. Distinguish measured timings from estimates and include dataset size, hardware, device, epochs, and software versions. Do not promise a training duration before benchmarking.

Every run must distinguish implemented, verified, failed, blocked, and not-run work. No automatic deployment is part of this workflow. Capture human feedback as proposed case-study improvements; do not silently promote an unreviewed generated module into an approved exemplar.
