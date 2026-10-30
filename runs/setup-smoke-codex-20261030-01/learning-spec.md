# Learning specification — setup smoke

Saved by the orchestrator from the returned response of `/root/smoke_planner`. Role assignment used explicit canonical files, not automatic custom-role selection.

Scope: a pure-Python projectile fixture demonstrating sequential role handoffs; no full pilot.

Assumed audience: introductory undergraduates familiar with algebra and trigonometry. Objective: predict how launch speed and angle affect flight time, horizontal range, and maximum height, then compare predictions with numerical outputs.

Required inputs: finite scalar speed 0–50 m/s and angle 0–90 degrees. Required outputs: flight time (s), range (m), maximum height (m). Assumptions: no drag, constant downward gravity 9.81 m/s², equal launch/landing height.

Learning sequence: state assumptions → predict → compute contrasting cases → explain results. Assessment: “Does vertical launch maximize range?” Feedback: no; horizontal velocity is zero. Under these assumptions, 45 degrees maximizes range at fixed positive speed. This is proposed learning content, not a measured learning outcome.

| Requirement | Inspected exemplar | Observed pattern | Adaptation and verification |
| --- | --- | --- | --- |
| Clear input feedback | `engine/check_datafile.py` in the SINDy source root | Rejects NaN/infinity before computation; returns explanatory messages | Validate scalar types, finiteness, and bounds before projectile calculations; check invalid inputs explicitly |

Planner reported source SHA-256 `79ee0bb486c3217963785a103feea964d6385f6d25441c9e4b566a72e1ac76af` matching the catalog.

Acceptance:

- SM-01: orchestrator records actual Planner → Architect → Builder → QA execution and handoffs.
- SM-02: architecture documents the inspected validation pattern and its adaptation.
- SM-03: QA independently verifies analytical expectations, invalid inputs, zero speed, horizontal launch, and vertical launch. Horizontal launch from ground has zero flight duration; vertical launch has zero range.
- SM-04: orchestrator saves outputs, evidence, and explicit statuses/limitations.

Limitations: no browser, UI, Flask/Bokeh, deployment, full-pilot acceptance, or learning-effectiveness verification. No blocking curriculum question for this smoke scope.

Evidence reported by Planner: explicitly read platform `AGENTS.md`, `agents/stem-learning-planner.md`, both requested skill files, run `brief.md`, `docs/design-proposal.md`, `corpus/catalog.json`, `corpus/sindy.md`, and original `engine/check_datafile.py`. These are file-read records, not automatic skill-loading evidence. Original tool activity remains in the subagent session; this document is a saved response with normalized notation.
