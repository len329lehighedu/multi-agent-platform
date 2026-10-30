"""Bokeh document factory; every model and callback belongs to one session."""
from html import escape
from bokeh.layouts import column
from bokeh.models import ColumnDataSource, Div, HoverTool, Range1d, Slider
from bokeh.plotting import figure
from .engine import trajectory


def build_document(doc):
    """Populate a Bokeh Document without launching any services."""
    speed = Slider(name="speed", title="Initial speed (m/s)", start=0, end=50,
                   step=1, value=20, sizing_mode="stretch_width", min_width=280)
    angle = Slider(name="angle", title="Launch angle (degrees from horizontal)",
                   start=0, end=90, step=1, value=45,
                   sizing_mode="stretch_width", min_width=280)
    source = ColumnDataSource(name="trajectory", data=dict(t=[], x=[], y=[]))
    metrics = Div(name="metrics", sizing_mode="stretch_width")
    status = Div(name="status", sizing_mode="stretch_width")
    plot = figure(name="trajectory_plot", title="Flight from launch to landing",
                  x_axis_label="Horizontal position x (m)", y_axis_label="Height y (m)",
                  sizing_mode="stretch_width", min_width=280, height=350,
                  x_range=Range1d(0, 50), y_range=Range1d(0, 15),
                  tools="pan,wheel_zoom,reset,save", active_scroll=None)
    line = plot.line("x", "y", source=source, line_width=3, color="#155e75")
    plot.scatter("x", "y", source=source, size=3, alpha=0.25, color="#155e75")
    plot.add_tools(HoverTool(renderers=[line], tooltips=[
        ("Time (s)", "@t{0.000}"), ("x (m)", "@x{0.000}"), ("y (m)", "@y{0.000}")]))

    def update(attr, old, new):
        try:
            result = trajectory(speed.value, angle.value)
        except ValueError as error:
            status.text = f"<p role='alert'>Choose valid controls: {escape(str(error))}</p>"
            return
        source.data = dict(t=result.time, x=result.x, y=result.y)
        metrics.text = (
            f"<p><b>Flight time:</b> {result.flight_time:.3f} s &nbsp; "
            f"<b>Range:</b> {result.range:.3f} m &nbsp; "
            f"<b>Maximum height:</b> {result.max_height:.3f} m</p>")
        status.text = ("<p>Zero-duration flight: with no upward launch velocity, landing is immediate.</p>"
                       if result.flight_time == 0 else
                       "<p>Change either control to update the flight. Hover over the curve for sampled positions.</p>")
        plot.x_range.end = max(1.0, result.range * 1.08)
        plot.y_range.end = max(1.0, result.max_height * 1.15)
        plot.x_range.reset_end = plot.x_range.end
        plot.y_range.reset_end = plot.y_range.end

    speed.on_change("value", update)
    angle.on_change("value", update)
    update(None, None, None)
    doc.add_root(column(
        Div(text="<h2>Explore the flight</h2><p>Predict first: what will change if you double the speed at the same angle?</p>",
            sizing_mode="stretch_width"),
        speed, angle, metrics, status, plot,
        Div(text="<p>The axes use meters but their screen scales can differ. Compare the labeled values when judging distance and height.</p>",
            sizing_mode="stretch_width"),
        sizing_mode="stretch_width", min_width=280, name="projectile_workspace"))
    doc.title = "Projectile motion"
