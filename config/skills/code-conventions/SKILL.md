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
- No module-level mutable state; per-session objects are created inside `main.py`'s per-session code.
- Files stay under about 400 lines; split before they grow. Functions do one thing.
- Validate at the boundary (uploads, user input) in `engine/`, once, and reuse the validator across tabs.
- Match the interpreter and package versions stated in the context; exact pins in `requirements.txt`; no unused imports or dead code.
- Paths come from `app_paths.py`. Debug and host settings are explicit, never implicit.
- No HTML templates or Flask routes: the module is a Bokeh app.

**Mistakes seen in real builds, do not repeat:**
- Name every test after the criterion it checks, e.g. `test_ac3_best_degree_in_range`; the platform uses the ID in the name to tell an unreachable criterion (it asks the user) from a bug (it repairs).
- Tests use the standard library `unittest` only. `pytest` is not installed, so `import pytest` fails the whole suite.
- Never write an empty file. Give `__init__.py` a one-line docstring; an empty file is rejected.
- Write each file once, compactly. Do not repeat blocks or pad files; a long, repetitive reply is cut off at the output limit and the build fails.
- A change request must change at least one file. If the request needs no code change, say so in `message` and still return the one file whose documentation or test records the decision.
- Statistical tests (best degree, recovery rate across seeds) need a margin: choose thresholds from measured behaviour on several seeds, never exactly at the edge.