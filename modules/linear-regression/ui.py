"""All models and callback state are constructed separately per Document."""
import html
import numpy as np
from bokeh.layouts import column
from bokeh.models import Button, CDSView, ColumnDataSource, Div, GroupFilter, HoverTool, NumericInput, Slider, Span
from bokeh.plotting import figure
from .engine import MAX_SEED, generate_data, fit_and_evaluate


def build_document(doc):
    noise = Slider(title="Noise standard deviation σ (response units)", start=0, end=5, step=.1, value=1, name="noise", sizing_mode="stretch_width")
    count = Slider(title="Sample count n", start=20, end=300, step=1, value=100, name="sample_count", sizing_mode="stretch_width")
    seed = NumericInput(title=f"Random seed (integer, 0–{MAX_SEED})", value=42, low=0, high=MAX_SEED, mode="int", name="seed", sizing_mode="stretch_width")
    generate = Button(label="Generate and fit", button_type="primary", name="generate", sizing_mode="stretch_width")
    status = Div(name="status", sizing_mode="stretch_width")
    metrics = Div(name="metrics", sizing_mode="stretch_width")
    observations = ColumnDataSource(dict(x=[], y=[], prediction=[], residual=[], split=[], marker=[]), name="observations")
    residuals = ColumnDataSource(dict(x=[], residual=[], split=[], marker=[]), name="residuals")
    fit_line = ColumnDataSource(dict(x=[], y=[]), name="fit_line")
    true_line = ColumnDataSource(dict(x=[0., 10.], y=[1., 21.]), name="true_line")
    scatter = figure(title="Observations and fitted relationship", x_axis_label="x (dimensionless)", y_axis_label="y (dimensionless)", height=360, min_width=280, sizing_mode="stretch_width", tools="pan,wheel_zoom,box_zoom,reset,save")
    diagnostic = figure(title="Residuals: observed y − fitted prediction", x_axis_label="x (dimensionless)", y_axis_label="Residual (response units)", height=300, min_width=280, sizing_mode="stretch_width", tools="pan,wheel_zoom,box_zoom,reset,save")
    for split, color, marker, label in (("train", "#146b91", "circle", "Train (circles)"), ("test", "#b34a13", "triangle", "Test (triangles)")):
        for plot, source, response in ((scatter, observations, "y"), (diagnostic, residuals, "residual")):
            plot.scatter("x", response, source=source, view=CDSView(filter=GroupFilter(column_name="split", group=split)), marker=marker, size=8, color=color, alpha=.8, legend_label=label)
    scatter.line("x", "y", source=true_line, line_color="#555555", line_dash="dashed", line_width=2, legend_label="True: y = 2x + 1")
    scatter.line("x", "y", source=fit_line, line_color="#7a309c", line_width=3, legend_label="Training fit")
    scatter.add_tools(HoverTool(tooltips=[("x", "@x{0.000}"), ("y", "@y{0.000}"), ("prediction", "@prediction{0.000}"), ("residual", "@residual{0.000}"), ("split", "@split")], renderers=scatter.renderers[:2]))
    diagnostic.add_layout(Span(location=0, dimension="width", line_dash="dashed", line_color="#555555"))
    for plot in (scatter, diagnostic):
        plot.legend.location = "top_left"
        plot.legend.label_text_font_size = "10px"
        plot.legend.spacing = 2
        plot.legend.padding = 4
    committed = {}

    def mark_pending(attr, old, new):
        status.text = "<strong>Pending changes.</strong> Click Generate and fit to apply controls. Plots and metrics show the last committed run."

    def update():
        try:
            config = dict(noise=noise.value, sample_count=count.value, seed=seed.value)
            data = generate_data(**config)
            result = fit_and_evaluate(data)
        except (ValueError, TypeError) as exc:
            status.text = f"<strong>Input error:</strong> {html.escape(str(exc))} Click Generate and fit after correcting controls. Previous results remain visible."
            return
        split = np.full(len(data.x), "test", dtype=object)
        split[data.train_idx] = "train"
        markers = np.where(split == "train", "circle", "triangle")
        observations.data = dict(x=data.x, y=data.y, prediction=result.predictions, residual=result.residuals, split=split, marker=markers)
        residuals.data = dict(x=data.x, residual=result.residuals, split=split, marker=markers)
        fit_line.data = dict(x=[0., 10.], y=[result.intercept, result.slope * 10 + result.intercept])
        true_line.data = dict(x=[0., 10.], y=[1., 21.])
        committed.update(config)
        metrics.text = (f"<h3>Committed run</h3><p>Fitted equation: ŷ = {result.slope:.6f} x {result.intercept:+.6f}</p>"
                        f"<p>σ = {config['noise']:g}; n = {config['sample_count']}; seed = {config['seed']}. "
                        f"Train: {len(data.train_idx)} rows; test: {len(data.test_idx)} rows (75% training, rounded down).</p>"
                        f"<p>Training MSE: {result.train_mse:.6g}; test MSE: {result.test_mse:.6g} (squared response units).</p>")
        status.text = "Run committed. Only training rows determined the fitted line; held-out test rows evaluate it."

    for widget in (noise, count, seed):
        widget.on_change("value", mark_pending)
    generate.on_click(update)
    update()
    doc.add_root(column(Div(text="<p>Predict: how will more noise change the scatter and held-out error? Change controls, then click <strong>Generate and fit</strong>. With the same seed and n, noise comparisons reuse the same draws and split; changing n may change the realization.</p>", sizing_mode="stretch_width"), noise, count, seed, generate, status, metrics, scatter, diagnostic, Div(text="<p>A point above the fitted line has a positive residual. MSE averages squared residuals. With the same seed and n, residuals scale with σ and both MSEs scale with σ² (apart from rounding): doubling σ quadruples MSE. Comparisons across different random realizations, seeds, or splits need not be monotonic in σ. Test error can be smaller or larger than training error.</p>", sizing_mode="stretch_width"), sizing_mode="stretch_width", min_width=280, name="regression_workspace"))
    doc.title = "Linear regression: noise and held-out evidence"
