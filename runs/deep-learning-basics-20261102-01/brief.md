# Module brief: Deep Learning Basics

## Request and audience

User request: “I want to build a new module relate to deep learning. Research inputs needed, display the graph using bokeh. make it simple.”

Module ID: `deep-learning-basics`. Proposed audience: introductory undergraduate learners or researchers new to neural networks; prerequisites: plotting points and basic functions. The explicit requirements are a new deep learning module, research data inputs, a Bokeh graph, and simplicity.

## Scientific contract

Teach supervised one-dimensional regression with a small neural network (one hidden layer). Output is a numerical prediction curve, **not** an explicit scientific equation. Inputs are either a seeded built-in sample or a two-column CSV with headers `x,y`, finite numeric values, at least 20 and at most 500 rows, and at least 10 distinct x values. Units are dataset-defined and displayed as generic x/y. The graph shows observed points and the trained prediction curve; a loss graph shows training history. Use a deterministic train/test split and report held-out error. Reject malformed inputs with a visible explanation. Explain that a good fit does not prove a causal law.

## Learner experience

1. Start from the sample or upload `x,y` data.
2. Adjust a small number of learning controls, train, and watch progress/status.
3. Compare Bokeh data points, prediction curve, training loss, and held-out error.

Keep the page in the platform's lesson shell with a full-width workspace. Use three short assessment questions with answers in metadata. Inspect `corpus/catalog.json`, `corpus/sindy.md`, and original SINDy source for validation, session state, and graph patterns; also inspect the existing neural-equation-finder implementation for integration lessons without cloning its equation-discovery scope.

## Execution constraints

CPU-only default; dataset cap 500 rows. Limit model complexity and training to a small fixed upper bound (architect selects exact controls and caps); avoid a long synchronous Bokeh callback. One training job per session, bounded execution, deterministic seed. No cloud training or external data service. Run budget: one lightweight local CPU fit and bounded verification fits; no GPU requirement. Two repair cycles after initial build. Use the repository's shared Flask/Bokeh runtime and a module-local dependency file; verify actual environment versions and measured timings before claims.

## Acceptance criteria

| ID | Mandatory behavior | Verification | Responsible role |
| --- | --- | --- | --- |
| DL-01 | Sample and valid `x,y` CSV train a genuine one-hidden-layer neural regression model | Independent numerical and input tests | Builder, QA |
| DL-02 | Invalid, nonfinite, insufficient, or oversized CSV is rejected with clear UI feedback | Engine tests and browser interaction | Builder, QA |
| DL-03 | Bokeh updates data/prediction and loss plots plus held-out error after training | Browser interaction and callback evidence | Builder, QA |
| DL-04 | Repeated runs are deterministic for identical data/settings and fit uses train data only | Independent tests | Builder, QA |
| DL-05 | Training remains bounded and gives visible progress/status without blocking the document for the full fit | Timing, code inspection, browser check | Architect, Builder, QA |
| DL-06 | Lesson instructions, assumptions, and at least three questions correctly explain inputs and prediction limits | Metadata/content inspection | Planner, QA |
| DL-07 | Module launches through shared Flask/Bokeh runtime using documented setup | Startup and embedded browser check | Builder, QA |

## Assumptions and unresolved issues

“Research inputs needed” is interpreted as learner-supplied numeric research observations (`x,y`) with a documented CSV schema, plus a sample for first use. This is a learning example and does not claim to handle images, text, multivariate datasets, or scientific equation discovery. No blocking question is identified for this limited scope.
