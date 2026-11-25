---
name: package-selection
description: Select science packages with pinned, verified versions, license and footprint.
owner: researcher
---
# Package selection

Choose only from the packages the task context lists as installed in the module environment; nothing else can be imported or installed. If the method needs a package that is not listed, say so in `risks` and choose a method that works with the listed ones.

For every package record `name`, an exact pinned `version`, `purpose`, `license` and `verified`.

- Set `verified: true` only if you checked the version and the API you rely on against official documentation or the package index in this run. Otherwise set `false` and add a line to `risks`. Never invent a version number.
- Prefer maintained packages with a permissive license and CPU-only operation.
- Avoid heavy dependencies when a small one suffices; deployment is a university server.
- The interpreter version is stated in the task context.
- One package per purpose. Do not add a library for something NumPy or SciPy already does.
- State anything that conflicts with the fixed stack.

Do not write install scripts.

`packages` in the research brief must have at least one entry, even when the method needs nothing beyond the given stack. List every library the module imports beyond the standard library (for example `numpy`), with the pinned version, and `verified: false` plus a risk line when you did not check it. An empty list is rejected.