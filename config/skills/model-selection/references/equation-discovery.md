# Equation-discovery decisions

The request “use a neural network to find an equation from input data” is a task family, not a fully specified algorithm.

| Desired scientific output | Method family to investigate | Required evidence |
| --- | --- | --- |
| A numerical predictor or learned vector field | Neural regression or neural differential equation methods | Held-out prediction, rollout behavior where applicable, and model limitations |
| An explicit interpretable formula | Symbolic regression or neural model plus a specified symbolic extraction stage | Extracted expression, complexity, held-out error, and recovery checks on a known system |
| Unknown coefficients in a known equation | Parameter inference, potentially a physics-informed network | Assumptions, identifiability, coefficient error, and residual/trajectory checks |

Package choice follows this distinction. Investigate current official documentation before committing to a library; PyTorch, differential-equation libraries, and symbolic-regression libraries are candidates, not universally required dependencies. A source-code formula representing an entire network is not automatically the concise governing equation the learner expects.

If the request is ambiguous, present the interpretations and record the proposed output before expensive implementation. Ask only when that choice materially changes the requested outcome. Do not call a black-box model successful symbolic discovery.

Plan the interface together with the method: input preview and schema errors, variable/time mapping where relevant, data split, noise handling, training budget and progress, learning curve, fitted versus observed values, residuals, and any discovered expression with units and limitations. Show derivative and state errors separately for dynamical systems. Not every module needs every plot.

For an initial benchmark, use a known synthetic system with a fixed seed and an explicit data size. Check recovery within a declared tolerance, held-out behavior, degenerate data, and noisy-data limitations. Do not infer mathematical uniqueness or causality from low prediction error.
