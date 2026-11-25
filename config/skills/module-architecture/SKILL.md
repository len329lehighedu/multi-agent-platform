---
name: module-architecture
description: The Bokeh-only file layout, with train, test and predict in separate files.
owner: builder
---
# Module architecture

Follow the proven layout (full reference attached). The entry file is `main.py`: a Bokeh directory app that builds the tabs and adds the layout to `curdoc()`.

- `engine/`: all scientific computation and upload validation. It never imports Bokeh, so it is testable alone.
- `tabs/<id>_tab.py`: exactly one file per tab, exposing `<id>_tab_layout(engine, storage)`. Train, test and predict are separate files. A tab file over about 400 lines should be split.
- `main.py`: builds a fresh engine and storage dict per Bokeh session, so users never share state, then calls `curdoc().add_root(...)`. No module-level mutable state. The platform previews it with `bokeh serve <module folder>`.
- No `flask_app.py` and no HTML templates: HTML description pages and the Flask shell are disabled for now. Everything the learner sees is a Bokeh app served by `bokeh serve`.
- `app_paths.py` resolves data from the file location, not the working directory.
- `tests/`: engine tests, UI contract tests, one smoke test.
- Pinned `requirements.txt`, `run.sh` that starts the Bokeh server and stops it on Ctrl+C.

In `design_spec`: list every file with its role, the engine API (function, inputs, outputs), and map each acceptance criterion in `criteria_map`. Every tab needs `tabs/<id>_tab.py` in `files`.
