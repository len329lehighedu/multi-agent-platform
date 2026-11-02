"""Deterministic 4x4 Gridworld and tabular Q-learning primitives."""

from dataclasses import dataclass
import math

import numpy as np


ROWS = COLS = 4
N_STATES = 16
N_ACTIONS = 4
START_STATE = 12
GOAL_STATE = 3
HAZARD_STATE = 10
MAX_STEPS = 40
ACTION_NAMES = ("up", "right", "down", "left")
ACTION_ARROWS = ("↑", "→", "↓", "←")
ACTION_DELTAS = ((-1, 0), (0, 1), (1, 0), (0, -1))


@dataclass(frozen=True)
class Transition:
    state: int
    action: int
    next_state: int
    reward: float
    terminated: bool
    truncated: bool
    steps_taken: int


@dataclass(frozen=True)
class ActionChoice:
    action: int
    exploratory: bool


@dataclass(frozen=True)
class UpdateRecord:
    transition: Transition
    old_q: float
    future: float
    target: float
    td_error: float
    new_q: float


@dataclass(frozen=True)
class EpisodeSummary:
    episode_return: float
    steps: int
    outcome: str


def new_q_table():
    return np.zeros((N_STATES, N_ACTIONS), dtype=np.float64)


def _validate_state(state, *, allow_terminal=True):
    if isinstance(state, (bool, np.bool_)) or not isinstance(state, (int, np.integer)) or not 0 <= int(state) < N_STATES:
        raise ValueError("state must be an integer from 0 to 15")
    if not allow_terminal and state in (GOAL_STATE, HAZARD_STATE):
        raise ValueError("cannot step from a terminal state")
    return int(state)


def _validate_action(action):
    if isinstance(action, (bool, np.bool_)) or not isinstance(action, (int, np.integer)) or not 0 <= int(action) < N_ACTIONS:
        raise ValueError("action must be an integer from 0 to 3")
    return int(action)


def _validate_q(q):
    if not isinstance(q, np.ndarray) or q.shape != (N_STATES, N_ACTIONS) or not np.issubdtype(q.dtype, np.floating):
        raise ValueError("Q must be a floating NumPy array with shape (16, 4)")
    if not np.all(np.isfinite(q)):
        raise ValueError("Q values must be finite")
    return q


def _unit_interval(name, value):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, float, np.number)) or not math.isfinite(float(value)) or not 0 <= float(value) <= 1:
        raise ValueError(f"{name} must be finite and between 0 and 1")
    return float(value)


def _episode_count(episodes):
    if isinstance(episodes, (bool, np.bool_)) or not isinstance(episodes, (int, np.integer)) or not 1 <= int(episodes) <= 500:
        raise ValueError("episodes must be an integer from 1 to 500")
    return int(episodes)


def transition(state, action, steps_taken):
    """Apply one deterministic action; ``steps_taken`` is before this action."""
    state = _validate_state(state, allow_terminal=False)
    action = _validate_action(action)
    if isinstance(steps_taken, (bool, np.bool_)) or not isinstance(steps_taken, (int, np.integer)) or not 0 <= int(steps_taken) < MAX_STEPS:
        raise ValueError("steps_taken must be an integer from 0 to 39")
    row, col = divmod(state, COLS)
    dr, dc = ACTION_DELTAS[action]
    next_row = min(ROWS - 1, max(0, row + dr))
    next_col = min(COLS - 1, max(0, col + dc))
    next_state = COLS * next_row + next_col
    terminated = next_state in (GOAL_STATE, HAZARD_STATE)
    reward = 1.0 if next_state == GOAL_STATE else (-1.0 if next_state == HAZARD_STATE else -0.05)
    new_steps = int(steps_taken) + 1
    truncated = new_steps == MAX_STEPS and not terminated
    return Transition(state, action, next_state, reward, terminated, truncated, new_steps)


def choose_training_action(q, state, epsilon, rng):
    q = _validate_q(q)
    state = _validate_state(state)
    epsilon = _unit_interval("epsilon", epsilon)
    if not isinstance(rng, np.random.Generator):
        raise ValueError("rng must be a NumPy Generator")
    exploratory = bool(rng.random() < epsilon)
    if exploratory:
        action = int(rng.integers(N_ACTIONS))
    else:
        best = np.flatnonzero(q[state] == np.max(q[state]))
        action = int(rng.choice(best))
    return ActionChoice(action, exploratory)


def greedy_action(q, state):
    """Return a greedy action with fixed up/right/down/left tie order."""
    q = _validate_q(q)
    state = _validate_state(state)
    return int(np.argmax(q[state]))


def apply_q_update(q, item, alpha, gamma):
    q = _validate_q(q)
    if not isinstance(item, Transition):
        raise ValueError("item must be a Transition")
    alpha = _unit_interval("alpha", alpha)
    gamma = _unit_interval("gamma", gamma)
    old = float(q[item.state, item.action])
    future = 0.0 if item.terminated else float(np.max(q[item.next_state]))
    target = float(item.reward + gamma * future)
    error = target - old
    new = old + alpha * error
    q[item.state, item.action] = new
    return UpdateRecord(item, old, future, target, error, float(new))


def train_episodes(q, rng, episodes, alpha, gamma, epsilon):
    """Mutate Q with complete episodes and return one summary per episode."""
    _validate_q(q)
    episodes = _episode_count(episodes)
    alpha = _unit_interval("alpha", alpha)
    gamma = _unit_interval("gamma", gamma)
    epsilon = _unit_interval("epsilon", epsilon)
    if not isinstance(rng, np.random.Generator):
        raise ValueError("rng must be a NumPy Generator")
    summaries = []
    for _ in range(episodes):
        state = START_STATE
        total = 0.0
        for step in range(MAX_STEPS):
            choice = choose_training_action(q, state, epsilon, rng)
            item = transition(state, choice.action, step)
            apply_q_update(q, item, alpha, gamma)
            total += item.reward
            state = item.next_state
            if item.terminated or item.truncated:
                outcome = "goal" if state == GOAL_STATE else ("hazard" if state == HAZARD_STATE else "truncated")
                summaries.append(EpisodeSummary(float(total), item.steps_taken, outcome))
                break
    return summaries


def evaluate_greedy(q, episodes=100):
    """Evaluate without mutating Q or consuming the training RNG."""
    _validate_q(q)
    episodes = _episode_count(episodes)
    counts = {"goal": 0, "hazard": 0, "truncated": 0}
    returns = []
    steps_total = 0
    for _ in range(episodes):
        state = START_STATE
        total = 0.0
        for step in range(MAX_STEPS):
            item = transition(state, greedy_action(q, state), step)
            total += item.reward
            state = item.next_state
            if item.terminated or item.truncated:
                outcome = "goal" if state == GOAL_STATE else ("hazard" if state == HAZARD_STATE else "truncated")
                counts[outcome] += 1
                returns.append(float(total))
                steps_total += item.steps_taken
                break
    return {
        **counts,
        "episodes": episodes,
        "success_rate": counts["goal"] / episodes,
        "mean_return": float(np.mean(returns)),
        "mean_steps": steps_total / episodes,
    }
