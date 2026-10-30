"""Simple parameter exploration: y = coefficient * x."""

import math


def evaluate(coefficient):
    if type(coefficient) not in (int, float) or not math.isfinite(coefficient) or not -5 <= coefficient <= 5:
        raise ValueError("Coefficient must be a finite number between -5 and 5")
    x = list(range(11))
    return {"x": x, "y": [float(coefficient) * value for value in x]}
