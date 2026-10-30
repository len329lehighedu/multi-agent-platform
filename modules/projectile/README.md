# Projectile motion

An introductory undergraduate exploration of ideal projectile motion, using constant gravity 9.81 m/s², no drag, and equal launch and landing heights. Predict, move a slider, inspect labeled results, then reveal the three explanations in the lesson shell.

From the repository root, use the shared locked environment and launcher:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r modules/projectile/requirements.txt
.venv/bin/python scripts/serve.py --module projectile
```

The shared launcher serves the Flask lesson at http://127.0.0.1:8080 and Bokeh at http://127.0.0.1:5006. The browser needs both endpoints. Stop with Ctrl+C. See the root README for supported interpreter and lifecycle evidence; this module has no standalone server and does not launch services on import.

```sh
.venv/bin/python -m unittest discover -s modules/projectile/tests -v
```

`engine.trajectory(speed, angle, samples=201)` returns a `Trajectory` dataclass with aligned float64 `time`, `x`, `y` arrays and analytic `flight_time` (s), `range` (m), `max_height` (m). Speed accepts finite real scalars from 0 to 50, angle from 0 to 90 degrees. Booleans, strings, arrays, complex numbers, missing/nonfinite values and out-of-range values raise `ValueError`. Samples must be an integer from 2 to 10001. Zero-speed/horizontal launches produce all-zero samples; vertical launches have exactly zero range and x values. Summary height is analytic even when a coarse sample grid omits the apex.

`ui.build_document(doc)` creates all mutable state for one learner session. Named controls `speed`, `angle`, source `trajectory` (`t`, `x`, `y`) and Div `metrics` support interaction checks. The plot rescales after changes; x/y screen scales can differ, as stated beside the plot.

The implementation adapts SINDy's scientific/UI separation and per-session construction; it uses a focused vertical workspace rather than training/history tabs. Source provenance, measured tests, pending browser verification and assumptions are in `runs/mvp-completion-20261030/projectile-build-report.md`. No learning effectiveness, deployment, or hosted service claim is made.
