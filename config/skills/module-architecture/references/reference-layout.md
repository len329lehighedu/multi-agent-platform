# Reference layout (from the SINDy module, Bokeh part only)

```
<Module>/
  <Module>.py          Bokeh entry: build_app() creates engine + storage per session, Tabs([...])
  app_paths.py         MODULE_DIR, DATA_DIR from __file__
  engine/<model>.py    class Engine: fit, simulate/predict, diagnostics, metrics
  engine/check_datafile.py   validate_dataframe, validate_trajectory_set, check_upload_size
  tabs/train_tab.py    train_tab_layout(engine, storage) -> layout
  tabs/test_tab.py     test_tab_layout(engine, storage) -> (layout, update_fn)
  tabs/predict_tab.py  predict_tab_layout(engine, storage) -> (layout, update_fn)
  static/css, static/js
  data/                built-in datasets
  tests/test_engine.py, test_ui_contracts.py, test_app_smoke.py
  requirements.txt (pinned), run.sh, README.md, DEPLOYMENT.md
```

Patterns worth copying:
- Later tabs refresh lazily: `Tabs.on_change('active')` calls each tab's `update_fn` so model lists reflect new runs.
- `storage` maps run_id to model instance, metrics, plot data, config; tables restore any run.
- Upload handling decodes base64 in a next-tick callback and validates before use.
- Simulation failure raises; it never returns fake zeros.
- HTML description pages and the Flask shell of the original SINDy module are disabled for now; generate the Bokeh app only. (Later, the parent site embeds it with `server_document`.)
