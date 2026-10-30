"""Projectile summaries: no drag, g=9.81 m/s², equal endpoint heights."""

import math


def _validated_scalar(value, name, upper):
    message = f"{name} must be a finite built-in int or float in [0, {upper}]"
    if type(value) not in (int, float):
        raise TypeError(message)
    # Compare before conversion: arbitrarily large built-in ints are valid
    # Python numbers but must yield ValueError rather than conversion overflow.
    if not 0 <= value <= upper:
        raise ValueError(message)
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(message)
    return converted


def projectile_summary(speed_m_s, angle_deg):
    """Return flight time (s), range (m), and maximum height (m).

    Accept only built-in int/float scalars (excluding bool): speed in [0, 50]
    m/s and angle in [0, 90] degrees. Invalid types raise TypeError; nonfinite
    or out-of-range numbers raise ValueError. Validate both parameters before
    handling launches with zero duration.
    """
    speed = _validated_scalar(speed_m_s, "speed_m_s", 50)
    angle = _validated_scalar(angle_deg, "angle_deg", 90)
    if speed == 0.0 or angle == 0.0:
        return {"flight_time_s": 0.0, "range_m": 0.0, "max_height_m": 0.0}

    theta = math.radians(angle)
    vx = 0.0 if angle == 90.0 else speed * math.cos(theta)
    vy = speed * math.sin(theta)
    gravity = 9.81
    flight_time = 2.0 * vy / gravity
    result = {
        "flight_time_s": flight_time,
        "range_m": vx * flight_time,
        "max_height_m": vy**2 / (2.0 * gravity),
    }
    return {key: 0.0 if value == 0.0 else value for key, value in result.items()}
