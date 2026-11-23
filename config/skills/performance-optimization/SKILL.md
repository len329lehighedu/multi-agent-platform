---
name: performance-optimization
description: Compute and rendering efficiency for interactive Bokeh modules, based on measurement.
owner: builder
---
# Performance optimization

Decide the strategy in the design; measure later. Never claim a speed you have not measured.

- **Compute once.** Derivatives, feature matrices and splits are computed once per run and cached in the run's storage entry, not on every callback.
- **Bound the work.** Enforce the data size and hyperparameter limits from the research brief with a visible message, so no input can make a callback run for minutes.
- **Vectorize.** NumPy over Python loops; no per-row DataFrame operations.
- **Choose inline vs background.** If the fit fits `max_train_seconds` comfortably, run inline and set `background_training: false`. Otherwise train in a worker and publish results from the owning document via `add_next_tick_callback`; never mutate Bokeh models from a worker thread. `add_next_tick_callback` alone does not make work non-blocking. Handle double clicks, stale results after inputs change, failures and timeout.
- **Render cheaply.** Update `ColumnDataSource.data` in one assignment. Toggle renderer `visible` instead of redrawing. Downsample traces above about 5,000 points for display only.
- **Keep sessions small.** Cap stored history; drop heavy arrays that can be recomputed.
- Benchmark compute separately from rendering, on representative data.

Record the chosen strategy and its limits in `performance`.
