---
name: hyperparameter-spec
description: Specify each hyperparameter with default, range, effect and whether it becomes a UI control.
owner: researcher
---
# Hyperparameter specification

List every parameter the algorithm needs. For each give `default`, `range`, `effect` and `ui_control`.

**Exposure rule.** Expose a parameter (`slider`, `select`, `text`) only if changing it teaches something about the science: model capacity or library, regularization or threshold, split fraction, split method, noise level. Use `none` for implementation details such as random seeds and solver tolerances; these are fixed and recorded.

**Defaults** must produce a good, fast result on the built-in data so a first click of Train succeeds. Say in `effect` what the learner will observe when the value goes up or down, including the failure mode (overfit, empty model, divergence).

**Ranges.** Give a hard valid range and note combinations that are invalid or slow (for example high polynomial degree on many variables). Mention units.

Keep the exposed set small: at most 7 controls per module.

Use `slider` for bounded numbers, `select` for categories, `text` only for numbers that need exact entry.
