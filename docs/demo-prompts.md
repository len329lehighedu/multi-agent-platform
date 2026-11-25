# Demo prompts

Saved to run during a demo, so no API credit is spent before then. Create a new project for each.
Thresholds in these prompts were chosen to be reachable; do not tighten them without measuring first.

## PINN: damped harmonic oscillator (not yet run with Claude)

Needs `pip install -r requirements-modules.txt` (PyTorch). Measured locally on 2026-11-25 with this
model over 10 seeds (d = 0.5, w = 4, T = 2), worst relative L2 error: 200 iterations 0.57, 500
iterations 0.24, 3000 iterations 0.044 (about 1.3 s of CPU training). At w = 6 the error is about
0.33 after 3000 iterations, which is a useful teaching moment, not a bug. Estimated cost $0.2-0.5.
Watch the Builder (Haiku): this is its first hard task (second-order autograd). If two repair rounds
fail, set the builder tier to `strong` in `config/agents/manifest.json`.

```text
Build a module that teaches Physics-Informed Neural Networks (PINNs) on a damped harmonic oscillator u'' + 2*d*u' + w^2*u = 0 with u(0)=1, u'(0)=0, for t in [0, 2]. Use PyTorch on CPU. No file upload; the exact analytic solution is the reference.

Model: a fully connected network with two hidden layers of 32 tanh units, hard-constrained initial conditions u(t) = 1 + (t/2)^2 * N(t/2), trained with Adam (learning rate 0.01) on 100 evenly spaced collocation points, loss = mean of (residual / w^2)^2. Use torch.set_num_threads(2) and a fixed seed.

Train tab: sliders for damping d (0.1 to 1, default 0.5), frequency w (2 to 6, default 4), training iterations (200 to 5000, default 3000) and seed; a Train button; a plot of the PINN solution against the exact solution and a plot of the loss curve on a log scale.
Test tab: pointwise absolute error over t, and the relative L2 error against the exact solution.
Predict tab: a slider for t from 0 to 4 showing the PINN and exact values, so learners see that extrapolating beyond the training interval t <= 2 fails.

Acceptance: with the default settings the relative L2 error after 3000 iterations is below 0.08; the error after 200 iterations is larger than after 3000; the same seed gives identical results. Do not state any other numeric thresholds. Tests must finish in well under 180 seconds.
```

## Polynomial regression and overfitting (run successfully)

```text
Build a module where learners explore overfitting with polynomial regression.
Use built-in synthetic data only (a noisy sine curve), no file upload. Use numpy only, no scikit-learn.

Train tab: sliders for polynomial degree (1 to 15), noise level, number of training points, and a random seed. Plot the data points and the fitted curve.
Test tab: evaluate the fit on held-out points, show train error and test error (RMSE), and plot both errors against polynomial degree so learners can see overfitting.
Predict tab: a slider for x, showing the model's prediction and the true curve value.

Acceptance: test error at degree 15 is clearly larger than at the best degree; fitting the same seed twice gives identical results.
```

Follow-up feature (run successfully):

```text
Add a Cross-validation tab to this module. The learner picks the number of folds (3 to 10) with a slider and sees, for every polynomial degree from 1 to 15, the mean validation RMSE across folds with an error band of one standard deviation. Mark the degree with the lowest mean validation RMSE. Reuse the existing engine and data; use numpy only, and make folds reproducible from the seed.

Acceptance: the same seed and fold count always give identical results; the selected degree has the lowest mean validation RMSE of all degrees shown; with noise 0.1 the mean validation RMSE at degree 15 is higher than at the selected degree. Do not state any other numeric thresholds.
```

Not yet run:

```text
Add Ridge regularization to the polynomial fit. A new slider sets the regularization strength lambda on a log scale from 1e-6 to 10 (default 0), shared by the Train, Test and Predict tabs. On the Test tab add a plot of test RMSE against lambda for the current degree, with the best lambda marked. Use numpy only (closed-form solution), not scikit-learn.

Acceptance: lambda 0 gives the same coefficients as the existing fit; the same seed gives identical results; at degree 15 and noise 0.1 the best lambda from the sweep gives a lower test RMSE than lambda 0. Do not state any other numeric thresholds.
```
