"""Session-local dashboard, background training, atomic result publication."""
import base64
import html
import time

import numpy as np
from bokeh.layouts import column, row
from bokeh.models import (
    Button, CDSView, ColumnDataSource, CustomJS, Div, FileInput, GroupFilter,
    InlineStyleSheet, MultiChoice, NumericInput, Select, Span, TextInput,
    Tooltip,
)
from bokeh.plotting import figure

from .engine import MAX_BYTES, parse_csv, prepare_data, validate_config
from .worker import WorkerJob


CONTENT_CSS = """
  :host{color:var(--ink)}
  h1{font-size:clamp(27px,3vw,38px);line-height:1.12;letter-spacing:-1.1px;margin:2px 0 0}
  h3{margin:0;font-size:16px}.module-kicker{font-size:11px;font-weight:750;letter-spacing:1.4px;color:var(--blue)}
  .status-badge,.status-chip,.equation-chips span,.file-chip{display:inline-flex;align-items:center;border-radius:999px;padding:4px 9px;margin:2px 4px 2px 0;font-size:12px;font-weight:650;border:1px solid var(--line);background:var(--soft)}
  .status-badge.ok{color:var(--ok);border-color:var(--ok)}
  .kpi-strip{display:grid;grid-template-columns:repeat(auto-fit,minmax(118px,1fr));gap:9px}.kpi{min-width:0;background:var(--card);border:1px solid var(--line);border-left:4px solid #98a2b3;border-radius:10px;padding:11px 10px}.kpi.ok{border-left-color:var(--ok)}.kpi.warn{border-left-color:var(--warn)}.kpi.err{border-left-color:var(--err);background:color-mix(in srgb,var(--err) 6%,var(--card))}.kpi small{display:block;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.kpi strong{display:block;font-size:20px;line-height:1.25;margin-top:3px}.kpi.err strong{color:var(--err)}
  .kpi-tile small{display:block;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.kpi-tile strong{display:block;font-size:20px;line-height:1.25;margin-top:3px}
  .data-preview{border-collapse:collapse;white-space:nowrap;width:100%;font-size:12px}.data-preview th,.data-preview td{text-align:left;padding:5px 7px;border-bottom:1px solid var(--line)}.data-preview th{color:var(--muted);font-weight:650}.preview-meta,.field-note,.equation-map{color:var(--muted);font-size:12px;margin:4px 0 7px}.equation-line{white-space:pre-wrap;overflow-wrap:anywhere;font:600 14px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--soft);border-radius:9px;padding:12px;margin:0 0 9px}.equation-chips span{font-size:11px}
  @media(max-width:900px){.kpi-strip{grid-template-columns:repeat(2,minmax(0,1fr))}}
"""


def _content_stylesheet():
    return [InlineStyleSheet(css=CONTENT_CSS)]


def sample_csv():
    x = np.linspace(-2, 2, 300)
    return "x,target\n" + "\n".join(
        f"{value:.17g},{(.5 * value * value - 1.2 * value + .7):.17g}" for value in x
    )


def _rounded_equation(coefficients, powers, digits=4):
    """Format the displayed surrogate compactly; computation keeps full precision."""
    parts = []
    for coefficient, power in zip(coefficients, powers):
        factors = []
        for index, exponent in enumerate(power):
            if exponent:
                factors.append(f"x{index + 1}" + (f"^{exponent}" if exponent != 1 else ""))
        magnitude = f"{abs(float(coefficient)):.{digits}g}"
        term = magnitude + ("·" + "·".join(factors) if factors else "")
        if not parts:
            parts.append(("−" if coefficient < 0 else "") + term)
        else:
            parts.append((" − " if coefficient < 0 else " + ") + term)
    return "y = " + "".join(parts)


