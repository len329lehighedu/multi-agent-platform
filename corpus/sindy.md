# SINDy: source-reviewed module case study

Review date: October 30, 2026. Review method: source inspection only; no new browser or performance validation. Catalog file hashes identify the inspected source snapshot.

Purpose: discover sparse governing equations from trajectory data and help learners compare fit, simulation, and robustness. This supplies concrete design and implementation examples for future agents.

| Area | Source paths relative to the SINDy root | Observed pattern | Reuse or improvement |
| --- | --- | --- | --- |
| Page and navigation | `templates/index.html`, `static/css/style.css` | Flask page combines explanatory HTML fragments and an embedded Bokeh workspace | Adapt lesson navigation and visual hierarchy; verify narrow viewports and actual rendering before claiming usability |
| Data input | `engine/check_datafile.py`, `tabs/train_tab.py` | CSV checks, finite values, increasing time, compatible trajectory columns; presets and uploads | Preserve clear validation; choose a schema appropriate to the new method rather than always requiring time-series columns |
| Controls and results | `tabs/train_tab.py` | Dataset/configuration controls, recommended profiles, model history, plots and diagnostics | Reuse the progression from input to configuration to result; adapt controls to scientific meaning |
| Scientific layer | `engine/sindy_model.py` | Fit, simulation, diagnostics, and ensemble computations separated from layout code | Keep computation independently testable; do not substitute sparse regression for a requested neural method |
| State | `main.py` | Engine and training storage constructed inside `build_app()` | Reuse per-session construction and explicitly test isolation |
| Test and prediction | `tabs/test_tab.py`, `tabs/predict_tab.py` | Separate unseen-data evaluation and forward simulation | Preserve the distinction between fit quality and generalization; a different module may use different navigation |
| Robustness | `tabs/ensemble_tab.py` | Bootstrap analysis and interpretable summaries | Reuse uncertainty presentation only when the method and denominator are justified |
| Web integration | `flask_app.py` | Flask shell embeds a separately served Bokeh app with environment-configured URL | Keep browser-to-Bokeh connectivity explicit; test WebSocket origins |
| Learning content | `templates/fragment/` | Explanation, training/test/prediction guidance, and curated questions | Adapt language and assessments to the actual audience; source presence does not establish educational effectiveness |
| Verification | `tests/test_app_smoke.py`, `tests/test_ui_contracts.py`, `tests/test_engine.py`, `tests/test_suggester.py` | Numerical and UI construction/contract checks | Add real browser interaction evidence; do not mistake construction checks for end-to-end behavior |
| Local launch | `run.sh` | Starts two processes, opens a browser after a fixed sleep, and handles termination | Replace fixed readiness assumptions with checks in a new scaffold |

## Performance limitation to avoid copying

The training button callback invokes fitting synchronously. Upload processing uses a next-tick callback, which schedules work but does not itself make expensive computation asynchronous. There is no measured training-time guarantee in this case study. A neural training module needs a workload-specific execution strategy, measured timings, visible progress, and a plan for time limits or cancellation.

## Example transfer: neural equation discovery

Likely transferable: dataset preview/validation, explicit controls, saved run configuration, fit-versus-held-out views, residual diagnostics, and contextual explanation.

Must be redesigned: algorithm/package, learned output representation, scaling/splitting, training controls, progress, compute budget, and how an explicit equation is extracted if required. The Architect should explain these choices using current official technical references. Do not claim a neural predictor has recovered a symbolic governing law merely because it fits the data.

## Provenance and review status

The source README displays an MIT badge, but a LICENSE file was not present in the inspected file listing. Reuse licensing is therefore unverified; do not represent this card as legal clearance to redistribute the source. The card contains internal observations and source pointers, not a copied source distribution. Status: source-reviewed, not approved-exemplar.
