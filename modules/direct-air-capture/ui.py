"""Per-session Bokeh laboratory for the DAC packed-bed simulation."""
import html

import numpy as np
from bokeh.layouts import column
from bokeh.models import Button, ColumnDataSource, Div, HoverTool, InlineStyleSheet, LinearAxis, Range1d, Select, Slider
from bokeh.plotting import figure

from .engine import SimulationConfig, WALLS, validate_config
from .worker import WorkerJob

CARD_CSS = """
:host{color:var(--ink);min-width:0}.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;box-sizing:border-box}
.process{font-size:15px;line-height:1.55}.flow{font-weight:750;color:var(--blue);letter-spacing:.2px}.muted{color:var(--muted);font-size:12px}
.status{border-left:4px solid var(--blue);background:var(--soft);border-radius:9px;padding:10px 12px}.status.ok{border-left-color:var(--ok)}.status.err{border-left-color:var(--err)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(125px,1fr));gap:8px}.kpi{border:1px solid var(--line);border-left:4px solid #8ba1b8;border-radius:10px;padding:9px;background:var(--card)}.kpi small{display:block;color:var(--muted)}.kpi strong{display:block;font-size:19px;margin-top:2px}.details{line-height:1.55;font-size:13px}.details code{background:var(--soft);padding:2px 4px;border-radius:4px}.warn{color:var(--warn);font-weight:700}
@media(max-width:600px){.kpis{grid-template-columns:repeat(2,minmax(0,1fr))}}
"""


def _div(text="", name=None):
    return Div(text=text, name=name, sizing_mode="stretch_width", stylesheets=[InlineStyleSheet(css=CARD_CSS)])


