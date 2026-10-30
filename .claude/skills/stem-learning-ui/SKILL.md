---
name: stem-learning-ui
description: Adapts existing STEM module UI patterns into clear HTML and Bokeh learner flows, input controls, results, and scientific presentation.
---

# UI from examples and requirements

Read relevant HTML, CSS, and Bokeh layout sources from the corpus. If available, inspect screenshots or the running module. Record whether visual observations come from rendered evidence or source inspection.

Design the learner's path from scientific question to inputs, action, result, and interpretation. Reuse familiar patterns such as dataset selection, configuration controls, model history, and diagnostic panels only when they fit the new task. Do not copy SINDy's tabs or labels into unrelated lessons by default.

Choose controls with valid ranges, defaults, units, help text, and visible errors. Distinguish fit, test, and prediction outputs. For neural training, explain progress, runtime limits, failures, and what the learned output means without promising an unmeasured duration.

Use readable axes and legends, semantic HTML, keyboard-usable controls, sufficient contrast, and meaning beyond color alone. Verify intended viewport behavior and that explanatory content matches the plots. Learner-facing text should describe the science, not the multi-agent pipeline.
