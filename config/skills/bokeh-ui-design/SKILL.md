---
name: bokeh-ui-design
description: Plot count, layout, controls and in-app descriptions for a Bokeh learning module.
owner: builder
---
# Bokeh UI design

Everything is Bokeh: plots, inputs and short descriptions. No HTML pages.

**Layout per tab.** A 320 px control column on the left, one main plot (about 500 px high) on the right, up to three diagnostic plots (about 280 px) below; at most 5 plots per tab. Every plot names the learner question it answers (`question_answered`). Typical plots: fit against data and residuals (train), prediction on unseen data with its error (test), a forward prediction from a chosen input (predict).

**Controls and shared state.** One control per exposed hyperparameter (`hyperparameter` = its name). Slider for bounded numbers, Select for categories, Button for actions, FileInput with a visible file list for uploads; defaults from the research brief. A setting used by several tabs (data size, noise, seed, k) lives once in the session's shared state: one control, and every tab reads that state when it refreshes. Never give each tab its own copy of the same setting.

**Plots that read correctly.** Colour by a category with `factor_cmap("label", palette, factors)` from `bokeh.transform`, with string factors and a legend; `color="label"` treats the values as colour names and draws nothing. Keep the class colours in every plot where the class matters (neighbours, predictions). Fit the axis range to the data with a small margin when the differences are small (accuracies 0.85 to 0.95 on a 0 to 1 axis look flat); use a log axis when values span orders of magnitude.

**Feedback.** Status and validation messages in a Div, errors visibly distinct. Hover tooltips with variable and value; axis labels with units; meaning never depends on colour alone.

**In-app description.** Each tab starts with a short `Div`: what the controls do, what the plots show, what to conclude. Describe the science, not the pipeline.

**Bokeh API rules unit tests miss** (the platform loads `main.py` as a Bokeh app after the tests; a violation fails the build):
- A property callback is exactly `def handler(attr, old, new)`: no defaults, no `*args`. A Button callback is `def handler()` with `on_click`.
- Put the work in a no-argument `def refresh(): ...` and register `slider.on_change("value", lambda attr, old, new: refresh())`. Tests call `refresh()`, or a handler as `handler("value", None, None)`.
- Register callbacks once, inside the per-session code; build every model there, never at import time of `engine/`.
- Bokeh 3.x: `Tabs(tabs=[TabPanel(child=layout, title="Train")])` from `bokeh.models` (`Panel` is gone); figure size is `width=`/`height=`, never `plot_width`.
