# Evaluation report

## Functional and behavioral evidence

| Case | Actual scope and evidence | Result | Limitations |
| --- | --- | --- | --- |
| New module | Projectile pilot, explicit Planner/Architect/Builder/QA, source adaptation,8 Builder tests, independent checks and actual browser controls | Pass: all8PM criteria accepted by QA | Faculty/human acceptance separate |
| Reuse for data science | Linear regression uses same host/shell/module contract;10 Builder tests and independent OLS/held-out tests | Pass: all10LR criteria accepted by QA | Two pilots demonstrate reuse, not universal module generation |
| Existing-module adaptation | Isolated CSV ingestion fixture reuses shipped regression Dataset/OLS;9 tests and independent QA | Numerical ingestion extension passes | This is a narrowed evaluation. The original broader CSV upload UI/residual-rendering request was not implemented or accepted |
| Scientific/performance review | Independent QA reviewed controlled claim-review fixture without being given expected findings | Detected unsupported equation-recovery, generalization and fixed-time claims | Fixture is intentionally for evaluation, not shipped as a lesson |

A real instructional defect was found and repaired: fixed-seed/n OLS residuals scale with sigma and MSE with sigma squared in this exactly linear experiment. The broad nonmonotonic noise warning was qualified; a metamorphic test and independent QA recheck support the correction. Browser screenshots were refreshed after restarting the repaired app.

## Productivity

No matched human baseline measurements exist. The result in runs/mvp-completion-20261030/productivity-status.json is insufficient-data, not a30% gain. Training/computation timings are not human-effort measurements.

To measure: create at least three equivalent task pairs with identical acceptance criteria. Run baseline using the team's usual tools and multi-agent mode. Record active human minutes, wall seconds, actual available cost, and quality outcome. Keep unsuccessful runs. Report setup/maintenance effort separately. Use measurements-template.csv and scripts/evaluate_productivity.py; synthetic evaluator unit tests are not project performance data.

```bash
.venv/bin/python scripts/evaluate_productivity.py evaluations/measurements.csv --output output/productivity.json
```

The evaluator refuses invalid/duplicate measurements, reports missing pairs as insufficient-data, and does not drop quality failures to manufacture a gain. The target is30% lower median active human task effort across at least three matched pairs at equivalent quality. A small study still does not establish general productivity improvement.

## Runtime and educational limits

Actual native Codex subagents with explicit role/skill-file assignments were exercised. Live Claude execution, learner outcome studies, unrestricted neural equation discovery and deployment are outside verified scope. Automatic configuration discovery must be assessed separately from explicit role execution. Human acceptance of generated pilots/corpus remains pending.
