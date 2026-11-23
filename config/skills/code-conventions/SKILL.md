---
name: code-conventions
description: Coding rules for generated modules: clarity, determinism, visible failures.
owner: builder
---
# Code conventions

- English comments and docstrings. Comment the why, especially mathematical and signal-processing choices.
- Type hints and short docstrings on every public engine function.
- Failures are visible: raise with a readable message; never return placeholder zeros or swallow exceptions. The UI catches and displays the message.
- Determinism: every random choice takes a seed from the config; record the seed with the run.
- No module-level mutable state; per-session objects are created in `build_app()`.
- Files stay under about 400 lines; split before they grow. Functions do one thing.
- Validate at the boundary (uploads, user input) in `engine/`, once, and reuse the validator across tabs.
- Python 3.13 compatible; exact pins in `requirements.txt`; no unused imports or dead code.
- Paths come from `app_paths.py`. Debug and host settings are explicit, never implicit.
- No HTML templates or Flask routes: the module is a Bokeh app.
