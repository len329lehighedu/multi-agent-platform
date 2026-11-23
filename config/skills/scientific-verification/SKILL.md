---
name: scientific-verification
description: Verify that the implementation matches the scientific definition using independent evidence.
owner: tester
---
# Scientific verification

Builder reports are leads, not evidence.

1. **Oracle.** Run the research brief's oracle with its stated tolerance. Compute the expected values independently of the engine (analytic result or a separately written reference), never by calling the code under test.
2. **Claim versus output.** Confirm the module delivers the promised output type. An equation module must show an interpretable expression with units and limits, not only a predictor.
3. **Leakage.** Preprocessing fit on training data only; train and validation indices disjoint; derivatives or windows computed per trajectory before pooling; split respects trajectory boundaries.
4. **Reproducibility.** Same seed gives the same result; different seeds change only what they should.
5. **Metric space.** Metrics are computed where the brief says (derivative, state, coefficient) and labelled so.
6. **Robustness.** Error rises smoothly with noise; degenerate data fails visibly.
7. **Units and labels.** Axes and equations carry units.

Report the measured numbers next to the tolerance. If a check cannot run, mark it `blocked` or `not_run` with the exact manual steps.
