# Technical plan — setup smoke

Saved by the orchestrator from `/root/smoke_architect`, with normalized notation. Actual tool activity remains in the subagent session.

Implement `fixture/projectile.py` under this run as a pure deterministic module using only Python's standard library. No server, UI, data files, fitting, preprocessing, or train/test split is needed.

Expose `projectile_summary(speed_m_s, angle_deg)`, returning a fresh dictionary with exactly three keys: `flight_time_s`, `range_m`, `max_height_m`. Each value is a finite nonnegative float.

Use gravity 9.81 m/s², no drag, equal launch/landing height. Resolve velocity into `vx = v*cos(theta)` and `vy = v*sin(theta)`; calculate `T = 2*vy/g`, `R = vx*T`, `H = vy**2/(2*g)`.

Accept built-in int and float only, excluding bool. Raise TypeError for strings, complex values, containers, None, and other types. Raise ValueError for nonfinite/out-of-range numbers. Messages identify the parameter and permitted range: speed [0, 50], angle [0, 90]. Check bounds before float conversion to avoid overflow on enormous integers. Validate both inputs before special cases. Accept signed zero; normalize output zeros to positive zero.

Zero speed or zero angle returns exact 0.0 values for all outputs. At angle 90 set vx to exact 0.0; flight time and height remain positive for positive speed. Do not snap nearby angles to endpoints.

Use the standard-library math API; Builder records its actual interpreter version. Architect cited [official math documentation](https://docs.python.org/3/library/math.html); this document does not independently establish how that external page was accessed. No package installation or version compatibility claim is needed for the plan.

## Independent verification plan

- (10, 45): T = 10*sqrt(2)/9.81; R = 100/9.81; H = 25/9.81.
- (50, 90): T = 100/9.81; R = 0; H = 2500/19.62.
- Use relative and absolute tolerance 1e-12 for nonzero analytical checks; require exact endpoint zeros.
- Check complementary-angle range symmetry, speed scaling, boundaries, and every invalid-input category without importing implementation helpers.

| Requirement | Inspected exemplar | Adaptation and verification |
| --- | --- | --- |
| Clear input feedback | SINDy `engine/check_datafile.py` rejects missing/nonfinite CSV values before computation | Retain early explanatory validation; replace dataframe constraints with scalar bounds; test exceptions |
| Independent science | Corpus describes engine/UI separation | Keep fixture importable without services; verify analytical special cases |

Builder implements the interface and records execution evidence; QA supplies independent checks. SM-01 depends on actual execution/handoffs; SM-02 on this adaptation; SM-03 on numerical QA; SM-04 on saved artifacts and honest statuses.

Architect reported explicit reads of AGENTS.md, its role file, all three named skills, run brief/spec/handoff, design proposal, catalog, case study, and original validation source. Reported SHA-256 matched `79ee0bb486c3217963785a103feea964d6385f6d25441c9e4b566a72e1ac76af`. This is explicit file-read evidence, not automatic skill discovery. Architect performed no edits or tests. Browser, Flask/Bokeh, deployment, timing, and learning-effectiveness acceptance remain not-run.
