"""Runnable example to adapt to a new learning brief."""

from bokeh.layouts import column
from bokeh.models import ColumnDataSource, Slider
from bokeh.plotting import figure

from .engine import evaluate


def build_document(doc):
    coefficient = Slider(title="Coefficient (dimensionless)", start=-5, end=5, value=1, step=.1, name="coefficient", sizing_mode="stretch_width")
    source = ColumnDataSource(evaluate(1), name="exploration")
    plot = figure(height=360, sizing_mode="stretch_width", min_width=260, x_axis_label="x (dimensionless)", y_axis_label="y (dimensionless)", title="Explore y = a × x")
    plot.line("x", "y", source=source, line_width=3, color="#087f8c")
    coefficient.on_change("value", lambda attr, old, new: setattr(source, "data", evaluate(new)))
    doc.add_root(column(coefficient, plot, sizing_mode="stretch_width"))
