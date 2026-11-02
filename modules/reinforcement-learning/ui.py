"""Bokeh lesson UI for the deterministic Gridworld."""

import html
import time

import numpy as np
from bokeh.layouts import column, row
from bokeh.models import Button, ColumnDataSource, Div, HoverTool, InlineStyleSheet, Slider, Spinner
from bokeh.plotting import figure

from .engine import (
    ACTION_ARROWS,
    ACTION_NAMES,
    GOAL_STATE,
    HAZARD_STATE,
    MAX_STEPS,
    START_STATE,
    apply_q_update,
    choose_training_action,
    evaluate_greedy,
    greedy_action,
    new_q_table,
    train_episodes,
    transition,
)


CARD = {
    "background": "#ffffff",
    "border": "1px solid #dfe3ea",
    "border-radius": "10px",
    "padding": "13px",
    "box-sizing": "border-box",
    "min-width": "0",
}


def build_document(doc):
    """Create one complete, isolated learner session in ``doc``."""
    alpha = Slider(title="Learning rate α", start=0, end=1, value=.3, step=.05, name="alpha", sizing_mode="stretch_width")
    gamma = Slider(title="Future weight γ", start=0, end=1, value=.95, step=.05, name="gamma", sizing_mode="stretch_width")
    epsilon = Slider(title="Exploration ε", start=0, end=1, value=.2, step=.05, name="epsilon", sizing_mode="stretch_width")
    episodes = Spinner(title="Episodes (1–500)", low=1, high=500, value=100, step=1, name="episodes", sizing_mode="stretch_width")
    seed = Spinner(title="Seed (applies after reset)", low=0, high=4_294_967_295, value=42, step=1, name="seed", sizing_mode="stretch_width")
    step_button = Button(label="Step one transition", button_type="primary", name="step_training", sizing_mode="stretch_width")
    train_button = Button(label="Train episodes", button_type="success", name="train_episodes", sizing_mode="stretch_width")
    reset_button = Button(label="Reset Q", name="reset_q", sizing_mode="stretch_width")

    state = {
        "q": new_q_table(),
        "rng": np.random.default_rng(42),
        "applied_seed": 42,
        "current_state": START_STATE,
        "steps": 0,
        "episode_return": 0.0,
        "episode": 1,
        "history": [],
        "last_update": None,
        "last_choice": None,
        "done": False,
        "busy": False,
    }

    board_source = ColumnDataSource(name="board_source")
    curve_source = ColumnDataSource(data=dict(episode=[], episode_return=[]), name="episode_curve_source")
    status = Div(name="status", sizing_mode="stretch_width")
    q_values = Div(name="q_values", sizing_mode="stretch_width", styles=CARD)
    last_update = Div(name="last_update", sizing_mode="stretch_width", styles=CARD)
    outcomes = Div(name="outcomes", sizing_mode="stretch_width", styles=CARD)
    evaluation = Div(name="evaluation", sizing_mode="stretch_width", styles=CARD)

    board = figure(
        height=430,
        sizing_mode="stretch_width",
        min_width=300,
        x_range=(-.5, 3.5),
        y_range=(3.5, -.5),
        tools="",
        toolbar_location=None,
        title="Current state and greedy policy",
        name="gridworld_board",
        match_aspect=True,
    )
    board.rect("x", "y", width=.94, height=.94, source=board_source, fill_color="color", line_color="outline", line_width=3)
    board.text("x", "y", text="cell_label", source=board_source, text_align="center", text_baseline="middle", text_font_size="14px", text_font_style="bold")
    board.text("x", "policy_y", text="policy", source=board_source, text_align="center", text_baseline="middle", text_font_size="21px", text_color="#2f6fed")
    board.text("x", "value_y", text="value_label", source=board_source, text_align="center", text_baseline="middle", text_font_size="10px", text_color="#475467")
    board.add_tools(HoverTool(tooltips=[
        ("State", "@state"), ("Up", "@q_up{0.000}"), ("Right", "@q_right{0.000}"),
        ("Down", "@q_down{0.000}"), ("Left", "@q_left{0.000}"),
    ]))
    board.axis.visible = False
    board.grid.visible = False

    curve = figure(height=255, sizing_mode="stretch_width", min_width=300, title="Training episode returns", x_axis_label="Completed episode", y_axis_label="Episode return", tools="", toolbar_location=None, name="return_curve")
    curve.line("episode", "episode_return", source=curve_source, line_width=2, color="#2f6fed")
    curve.scatter("episode", "episode_return", source=curve_source, size=4, color="#2f6fed")

    def begin_fresh_episode():
        state.update(current_state=START_STATE, steps=0, episode_return=0.0, done=False)

    def append_summary(total, steps, outcome):
        state["history"].append({"episode_return": float(total), "steps": int(steps), "outcome": outcome})
        state["episode"] = len(state["history"]) + 1

    def board_data():
        data = {key: [] for key in ("x", "y", "policy_y", "value_y", "state", "cell_label", "color", "outline", "policy", "value_label", "q_up", "q_right", "q_down", "q_left")}
        for cell in range(16):
            r, c = divmod(cell, 4)
            base = "G" if cell == GOAL_STATE else ("H" if cell == HAZARD_STATE else ("S" if cell == START_STATE else ""))
            label = ("A · " + base).rstrip(" ·") if cell == state["current_state"] else base
            terminal = cell in (GOAL_STATE, HAZARD_STATE)
            action = None if terminal else greedy_action(state["q"], cell)
            values = state["q"][cell]
            data["x"].append(c); data["y"].append(r)
            data["policy_y"].append(r - .12); data["value_y"].append(r + .28)
            data["state"].append(cell); data["cell_label"].append(label)
            data["color"].append("#d1fadf" if cell == GOAL_STATE else ("#fee4e2" if cell == HAZARD_STATE else ("#eaf0ff" if cell == START_STATE else "#f8fafc")))
            data["outline"].append("#2f6fed" if cell == state["current_state"] else "#d0d5dd")
            data["policy"].append("" if terminal else ACTION_ARROWS[action])
            data["value_label"].append("terminal" if terminal else f"max Q {values[action]:.2f}")
            for key, value in zip(("q_up", "q_right", "q_down", "q_left"), values):
                data[key].append(float(value))
        return data

    def update_text(status_message=None):
        current = state["current_state"]
        values = state["q"][current]
        q_values.text = (
            f"<h3>Action values at state {current}</h3>"
            + "".join(f"<div><b>{arrow} {name.title()}</b>: {value:.3f}</div>" for arrow, name, value in zip(ACTION_ARROWS, ACTION_NAMES, values))
            + "<p style='color:#667085;font-size:12px'>Q estimates cumulative future reward; it is not the immediate reward.</p>"
        )
        record = state["last_update"]
        choice = state["last_choice"]
        if record is None:
            last_update.text = "<h3>Last Q update</h3><p>Step once to inspect state → action → reward → next state.</p><code>Q ← Q + α [reward + γ × future − Q]</code>"
        else:
            item = record.transition
            mode = "exploratory" if choice and choice.exploratory else "greedy among current ties/values"
            terminal_note = " Future is 0 because the next state is terminal." if item.terminated else ""
            last_update.text = (
                "<h3>Last Q update</h3>"
                f"<p><b>State {item.state}</b> → {html.escape(ACTION_NAMES[item.action])} ({mode}) → reward {item.reward:+.2f} → <b>state {item.next_state}</b>.</p>"
                f"<p>old Q {record.old_q:.3f} · future {record.future:.3f} · target {record.target:.3f} · TD error {record.td_error:.3f} · <b>new Q {record.new_q:.3f}</b>.</p>"
                f"<p>{terminal_note}</p>"
            )
        counts = {name: sum(item["outcome"] == name for item in state["history"]) for name in ("goal", "hazard", "truncated")}
        outcomes.text = f"<h3>Training outcomes</h3><p>{len(state['history'])} completed · goal {counts['goal']} · hazard {counts['hazard']} · truncated {counts['truncated']}</p>"
        result = evaluate_greedy(state["q"], 100)
        evaluation.text = (
            "<h3>Frozen greedy evaluation</h3>"
            f"<p><b>{result['success_rate']:.0%} goal rate</b> over 100 episodes · goal {result['goal']} · hazard {result['hazard']} · truncated {result['truncated']}.</p>"
            "<p style='color:#667085;font-size:12px'>Exploration is off and Q is not updated. Repeated outcomes are stronger evidence than one successful training episode.</p>"
        )
        if status_message is not None:
            status.text = status_message

    def publish(status_message=None):
        doc.hold("combine")
        try:
            board_source.data = board_data()
            curve_source.data = {
                "episode": list(range(1, len(state["history"]) + 1)),
                "episode_return": [item["episode_return"] for item in state["history"]],
            }
            update_text(status_message)
        finally:
            doc.unhold()

    controls = (step_button, train_button, reset_button, alpha, gamma, epsilon, episodes, seed)

    def lock(busy):
        state["busy"] = busy
        for widget in controls:
            widget.disabled = busy

    def step_clicked():
        if state["busy"]:
            return
        lock(True)
        try:
            if state["done"]:
                begin_fresh_episode()
            choice = choose_training_action(state["q"], state["current_state"], epsilon.value, state["rng"])
            item = transition(state["current_state"], choice.action, state["steps"])
            record = apply_q_update(state["q"], item, alpha.value, gamma.value)
            state["last_choice"] = choice
            state["last_update"] = record
            state["current_state"] = item.next_state
            state["steps"] = item.steps_taken
            state["episode_return"] += item.reward
            state["done"] = item.terminated or item.truncated
            mode = "exploratory" if choice.exploratory else "greedy/tie choice"
            message = f"Episode {state['episode']} · step {item.steps_taken}/{MAX_STEPS} · {mode} {ACTION_NAMES[item.action]} · reward {item.reward:+.2f}."
            if state["done"]:
                outcome = "goal" if item.next_state == GOAL_STATE else ("hazard" if item.next_state == HAZARD_STATE else "truncated")
                append_summary(state["episode_return"], item.steps_taken, outcome)
                message += f" Episode ended: {outcome}. The next step starts a new episode and keeps Q."
            publish(message)
        except Exception as exc:
            status.text = "Step failed: " + html.escape(str(exc))
        finally:
            lock(False)

    def train_clicked():
        if state["busy"]:
            return
        lock(True)
        started = time.perf_counter()
        try:
            count = int(episodes.value)
            summaries = train_episodes(state["q"], state["rng"], count, alpha.value, gamma.value, epsilon.value)
            for item in summaries:
                append_summary(item.episode_return, item.steps, item.outcome)
            begin_fresh_episode()
            elapsed = time.perf_counter() - started
            publish(f"Trained {count} complete episodes in {elapsed:.3f} s. Q was retained; the board is at a fresh start.")
        except Exception as exc:
            status.text = "Training failed: " + html.escape(str(exc))
        finally:
            lock(False)

    def reset_clicked():
        if state["busy"]:
            return
        try:
            chosen_seed = int(seed.value)
            if chosen_seed < 0 or chosen_seed > 4_294_967_295 or chosen_seed != seed.value:
                raise ValueError("seed must be a nonnegative integer up to 4294967295")
            state.update(
                q=new_q_table(), rng=np.random.default_rng(chosen_seed), applied_seed=chosen_seed,
                current_state=START_STATE, steps=0, episode_return=0.0, episode=1,
                history=[], last_update=None, last_choice=None, done=False,
            )
            publish(f"Reset complete · zero Q table · history cleared · seed {chosen_seed} applied.")
        except Exception as exc:
            status.text = "Reset failed: " + html.escape(str(exc))

    def settings_changed(attr, old, new):
        if not state["busy"]:
            seed_note = " Seed applies only after Reset Q." if attr == "value" and seed.value != state["applied_seed"] else ""
            status.text = "Settings changed. Reset before comparing runs under controlled conditions." + seed_note

    step_button.on_click(step_clicked)
    train_button.on_click(train_clicked)
    reset_button.on_click(reset_clicked)
    for widget in (alpha, gamma, epsilon, episodes, seed):
        widget.on_change("value", settings_changed)

    controls_card = column(
        Div(text="<h3>Train the agent</h3><p style='color:#667085'>Try one transition first, then train a small batch.</p>"),
        step_button, train_button, reset_button, alpha, gamma, epsilon, episodes, seed,
        sizing_mode="stretch_width", min_width=240, styles=CARD, name="rl_controls",
    )
    board_card = column(board, sizing_mode="stretch_width", min_width=300, styles=CARD)
    responsive_grid = InlineStyleSheet(css="""
        :host { display:grid !important; grid-template-columns:260px minmax(320px,1.25fr) minmax(240px,.75fr) !important; gap:12px; align-items:start; }
        @media (max-width:900px) { :host { grid-template-columns:minmax(0,1fr) !important; } }
    """)
    two_column = InlineStyleSheet(css="""
        :host { display:grid !important; grid-template-columns:repeat(2,minmax(0,1fr)) !important; gap:12px; }
        @media (max-width:900px) { :host { grid-template-columns:minmax(0,1fr) !important; } }
    """)
    top = row(controls_card, board_card, q_values, sizing_mode="stretch_width", min_width=0, stylesheets=[responsive_grid])
    lower = row(last_update, evaluation, sizing_mode="stretch_width", min_width=0, stylesheets=[two_column])
    explanation = Div(text=(
        "<p><b>Read the loop:</b> the agent sees a state, chooses an action, receives one reward, reaches the next state, then updates one Q value. "
        "α controls update size, γ weighs estimated future value, and ε controls random training actions. The world itself stays deterministic.</p>"
    ), sizing_mode="stretch_width")
    shell = column(explanation, status, top, outcomes, curve, lower, sizing_mode="stretch_width", min_width=0, name="rl_gridworld_lab")
    doc.add_root(shell)
    doc.title = "RL Gridworld Lab"
    publish("Ready · seed 42 · zero Q table. Predict a move, then step once.")
