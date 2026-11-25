---
name: bokeh-ui-design
description: Plot count, layout, controls and in-app descriptions for a Bokeh learning module.
owner: builder
---
# Bokeh UI design

Everything is Bokeh: plots, inputs and short descriptions. Separate HTML description pages are disabled for now.

**Layout per tab.** A 320 px control column on the left; one main plot (about 500 px high, stretch width) on the right; a row of up to three diagnostic plots (about 280 px) below. At most 5 plots per tab. Every plot must name the learner question it answers (`question_answered`); drop a plot that answers none.

**Choosing plots.** Fit tab: model result against data, residual versus time, predicted versus true. Test tab: true versus simulated on unseen data with per-variable error. Predict tab: forward trajectory from a chosen starting point. Add others only with a clear question.

**Controls.** One control per exposed hyperparameter, with `hyperparameter` set to its name. Bounded numbers use a Slider paired with a synchronized TextInput; categories use Select; actions use Button; uploads use FileInput with a visible file list and a clear button. Defaults come from the research brief. Disable actions while work is running.

**Feedback.** Status and validation messages in a Div, error text visibly distinct. A history table lets the learner reselect a past run and restore its plots. Hover tooltips show variable, trajectory, time and value. Axis labels carry units. Meaning must not depend on colour alone.

**In-app description.** Each tab starts with a short `Div` that mirrors the tab top to bottom: what the control does, what the plot shows, what to conclude. Describe the science, not the agent pipeline. No persistent quiz blocks. Do not create HTML files.

**Bokeh API rules that unit tests miss** (the platform loads `main.py` as a Bokeh app after the tests, and a violation fails the build):
- A property callback is `def handler(attr, old, new)` with exactly those three positional parameters and no defaults. Never `def handler(attr=None, old=None, new=None)` and never `*args`. A Button callback is `def handler()` and is registered with `on_click`.
- Register callbacks with `widget.on_change("value", handler)` or `button.on_click(handler)`, once, inside the per-session function.
- Build every model inside the per-session code that `main.py` runs, never at import time of `engine/`.
- Bokeh 3.x tabs: `Tabs(tabs=[TabPanel(child=layout, title="Train"), ...])`, all from `bokeh.models`. `Panel` no longer exists; `Panel(child=...)` fails at load. Figure size is `width=` and `height=`, never `plot_width` or `plot_height`.