def build_document(doc):
    defaults = SimulationConfig()
    state = {"job": None, "generation": 0, "closed": False, "result": None, "committed": None}
    common = dict(sizing_mode="stretch_width", min_width=0)
    volume = Slider(title="Reactor volume (L)", start=.2, end=2.0, step=.1, value=.5, name="volume_l", **common)
    inlet = Slider(title="Inlet / initial CO₂ (ppm)", start=300, end=2000, step=10, value=420, name="inlet_ppm", **common)
    temperature = Slider(title="Initial & wall temperature (°C)", start=5, end=40, step=1, value=25, name="initial_temperature_c", **common)
    flow = Slider(title="Volumetric air flow (L min⁻¹)", start=10, end=100, step=5, value=50, name="flow_l_min", **common)
    porosity = Slider(title="Bed porosity ε (gas fraction)", start=.30, end=.55, step=.01, value=.40, name="porosity", **common)
    wall = Select(title="Wall / effective cooling", value="stainless", options=[
        ("polymer", "Polymer-lined · low cooling (8 W m⁻² K⁻¹)"),
        ("stainless", "Stainless steel · moderate (25 W m⁻² K⁻¹)"),
        ("aluminum", "Aluminum · strong cooling (45 W m⁻² K⁻¹)"),
    ], name="wall_material", **common)
    run = Button(label="▶ Run 24-hour adsorption", button_type="primary", height=44, name="run_simulation", **common)
    reset = Button(label="Reset defaults", button_type="default", height=38, name="reset_simulation", **common)
    selected = Slider(title="Selected profile time (h)", start=0, end=24, step=.2, value=24, disabled=True, name="selected_time", **common)
    status = _div('<div class="status">Ready · choose conditions, predict, then Run.</div>', "status")
    process = _div('''<div class="card process"><span class="flow">Ambient air → amine sorbent bed → CO₂-depleted outlet</span><br>
        Captured CO₂ accumulates as solid loading <i>q</i>; adsorption releases heat while the wall moderates temperature.
        <span class="muted">Adsorption phase only: regeneration, compression, storage, humidity and pressure drop are outside this model.</span></div>''')
    derived = _div(name="derived_values")
    metrics = _div('<div class="card"><b>Results appear after Run.</b></div>', "metrics")
    interpretation = _div('<div class="card"><b>Predict:</b> Will the outlet start below 420 ppm? Where will the bed warm first? Will capture stay high forever?</div>', "interpretation")
    details = _div('''<div class="card details"><b>Model details & provenance</b><p>
        Finite-volume, 1-D dry-air plug flow; 30 cells; 24 h; SciPy BDF. The source equation is implemented as
        <code>dq/dt = k(T)[P(1−(q/qₛ)^tʰ)^(1/tʰ) − q/(b(T)qₛ)]</code>, coupled to gas mass and packed-bed energy balances.
        Toth shape/thermodynamic parameters follow Bos et al. (DOI 10.1016/j.cej.2018.11.072); the ambient-pressure kinetic scale is a pedagogical calibration, not a fitted DAC material. Wall names select assumed overall coefficients. Closure checks numerical accounting, not experimental validity.</p>
        <p class="muted">SI internally · first-order upwind flux · no dispersion, radial gradients, humidity, pressure drop, degradation or regeneration.</p></div>''', "model_details")

    time_source = ColumnDataSource(dict(time_h=[], outlet_ppm=[], inlet_ppm=[], capture_pct=[], uptake_g=[]), name="time_source")
    profile_source = ColumnDataSource(dict(z_m=[], co2_ppm=[], loading_pct=[], temperature_c=[], rate_mmol_kg_min=[]), name="profile_source")
    outlet_plot = figure(title="Outlet breakthrough", height=310, min_width=260, sizing_mode="stretch_width", x_axis_label="Time (h)", y_axis_label="CO₂ (ppm)", tools="pan,wheel_zoom,box_zoom,reset,save")
    outlet_plot.line("time_h", "inlet_ppm", source=time_source, line_dash="dashed", color="#7b8794", legend_label="Inlet")
    outlet_plot.line("time_h", "outlet_ppm", source=time_source, line_width=3, color="#1f77b4", legend_label="Outlet")
    outlet_plot.add_tools(HoverTool(tooltips=[("Time", "@time_h{0.00} h"),("Outlet", "@outlet_ppm{0.0} ppm")]))
    performance_plot = figure(title="Capture and cumulative uptake", height=310, min_width=260, sizing_mode="stretch_width", x_axis_label="Time (h)", y_axis_label="Capture fraction (%)", tools="pan,wheel_zoom,reset,save")
    performance_plot.extra_y_ranges = {"uptake": Range1d(start=0, end=1)}
    performance_plot.add_layout(LinearAxis(y_range_name="uptake", axis_label="Uptake (g CO₂)"), "right")
    performance_plot.line("time_h", "capture_pct", source=time_source, line_width=3, color="#2d8a61", legend_label="Capture")
    performance_plot.line("time_h", "uptake_g", source=time_source, line_width=2, color="#d07a32", y_range_name="uptake", legend_label="Uptake")
    performance_plot.add_tools(HoverTool(tooltips=[("Time", "@time_h{0.00} h"),("Capture", "@capture_pct{0.0}%"),("Uptake", "@uptake_g{0.000} g")]))

    def profile_plot(title, field, ylabel, color):
        plot = figure(title=title, height=285, min_width=260, sizing_mode="stretch_width", x_axis_label="Axial position z (m)", y_axis_label=ylabel, tools="pan,wheel_zoom,reset,save")
        plot.line("z_m", field, source=profile_source, line_width=3, color=color)
        plot.scatter("z_m", field, source=profile_source, size=4, color=color, alpha=.55)
        plot.add_tools(HoverTool(tooltips=[("z", "@z_m{0.000} m"),(ylabel, f"@{field}{{0.000}}")]))
        return plot
    co2_plot = profile_plot("Gas CO₂ profile", "co2_ppm", "CO₂ (ppm)", "#1f77b4")
    loading_plot = profile_plot("Sorbent loading", "loading_pct", "Loading (% qₛ)", "#7f5aa2")
    temp_plot = profile_plot("Bed temperature", "temperature_c", "Temperature (°C)", "#c4553c")
    rate_plot = profile_plot("Local adsorption rate", "rate_mmol_kg_min", "Rate (mmol kg⁻¹ min⁻¹)", "#2d8a61")

    inputs = [volume, inlet, temperature, flow, porosity, wall]
    def config():
        return validate_config(dict(volume_m3=volume.value*1e-3, inlet_ppm=inlet.value,
            initial_temperature_k=temperature.value+273.15, flow_m3_s=flow.value/60000,
            porosity=porosity.value, wall_key=wall.value))
    def update_derived():
        try:
            cfg = config(); length=cfg.volume_m3/.001; velocity=cfg.flow_m3_s/.001; tau=cfg.porosity*cfg.volume_m3/cfg.flow_m3_s
            derived.text = f'''<div class="card"><b>Derived model settings</b><p>Bed length <b>{length:.2f} m</b> · superficial velocity <b>{velocity:.2f} m s⁻¹</b> · gas residence time <b>{tau:.3f} s</b></p><p>Assumed effective wall coefficient <b>{WALLS[cfg.wall_key]:g} W m⁻² K⁻¹</b> · 30 cells · 24 h</p><p class="muted">Wall material is a scenario label for this coefficient, not a universal material property.</p></div>'''
        except Exception as exc: derived.text = f'<div class="card warn">{html.escape(str(exc))}</div>'
    def set_busy(busy):
        for widget in inputs + [run, reset]: widget.disabled = busy
        selected.disabled = busy or state["result"] is None
    def update_profile(index=None):
        result = state["result"]
        if result is None: return
        times = np.asarray(result["time_s"])/3600
        index = int(np.argmin(np.abs(times-selected.value))) if index is None else index
        selected.value = float(times[index])
        profile_source.data = dict(z_m=result["z_m"], co2_ppm=result["concentration_ppm"][index],
            loading_pct=(np.asarray(result["loading_fraction"][index])*100).tolist(),
            temperature_c=(np.asarray(result["temperature_k"][index])-273.15).tolist(),
            rate_mmol_kg_min=(np.asarray(result["rate_mol_kg_s"][index])*60000).tolist())
        interpretation.text = f'''<div class="card"><b>Read this run at {times[index]:.1f} h.</b> The outlet is <b>{result["outlet_ppm"][index]:.1f} ppm</b>, instantaneous capture is <b>{100*result["capture_fraction"][index]:.1f}%</b>, and cumulative uptake is <b>{result["uptake_g_co2"][index]:.3f} g CO₂</b>. Follow the loading/rate front rather than treating breakthrough as instant whole-bed saturation.</div>'''
    def publish(result):
        state["result"] = result; state["committed"] = result["config"]
        time_h = (np.asarray(result["time_s"])/3600).tolist()
        time_source.data = dict(time_h=time_h, outlet_ppm=result["outlet_ppm"], inlet_ppm=[result["config"]["inlet_ppm"]]*len(time_h), capture_pct=(100*np.asarray(result["capture_fraction"])).tolist(), uptake_g=result["uptake_g_co2"])
        performance_plot.extra_y_ranges["uptake"].start = 0
        performance_plot.extra_y_ranges["uptake"].end = max(result["uptake_g_co2"])*1.08 or 1
        selected.start=0; selected.end=time_h[-1]; selected.step=time_h[-1]/(len(time_h)-1); selected.value=time_h[-1]; selected.disabled=False
        update_profile(len(time_h)-1)
        worker = result.get("worker_seconds", result["solver_seconds"])
        values=[("Outlet",f'{result["final_outlet_ppm"]:.1f} ppm'),("Capture",f'{100*result["final_capture_fraction"]:.1f}%'),("Uptake",f'{result["final_uptake_g_co2"]:.3f} g'),("Peak T",f'{result["peak_temperature_k"]-273.15:.2f} °C'),("Peak rate",f'{result["peak_rate_mol_kg_s"]*60000:.2f} mmol kg⁻¹ min⁻¹'),("Closure",f'{result["mass_residual_percent"][-1]:.3g}%'),("Runtime",f'{worker:.3f} s')]
        metrics.text='<div class="card"><div class="kpis">'+''.join(f'<div class="kpi"><small>{a}</small><strong>{b}</strong></div>' for a,b in values)+'</div><p class="muted">Closure is a numerical accounting check; it is not experimental validation.</p></div>'
    def completed(generation, message):
        if state["closed"] or generation != state["generation"]: return
        state["job"] = None; set_busy(False)
        if not message.get("ok"):
            status.text=f'<div class="status err">Simulation failed: {html.escape(message.get("error","Unknown error"))}</div>'; return
        try:
            doc.hold("combine"); publish(message["result"])
        finally: doc.unhold()
        status.text=f'<div class="status ok">Complete · committed 24-hour run · {message["result"].get("worker_seconds",0):.3f} s end to end.</div>'
    def run_clicked():
        if state["job"] is not None: return
        try: cfg=config()
        except Exception as exc:
            status.text=f'<div class="status err">Input error: {html.escape(str(exc))}</div>'; return
        state["generation"] += 1; generation=state["generation"]; set_busy(True)
        status.text='<div class="status">Simulating 30 cells over 24 hours…</div>'
        def done(message):
            if not state["closed"]: doc.add_next_tick_callback(lambda: completed(generation,message))
        state["job"] = WorkerJob(dict(config=cfg.__dict__), done).start()
    def pending(attr, old, new):
        update_derived()
        if state["result"] is not None and state["job"] is None:
            status.text='<div class="status">Settings pending — plots show the previous committed run.</div>'
    def reset_clicked():
        if state["job"] is not None: state["job"].cancel(); state["job"] = None
        state["generation"] += 1
        volume.value=.5; inlet.value=420; temperature.value=25; flow.value=50; porosity.value=.40; wall.value="stainless"
        state["result"]=None; state["committed"]=None; time_source.data={k:[] for k in time_source.data}; profile_source.data={k:[] for k in profile_source.data}
        selected.value=24; selected.disabled=True; metrics.text='<div class="card"><b>Results appear after Run.</b></div>'; interpretation.text='<div class="card"><b>Predict:</b> Will the outlet start below 420 ppm? Where will the bed warm first? Will capture stay high forever?</div>'; set_busy(False); update_derived(); status.text='<div class="status">Defaults restored · predict, then Run.</div>'
    for widget in inputs: widget.on_change("value", pending)
    selected.on_change("value", lambda attr,old,new: update_profile() if state["result"] is not None else None)
    run.on_click(run_clicked); reset.on_click(reset_clicked)
    def closed(_context):
        state["closed"]=True
        if state["job"] is not None: state["job"].cancel()
    doc.on_session_destroyed(closed)
    update_derived()
    controls=column(*inputs,run,reset,sizing_mode="stretch_width",min_width=0)
    # Bokeh's layout engine computes row height before CSS media-query reflow. A
    # CSS-stacked Row can therefore paint over the next widget on narrow screens.
    # Native Columns keep layout geometry and hit targets consistent at every width.
    top=column(controls,derived,name="controls_and_settings",sizing_mode="stretch_width",min_width=0)
    times=column(outlet_plot,performance_plot,name="time_plots",sizing_mode="stretch_width",min_width=0)
    profiles=column(co2_plot,loading_plot,temp_plot,rate_plot,name="profile_plots",sizing_mode="stretch_width",min_width=0)
    doc.add_root(column(process,status,top,metrics,times,selected,profiles,interpretation,details,sizing_mode="stretch_width",min_width=0))
    doc.title="Direct Air Capture Packed-Bed Lab"
