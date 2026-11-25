---
name: test-design
description: Test layers, the edge-case catalogue for data and ML modules, and headless UI testing.
owner: tester
---
# Test design

Map every case to criterion IDs. Choose the cheapest layer that can prove the criterion.

**Layers.** `engine` (pure functions, stdlib unittest), `scientific` (oracle comparison), `ui_contract` (build each tab layout headlessly, find widgets with `layout.select({"type": Button})`, invoke registered callbacks directly), `smoke` (the full app builds), `browser` (real rendering and WebSocket; needs a running server, list it in `not_runnable` when unavailable).

**Data edge cases.** NaN; infinity; duplicate or decreasing time; fewer rows than the minimum; one column only; constant column; non-numeric cell; column mismatch between files; oversized upload; extreme noise; very small sample.

**Model edge cases.** Threshold so high the model is empty (valid, must not crash); simulation divergence (must raise, not return zeros); extreme hyperparameters; the same seed reproduces the result; pooled trajectories are differentiated separately.

**UI edge cases.** Test or predict with no trained model; double click on train; delete the selected run; switch tabs before any run; two sessions do not share state; upload then clear.

Include at least one edge case per layer used. Write failing-condition assertions, not only happy paths. Determinism: fix every seed.

**Rules from real runs.** Write cases the module can pass: derive numeric thresholds from the oracle's tolerance with margin, and report a criterion you think unreachable as a risk instead of encoding it as a hard assertion. Use only `unittest` (no `pytest`). A passing unit suite does not prove the app opens: the platform loads `main.py` as a Bokeh app after the tests, so UI contract tests must build every tab with real Bokeh models and register its callbacks.