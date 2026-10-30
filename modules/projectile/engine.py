"""Bounded, deterministic equal-height projectile motion in SI units."""
from dataclasses import dataclass
from numbers import Integral, Real
import math
import numpy as np

GRAVITY = 9.81
MAX_SAMPLES = 10001


@dataclass(frozen=True)
class Trajectory:
    """Aligned float64 samples, with analytic summaries (seconds and meters)."""
    time: np.ndarray
    x: np.ndarray
    y: np.ndarray
    flight_time: float
    range: float
    max_height: float


def _scalar(value, name, maximum):
    # Reject arrays, booleans, strings and complex values before conversion.
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real scalar in [0, {maximum}].")
    result = float(value)
    if not math.isfinite(result) or not 0 <= result <= maximum:
        raise ValueError(f"{name} must be a finite real scalar in [0, {maximum}].")
    return result


def trajectory(speed, angle, *, samples=201):
    """Return motion from launch to landing at the launch height.

    speed: real scalar in [0, 50] m/s; angle: real scalar in [0, 90] degrees.
    samples: integer in [2, 10001]. A zero-speed or horizontal launch has
    zero flight duration and all-zero sampled positions. Vertical launch
    has exactly zero horizontal position and range. No drag is modeled.
    """
    speed = _scalar(speed, "speed", 50)
    angle = _scalar(angle, "angle", 90)
    if isinstance(samples, (bool, np.bool_)) or not isinstance(samples, Integral) or not 2 <= samples <= MAX_SAMPLES:
        raise ValueError(f"samples must be an integer in [2, {MAX_SAMPLES}].")
    samples = int(samples)
    radians = math.radians(angle)
    vy = speed * math.sin(radians)
    vx = 0.0 if angle == 90 else speed * math.cos(radians)
    flight_time = 2 * vy / GRAVITY
    distance = 0.0 if angle in (0, 90) else speed**2 * math.sin(2 * radians) / GRAVITY
    height = vy**2 / (2 * GRAVITY)
    time = np.linspace(0, flight_time, samples, dtype=np.float64)
    x = vx * time
    y = vy * time - 0.5 * GRAVITY * time**2
    # Only remove endpoint cancellation roundoff; retain the analytic arc.
    x[-1] = distance
    y[0] = y[-1] = 0.0
    return Trajectory(time, x, y, flight_time, distance, height)
