# Pilot A: projectile motion

Status: proposed pilot specification for review; no application has been built.

## Request and audience

Build an interactive projectile-motion lesson using Python, Bokeh, Flask, and HTML. Proposed audience: introductory undergraduates familiar with algebra and basic trigonometry. The pilot tests the agent workflow before a data science module.

Learners should predict and explain how initial speed and angle affect flight time, range, and maximum height, and identify the limits of the simplified model.

## Scientific contract

Use constant gravity 9.81 m/s², no air resistance, two-dimensional motion, and equal launch and landing height. Input speed: 0–50 m/s. Input angle: 0–90 degrees, measured from the horizontal. Defaults: 20 m/s and 45 degrees. Zero-speed and zero-angle cases produce zero flight duration and range without division errors or invalid plot data. Use numerical tolerance for endpoint roundoff.

Outputs: trajectory with position axes in meters, flight time in seconds, horizontal range in meters, maximum height in meters, and an explanation of the assumptions. Explain that equal complementary angles give equal range under these assumptions and that these conclusions do not automatically transfer to drag or unequal heights.

## Learner flow and examples

Use SINDy's separation of scientific engine, controls/plots, Flask shell, and explanatory content as the starting reference. Adapt its layout to a small exploration task; training history, uploads, fitting, and four model tabs are unnecessary here. Record the adaptation table and source paths.

Changing either control updates the trajectory and summaries. Include three assessment questions with explanatory answers or feedback: changing speed, complementary angles, and the model's assumptions. Keep all learner-facing text in English.

## Environment and execution

CPU only; deterministic bounded calculations. No neural training or external data. Use a module-local dependency environment and record verified Python/package versions. Do not infer dependency compatibility from the host's Python 3.14 installation. Use two services for Flask and Bokeh unless the Architect justifies a simpler integration that still satisfies the stack requirements.

Default repair limit: two cycles. No paid training runs, hosting, or deployment required. Record runtime/model usage when available. The user's agent-session limits govern orchestration; report unavailable cost data.

## Mandatory acceptance criteria

| ID | Behavior | Verification |
| --- | --- | --- |
| PM-01 | Documented setup starts the module and shuts down its services cleanly | Fresh dependency environment; actual launch/readiness/shutdown evidence |
| PM-02 | Flight time, range, height, and trajectory match analytical expectations | Independent checks for 20 m/s at 30 degrees and additional edge cases, with declared tolerances |
| PM-03 | Both controls update plotted data and summaries in the embedded page | Browser observations at multiple settings; no WebSocket/console failures |
| PM-04 | Zero-speed, zero-angle, vertical launch, and out-of-range engine inputs are handled explicitly | Boundary tests and finite plot-data checks; invalid engine inputs produce useful errors |
| PM-05 | Labels, units, assumptions, objectives, and three questions with feedback are present and scientifically consistent | Content review plus rendered inspection |
| PM-06 | Two learner sessions have independent control state | Two-session interaction check |
| PM-07 | Controls remain usable during interaction and layout is readable at desktop and narrow viewport | Browser review; record actual viewport sizes and observed limitations |
| PM-08 | Agent execution and exemplar adaptations are traceable | Stage artifacts, handoffs, available runtime traces, and adaptation table |

Automated numerical checks alone cannot satisfy PM-03, PM-06, or PM-07. Mark unavailable browser checks not-run. Final result is ready for review only after all mandatory criteria pass; human acceptance remains separate.
