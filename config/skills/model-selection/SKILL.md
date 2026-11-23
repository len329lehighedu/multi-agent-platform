---
name: model-selection
description: Choose the module's model and algorithm from the required output type, with rejected alternatives.
owner: researcher
---
# Model selection

Start from the output the learner needs, then pick the simplest method that delivers it.

| Required output | Method family to consider |
| --- | --- |
| An explicit interpretable equation | Sparse regression (e.g. SINDy), symbolic regression |
| A numerical predictor or learned vector field | Regression, neural network, neural ODE |
| Unknown coefficients of a known law | Parameter inference, least squares, physics-informed fit |
| A class label | Classifier with a stated decision metric |

**Rules.**
- Never substitute a convenient algorithm for the required output. A neural network is not an interpretable equation.
- Compare at least two candidates in `method.rejected` with a concrete reason for each rejection (output mismatch, data need, compute, interpretability).
- Prefer methods that run on CPU within the task's `max_train_seconds` on the built-in data.
- State assumptions the method needs (sampling, noise, smoothness, library coverage) in `rationale`.
- Set `output_type` to what the learner receives, not to the internal technique.
- If the request is ambiguous between output types, record your interpretation in `rationale`; the Project Manager decides whether to ask.

Do not write code or choose UI elements.
