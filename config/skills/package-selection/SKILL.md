---
name: package-selection
description: Select science packages with pinned, verified versions, license and footprint.
owner: researcher
---
# Package selection

The stack (Bokeh, NumPy, pandas, scikit-learn, SciPy) is a given. Choose only the extra science packages the method needs.

For every package record `name`, an exact pinned `version`, `purpose`, `license` and `verified`.

- Set `verified: true` only if you checked the version and the API you rely on against official documentation or the package index in this run. Otherwise set `false` and add a line to `risks`. Never invent a version number.
- Prefer maintained packages with a permissive license and CPU-only operation.
- Avoid heavy dependencies when a small one suffices; deployment is a university server.
- Check Python compatibility with the module's interpreter (3.13 unless the task says otherwise).
- One package per purpose. Do not add a library for something NumPy or SciPy already does.
- State anything that conflicts with the fixed stack.

Do not write install scripts.
