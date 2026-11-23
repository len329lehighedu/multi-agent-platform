---
name: stem-bokeh-interaction
description: Implements and reviews Bokeh plots, controls, callbacks, per-session state, and responsive training interactions in STEM learning applications.
---

# Bokeh behavior

Inspect the selected exemplar's layout and callbacks before reuse. Create each session's engine, models, sources, and history separately. Connect each control to a defined scientific input; keep source columns aligned and show variable names and units on plots.

For inexpensive work, ordinary callbacks can update data directly. For long training, choose a worker strategy appropriate to the scientific library. Do not mutate Bokeh models from worker threads; schedule result publication on the owning document. Handle duplicate submissions, stale results after inputs change, failures, and the timeout/cancellation behavior agreed in the plan. Merely scheduling a long fit with `add_next_tick_callback` does not make it nonblocking.

Present status, validation errors, and scientific outputs where learners can understand them. Preserve run configuration with results so history can be interpreted and restored reliably.

Verify source changes and callbacks, then verify actual embedded browser behavior, including two-session isolation where state is retained. Test layout at the intended viewport; source inspection alone cannot establish rendered usability. Benchmark heavy computations separately from rendering.
