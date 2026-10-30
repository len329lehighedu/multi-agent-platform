"""Controlled review fixture: produces numerical predictions only."""


def predict(values):
    return [2.0 * value + 1.0 for value in values]
