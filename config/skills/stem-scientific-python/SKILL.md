---
name: stem-scientific-python
description: Chooses and implements scientific methods, data contracts, Python packages, reproducibility, and measured computation budgets for STEM modules, including equation discovery.
---

# Scientific implementation decisions

Start from the requested output: prediction, parameter inference, governing equation, symbolic expression, uncertainty, or a comparison. Do not substitute a convenient algorithm for the required output. An unconstrained neural network is not inherently an interpretable equation.

Define data columns, units, shapes, numeric types, missing/nonfinite handling, order requirements, and valid sizes. Apply time monotonicity and trajectory boundaries to time-series methods where needed; do not impose SINDy's CSV convention on unrelated datasets. Fit preprocessing only on training data. Choose split strategy for the data structure and intended generalization claim.

Compare plausible methods and packages by scientific fit, maintained official APIs, license, CPU/GPU requirements, Python support, and deployment footprint. Verify versions instead of assuming availability. Keep scientific computation separate from web/UI state and test against an independent oracle or known synthetic system. Record seeds, configurations, split definitions, and software versions.

Read [the equation-discovery decision guide](references/equation-discovery.md) for requests involving neural networks or inferred equations.

Treat training time as measured behavior. Benchmark a bounded representative dataset; record hardware/device, sample count, features, architecture, epochs/stopping rules, seeds, warm-up, fit-only time and total user-visible time separately. Label estimates, timeout bounds, failures, and unmeasured work explicitly. Design a responsive execution path for expensive workloads.
