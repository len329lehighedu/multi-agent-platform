"""What generated modules may import: the science packages installed in the shared interpreter."""

from __future__ import annotations

import platform
from importlib import metadata

# Only packages a module may choose from; the platform's own dependencies (Flask, SDKs) are not offered.
SCIENCE_PACKAGES = ("numpy", "scipy", "pandas", "scikit-learn", "bokeh", "torch", "jax", "matplotlib")


def available_packages() -> dict[str, str]:
    found = {}
    for name in SCIENCE_PACKAGES:
        try:
            found[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            continue
    return found


def environment_note() -> str:
    listed = ", ".join(f"{name} {version}" for name, version in available_packages().items())
    return (f"Module environment: Python {platform.python_version()}, CPU only. Installed packages (import only these and the "
            f"standard library; pin these exact versions): {listed}. Tests and the live preview run in this same environment, "
            "and tests time out after 180 seconds.\n\n")
