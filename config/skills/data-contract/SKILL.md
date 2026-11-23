---
name: data-contract
description: Define inputs, units, validity rules, multi-file semantics and a leakage-safe split.
owner: researcher
---
# Data contract

The contract is what the upload validator and the engine will enforce, so make it checkable.

- **Columns:** name, unit and meaning for each. For time series the first column is time and must be strictly increasing; remaining columns are state variables with identical names and order across files.
- **Validity rules** (one line each): no NaN or infinite values, minimum row count, maximum upload size (5 MB), numeric dtype, header required.
- **Multiple files:** decide whether they are separate trajectories of one system (same columns, different initial conditions) or something else. Compute any derivative or window PER file before pooling; pooling first creates artificial jumps where time restarts.
- **Split strategy** must match the data structure and the generalization claim: random sampling over pooled pairs, time-based hold-out, or random blocks. Respect trajectory boundaries. Record `train_fraction` and a one-sentence `leakage_guard` (for example "preprocessing is fit on the training split only").
- **Test data** must have exactly the training column names and order.
- Specify built-in datasets and whether they are simulated with a known truth.

Do not impose a time-series layout on tabular tasks.