def build_document(doc):
    state = dict(
        csv=sample_csv(), table=None, filename="Built-in sample", job=None,
        generation=0, closed=False, committed=None, started=0,
    )
    state["table"] = parse_csv(state["csv"])
    common = dict(sizing_mode="stretch_width", min_width=0)

    upload = FileInput(accept=".csv", name="upload", **common)
    file_chip = Div(text="", sizing_mode="stretch_width", stylesheets=_content_stylesheet())
    clear_file = Button(label="×", button_type="default", width=34, visible=False)
    target = Select(title="Target", options=list(state["table"].headers), value="target", name="target", **common)
    features = MultiChoice(title="Input features (1–4)", options=list(state["table"].headers), value=["x"], name="features", **common)
    hidden = TextInput(title="Hidden layers", value="32,32", name="hidden_layers", **common)
    activation = Select(title="Activation", options=["identity", "logistic", "tanh", "relu"], value="tanh", name="activation", **common)
    solver = Select(title="Solver", options=["lbfgs", "adam", "sgd"], value="lbfgs", name="solver", **common)
    alpha = NumericInput(title="L2 alpha", value=.0001, low=0, high=10, name="alpha", **common)
    rate = NumericInput(
        title="Learning rate", value=.001, low=1e-6, high=1, disabled=True,
        name="learning_rate",
        description=Tooltip(content="Used by adam and sgd. L-BFGS chooses its own steps."),
        **common,
    )
    iterations = NumericInput(title="Max iterations", value=1000, low=1, high=2000, mode="int", name="max_iter", **common)
    fraction = NumericInput(title="Test fraction", value=.2, low=.1, high=.4, name="test_fraction", **common)
    degree = NumericInput(title="Equation degree", value=2, low=1, high=4, mode="int", name="equation_degree", **common)
    seed = NumericInput(title="Seed", value=42, low=0, high=2**32 - 1, mode="int", name="seed", **common)
    train = Button(label="Train", button_type="primary", name="train", height=44, **common)

    status = Div(text="Ready · built-in sample", name="status", sizing_mode="stretch_width", stylesheets=_content_stylesheet())
    warning_button = Button(label="⚠ Not converged", button_type="warning", visible=False, width=150)
    warning_hint = Div(text="", visible=False, sizing_mode="stretch_width", stylesheets=_content_stylesheet())
    double_iterations = Button(label="Double max_iter", visible=False, width=150)
    scale_features = Button(label="Scale features", visible=False, width=140)
    metrics = Div(text="Metrics appear after training.", name="metrics", visible=False, sizing_mode="stretch_width")
    kpi_models = [Div(text="", sizing_mode="stretch_width", stylesheets=_content_stylesheet()) for _ in range(6)]
    equation = Div(
        text="<p>Train a model to see the surrogate equation.</p>", name="equation",
        sizing_mode="stretch_width", styles={"overflow-x": "auto", "min-width": "0"}, stylesheets=_content_stylesheet(),
    )
    copy_equation = Button(label="Copy", button_type="default", width=72, tags=[""])
    copy_equation.js_on_click(CustomJS(code="""
        const value = cb_obj.tags.length ? cb_obj.tags[0] : ""
        if (value && navigator.clipboard) navigator.clipboard.writeText(value)
    """))
    preview = Div(name="preview", sizing_mode="stretch_width", styles={"overflow-x": "auto", "min-width": "0", "max-height": "190px"}, stylesheets=_content_stylesheet())

    observations = ColumnDataSource(dict(x=[], y=[], actual=[], prediction=[], split=[], marker=[]), name="observations")
    nn_curve = ColumnDataSource(dict(x=[], y=[]), name="nn_curve")
    equation_curve = ColumnDataSource(dict(x=[], y=[]), name="equation_curve")
    identity_line = ColumnDataSource(dict(x=[], y=[]), name="identity_line")
    residuals = ColumnDataSource(dict(x=[], residual=[], split=[], marker=[]), name="residuals")
    loss = ColumnDataSource(dict(iteration=[], objective=[]), name="loss")

    plot = figure(title="Fit", height=430, min_width=250, sizing_mode="stretch_width", tools="pan,wheel_zoom,box_zoom,reset,save", x_axis_label="Input", y_axis_label="Target")
    residual_plot = figure(title="Residuals", height=280, min_width=250, sizing_mode="stretch_width", tools="pan,wheel_zoom,reset", x_axis_label="NN prediction", y_axis_label="Observed − predicted")
    loss_plot = figure(title="Training objective", height=250, min_width=250, sizing_mode="stretch_width", tools="pan,wheel_zoom,reset", x_axis_label="Iteration", y_axis_label="Objective")
    for group, color, marker in (("train", "#3567ad", "circle"), ("test", "#ce7132", "triangle")):
        plot.scatter("x", "y", source=observations, view=CDSView(filter=GroupFilter(column_name="split", group=group)), marker=marker, color=color, size=6, alpha=.62, legend_label=group.title())
        residual_plot.scatter("x", "residual", source=residuals, view=CDSView(filter=GroupFilter(column_name="split", group=group)), marker=marker, color=color, size=6, alpha=.62, legend_label=group.title())
    nn_renderer = plot.line("x", "y", source=nn_curve, color="#4168bd", line_width=3, legend_label="Neural network")
    eq_renderer = plot.line("x", "y", source=equation_curve, color="#c4547d", line_width=3, line_dash="dashed", legend_label="Equation")
    identity_renderer = plot.line("x", "y", source=identity_line, color="#5b6574", line_dash="dashed", legend_label="Identity", visible=False)
    loss_plot.line("iteration", "objective", source=loss, color="#4168bd", line_width=2)
    residual_plot.add_layout(Span(location=0, dimension="width", line_color="#677080", line_dash="dashed"))
    for fig in (plot, residual_plot):
        fig.legend.label_text_font_size = "9px"
        fig.legend.orientation = "horizontal"
        fig.legend.spacing = 8
        fig.legend.padding = 4
        fig.add_layout(fig.legend[0], "above")

    controls = [upload, target, features, hidden, activation, solver, alpha, rate, iterations, fraction, degree, seed]

    def config():
        return dict(hidden_layers=hidden.value, activation=activation.value, solver=solver.value, alpha=alpha.value, learning_rate=rate.value, max_iter=iterations.value, test_fraction=fraction.value, equation_degree=degree.value, seed=seed.value)

    def format_cell(value):
        try:
            number = float(value)
            return f"{number:.4f}" if np.isfinite(number) else str(value)
        except (TypeError, ValueError):
            return str(value)

    def update_preview():
        table = state["table"]
        cells = "<tr>" + "".join("<th>" + html.escape(name) + "</th>" for name in table.headers) + "</tr>"
        cells += "".join("<tr>" + "".join("<td>" + html.escape(format_cell(value)[:80]) + "</td>" for value in record) + "</tr>" for record in table.rows[:3])
        preview.text = f'<p class="preview-meta">{len(table.rows):,} raw rows · {len(table.headers)} columns · first 3 rows</p><table class="data-preview">{cells}</table>'
        file_chip.text = f'<span class="file-chip">{html.escape(state["filename"])}</span>'

    def pending(attr, old, new):
        rate.disabled = solver.value == "lbfgs" or state["job"] is not None
        if state["job"] is None:
            status.text = "Settings pending · click Train." if state["committed"] else "Ready · click Train."

    def uploaded(attr, old, new):
        if not new or state["job"] is not None:
            return
        try:
            if len(new) > 4 * ((MAX_BYTES + 2) // 3):
                raise ValueError("CSV exceeds the 5 MB decoded limit.")
            raw = base64.b64decode(new, validate=True)
            table = parse_csv(raw)
            text = raw.decode("utf-8-sig")
        except Exception as exc:
            status.text = "Upload rejected: " + html.escape(str(exc))
            return
        try:
            filename = upload.filename or "Uploaded CSV"
        except Exception:
            filename = "Uploaded CSV"
        state.update(csv=text, table=table, filename=filename)
        target.options = list(table.headers)
        features.options = list(table.headers)
        target.value = table.headers[-1]
        features.value = [table.headers[0]]
        clear_file.visible = True
        update_preview()
        status.text = f"Loaded {len(table.rows):,} rows · click Train."

    def clear_uploaded():
        if state["job"] is not None:
            return
        text = sample_csv()
        state.update(csv=text, table=parse_csv(text), filename="Built-in sample", committed=None)
        target.options = list(state["table"].headers)
        features.options = list(state["table"].headers)
        target.value = "target"
        features.value = ["x"]
        clear_file.visible = False
        update_preview()
        status.text = "Ready · built-in sample"

    def lock_controls(busy):
        for widget in controls:
            widget.disabled = busy
        train.disabled = busy
        rate.disabled = busy or solver.value == "lbfgs"

    def number(value):
        return "Unavailable" if value is None else f"{value:.5g}"

    def publish(result):
        one = len(result["features"]) == 1
        x = [record[0] for record in result["X"]] if one else result["y"]
        y = result["y"] if one else result["predictions"]
        markers = ["circle" if split == "train" else "triangle" for split in result["split"]]
        obs = dict(x=x, y=y, actual=result["y"], prediction=result["predictions"], split=result["split"], marker=markers)
        res = dict(x=result["predictions"], residual=result["residuals"], split=result["split"], marker=markers)
        fidelity = result["fidelity_r2"]
        fidelity_tone = "err" if fidelity is None or fidelity < .8 else ("warn" if fidelity < .95 else "ok")
        tiles = [
            ("NN test R²", number(result["test_r2"]), "ok", "Held-out neural network fit"),
            ("NN test RMSE", number(result["test_rmse"]), "ok", "Held-out error in target units"),
            ("Equation fidelity R²", number(fidelity), fidelity_tone, "Agreement between the displayed polynomial and neural network predictions"),
            ("Rows", f"{result['rows_used']} / {result['rows_dropped']}", "base", "Used / dropped"),
            ("Iterations", str(result["iterations"]), "base", "Neural network iterations"),
            ("Fit time", f"{result['fit_seconds']:.3f} s", "base", "Neural network fitting time"),
        ]
        metrics.text = " · ".join(f"{label}: {value}" for label, value, _tone, _tip in tiles)
        tone_colors = {"ok": "var(--ok)", "warn": "var(--warn)", "err": "var(--err)", "base": "#98a2b3"}
        for model, (label, value, tone, tip) in zip(kpi_models, tiles):
            model.text = f'<div class="kpi-tile" title="{html.escape(tip)}"><small>{html.escape(label)}</small><strong>{html.escape(value)}</strong></div>'
            model.styles = {
                "background": "var(--card)", "border": "1px solid var(--line)",
                "border-left": f"4px solid {tone_colors[tone]}", "border-radius": "10px",
                "padding": "11px 10px", "box-sizing": "border-box", "min-width": "0",
                "color": "var(--err)" if tone == "err" else "var(--ink)",
            }
        kpi_strip.visible = True
        rounded = _rounded_equation(result["coefficients"], result["powers"])
        mapping = " · ".join(f"x{i + 1} = {html.escape(name)}" for i, name in enumerate(result["features"]))
        equation.text = (
            f'<pre class="equation-line">{html.escape(rounded)}</pre>'
            f'<p class="equation-map">{mapping} · y = {html.escape(result["target"])}</p>'
            f'<div class="equation-chips"><span>rank {result["polynomial_rank"]}/{result["polynomial_terms"]}</span>'
            f'<span>condition {number(result["polynomial_condition"])}</span></div>'
        )
        copy_equation.tags = [rounded]
        doc.hold("combine")
        try:
            observations.data = obs
            residuals.data = res
            nn_curve.data = dict(x=result["curve_x"], y=result["curve_nn"])
            equation_curve.data = dict(x=result["curve_x"], y=result["curve_equation"])
            bounds = [float(min(result["y"] + result["predictions"])), float(max(result["y"] + result["predictions"]))]
            identity_line.data = dict(x=[] if one else bounds, y=[] if one else bounds)
            nn_renderer.visible = one
            eq_renderer.visible = one
            identity_renderer.visible = not one
            for item in plot.legend[0].items:
                item.visible = any(renderer.visible for renderer in item.renderers)
            plot.xaxis.axis_label = result["features"][0] if one else "Observed target"
            plot.yaxis.axis_label = result["target"] if one else "NN predicted target"
            loss.data = dict(iteration=list(range(1, len(result["loss"]) + 1)), objective=result["loss"])
            loss_card.visible = bool(result["loss"])
            state["committed"] = result
        finally:
            doc.unhold()

    def complete(generation, message):
        if state["closed"] or generation != state["generation"]:
            return
        state["job"] = None
        lock_controls(False)
        if not message.get("ok"):
            status.text = "Training failed: " + html.escape(message.get("error", "Unknown error"))
            return
        try:
            publish(message["result"])
        except Exception as exc:
            status.text = "Result publication failed: " + html.escape(str(exc))
            return
        result = message["result"]
        elapsed = time.perf_counter() - state["started"]
        status.text = (
            f'Complete <span class="status-badge ok">Complete</span>'
            f'<span class="status-chip">{result["rows_used"]} rows</span>'
            f'<span class="status-chip">{elapsed:.2f} s</span>'
        )
        has_warning = bool(result["warnings"])
        warning_button.visible = has_warning
        warning_hint.visible = False
        double_iterations.visible = False
        scale_features.visible = False
        warning_hint.text = ""

    def train_clicked():
        if state["job"] is not None:
            return
        try:
            prepare_data(state["table"], features.value, target.value)
            validated = validate_config(config(), len(features.value))
        except Exception as exc:
            status.text = "Check inputs: " + html.escape(str(exc))
            return
        state["generation"] += 1
        generation = state["generation"]
        state["started"] = time.perf_counter()
        status.text = "Training · 0.0 s elapsed"
        warning_button.visible = False
        lock_controls(True)
        payload = dict(csv=state["csv"], features=list(features.value), target=target.value, config=validated)

        def done(message):
            if not state["closed"]:
                doc.add_next_tick_callback(lambda: complete(generation, message))

        job = WorkerJob(payload, done)
        state["job"] = job
        job.start()

    def toggle_warning():
        visible = not warning_hint.visible
        warning_hint.visible = visible
        double_iterations.visible = visible
        scale_features.visible = visible
        warning_hint.text = "The optimizer stopped before convergence. Try more iterations; input features are already standardized during training."

    def double_max_iter():
        iterations.value = min(2000, int(iterations.value) * 2)
        status.text = "Settings pending · max_iter updated."

    def show_scaling_note():
        warning_hint.text = "Feature scaling is already enabled: training features and target are standardized from the training split."

    def tick():
        if state["job"] is not None:
            status.text = f"Training · {time.perf_counter() - state['started']:.1f} s elapsed"

    def destroyed(session_context):
        state["closed"] = True
        state["generation"] += 1
        if state["job"] is not None:
            state["job"].cancel()

    for widget in controls[1:]:
        widget.on_change("value", pending)
    upload.on_change("value", uploaded)
    train.on_click(train_clicked)
    clear_file.on_click(clear_uploaded)
    warning_button.on_click(toggle_warning)
    double_iterations.on_click(double_max_iter)
    scale_features.on_click(show_scaling_note)
    doc.on_session_destroyed(destroyed)
    doc.add_periodic_callback(tick, 500)
    update_preview()

    card_styles = {
        "background": "var(--card)", "border": "1px solid var(--line)", "border-radius": "12px",
        "padding": "15px", "box-sizing": "border-box", "min-width": "0", "color": "var(--ink)",
    }

    def card(*children, name=None):
        return column(*children, sizing_mode="stretch_width", min_width=0, styles=card_styles, name=name)

    def section(title, body, opened=True):
        toggle = Button(label=title + ("  ▾" if opened else "  ▸"), button_type="default", sizing_mode="stretch_width", height=38)
        body.visible = opened

        def switch():
            body.visible = not body.visible
            toggle.label = title + ("  ▾" if body.visible else "  ▸")

        toggle.on_click(switch)
        return column(toggle, body, sizing_mode="stretch_width", spacing=6)

    data_body = column(upload, row(file_chip, clear_file, sizing_mode="stretch_width"), target, features, preview, sizing_mode="stretch_width")
    model_body = column(hidden, activation, solver, degree, sizing_mode="stretch_width")
    advanced_body = column(alpha, rate, Div(text='<small class="field-note">Learning rate is disabled for L-BFGS.</small>', stylesheets=_content_stylesheet()), iterations, fraction, seed, sizing_mode="stretch_width")
    sidebar = card(section("Data", data_body), section("Model", model_body), section("Advanced", advanced_body, opened=False), train, name="module_sidebar")
    sidebar.styles.update(position="sticky", top="14px", align_self="start")

    title = Div(text='<div class="result-title"><span class="module-kicker">MODULE</span><h1>Neural Networks Equation Finding</h1></div>', sizing_mode="stretch_width", stylesheets=_content_stylesheet())
    status_bar = row(status, warning_button, sizing_mode="stretch_width", min_width=0)
    warning_actions = row(double_iterations, scale_features, sizing_mode="stretch_width")
    header_row = row(title, status_bar, sizing_mode="stretch_width", min_width=0, stylesheets=[InlineStyleSheet(css="""
        :host { display:grid !important; grid-template-columns:minmax(320px,1fr) auto !important; gap:16px; align-items:center; }
        @media (max-width:900px) { :host { grid-template-columns:minmax(0,1fr) !important; } }
    """)])
    result_header = column(header_row, warning_hint, warning_actions, sizing_mode="stretch_width")
    kpi_strip = row(*kpi_models, sizing_mode="stretch_width", min_width=0, visible=False, stylesheets=[InlineStyleSheet(css="""
        :host { display:grid !important; grid-template-columns:repeat(6,minmax(0,1fr)) !important; gap:9px; }
        @media (max-width:900px) { :host { grid-template-columns:repeat(2,minmax(0,1fr)) !important; } }
    """)])
    fit_card = card(plot)
    equation_header = row(Div(text="<h3>Equation</h3>", sizing_mode="stretch_width", stylesheets=_content_stylesheet()), copy_equation, sizing_mode="stretch_width")
    equation_card = card(equation_header, equation)
    residual_card = card(residual_plot)
    lower_grid = row(residual_card, equation_card, sizing_mode="stretch_width", min_width=0, stylesheets=[InlineStyleSheet(css="""
        :host { display:grid !important; grid-template-columns:minmax(0,1.15fr) minmax(300px,.85fr) !important; gap:14px; align-items:stretch; }
        @media (max-width:900px) { :host { grid-template-columns:minmax(0,1fr) !important; } }
    """)])
    loss_card = card(loss_plot)
    loss_card.visible = False
    results = column(result_header, metrics, kpi_strip, fit_card, lower_grid, loss_card, sizing_mode="stretch_width", min_width=0, spacing=14)
    shell = row(sidebar, results, sizing_mode="stretch_width", min_width=0, spacing=18, name="neural_dashboard", stylesheets=[InlineStyleSheet(css="""
        :host { display:grid !important; grid-template-columns:310px minmax(0,1fr) !important; gap:18px; align-items:start; }
        @media (max-width:900px) { :host { grid-template-columns:minmax(0,1fr) !important; } }
    """)])
    doc.add_root(shell)
    doc.title = "Neural Equation Finder"
