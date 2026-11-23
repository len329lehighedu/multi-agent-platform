---
name: scientific-oracle
description: Define an independent oracle, tolerances and sanity checks the Tester can run.
owner: researcher
---
# Scientific oracle

An oracle is a check that does not reuse the implementation it judges.

- Use a **known analytic or synthetic system** with a fixed seed and explicit data size, for example a system whose true coefficients you can state. List them in `oracle.systems`.
- Declare a **tolerance** in numbers ("coefficient error at most 5% on noise-free data"), never "close".
- Match the **metric space** to the claim: derivative error for fitting, state error for simulation, coefficient error for identification. State which.
- Include sanity checks the Tester can derive: error should degrade smoothly as noise rises; an all-zero model is valid and must not crash; the same seed reproduces the same result.
- Record what the oracle does NOT show. Low prediction error does not establish uniqueness or causality.
- Fill `covers` with the IDs of every `scientific_oracle` criterion in the task spec.

Do not claim the oracle has been run.
