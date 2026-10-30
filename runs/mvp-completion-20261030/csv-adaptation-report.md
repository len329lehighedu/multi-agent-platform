# CSV adaptation behavioral evaluation

Status: **narrowed numerical extension implemented and verified**. This fixture evaluates the existing-module adaptation behavior in `evaluations/cases.md` with the orchestrator's explicit scope: ingest in-memory CSV text with exactly x,y headers, 20–300 finite numeric rows, deterministic seeded 75/25 split, then fit through the shipped engine. No browser upload UI was requested for this narrowed evaluation. The full original case's uploaded-file browser workflow and rendered residual comparison were not implemented or verified and must not be marked completed by this report.

## Execution and instruction evidence

The existing regression pilot was available at evaluation time. Read `evaluations/cases.md`, `.agents/skills/stem-module-verification/SKILL.md`, and the shipped `modules/linear-regression/engine.py` before extending it. Applied previously explicitly read `stem-scientific-python` and `stem-module-examples` skills. The assignment was explicitly dispatched to regression Builder; no agent delegation, dependency installation, or skill auto-loading is claimed. Runtime: this Codex subagent session, inherited model (precise backend model identifier/usage metrics unavailable to the fixture); CPython 3.14.0, NumPy 2.4.1 in the shared verified environment. Human curriculum/fixture review remains pending. No clarification or approval intervention was required during this narrowed task.

Write scope was confined to `evaluations/artifacts/csv-adaptation/**` and this report. The shipped pilot, shared runtime, evaluation definitions, QA findings, and corpus catalog were not edited.

## Change versus the existing module

The shipped regression module originally produces x/y from a fixed synthetic generating line and known Gaussian draws. This fixture adds a parser for user-supplied x/y observations held in memory. It validates CSV structure, row count, numeric conversion and finiteness, preserves the input observation order, and assigns training/test indices using a seeded NumPy permutation. It then calls the shipped `fit_and_evaluate`; no least-squares algorithm is duplicated.

The shipped Dataset requires standard_noise even though CSV has no generating-noise information. The adapter sets it to zero solely as a compatibility placeholder, explicitly documented as unknown rather than inferred noiseless data. It does not claim recovery of a known true line for arbitrary CSV. Constant training x remains a rank-deficiency error from the shipped engine.

The split is the first floor(.75*n) rows of `default_rng(seed).permutation(n)` for training, the remainder for test. The same input row count and seed reproduce the split; changing y alone does not change it. This is not promised to match the synthetic generator's split, because the latter draws noise before its permutation. Valid seeds are integer [0,4294967295].

| Adaptation requirement | Existing pattern inspected | Change and reason | Actual evidence |
| --- | --- | --- | --- |
| Preserve scientific behavior | Shipped Dataset and fit_and_evaluate API | Import the existing engine directly under an isolated namespace; no OLS copy | Source-path assertion, centered-sums independent oracle, original module suite |
| Define valid CSV schema | Corpus data-validation guidance; existing finite aligned-array validation | Exactly x/y, no time column, 20–300 finite numeric observations, normal CSV quoting | Malformed header/column/quote, NaN/Inf/text/empty cell and oversized-row tests |
| Preserve split/leakage boundary | Existing train-only OLS API | Construct deterministic disjoint/exhaustive train/test arrays; pass all evaluation to shipped engine | Repeatability/coverage tests and held-out-y perturbation |
| Return meaningful residual evidence | Existing RegressionResult residuals and separate MSE | fit_csv returns Dataset and shipped RegressionResult for numerical comparison | Independent signed residual/MSE oracle; known-line recovery |
| Preserve pilot | Separate fixture path | No production/browser changes | Original 9-test suite passed after extension |

## Acceptance and executed commands

From `/private/tmp/stem-platform-completion-20261030`:

```sh
/private/tmp/stem-platform-venv-20261030/bin/python -m unittest discover -s evaluations/artifacts/csv-adaptation/tests -v
```

Initial result: **9 tests passed**, unittest time 0.053 s. A repeated run also passed and is retained at `evaluations/artifacts/csv-adaptation/test-results.txt`. This is test-run duration, not an end-user latency benchmark.

```sh
/private/tmp/stem-platform-venv-20261030/bin/python -m unittest discover -s modules/linear-regression/tests -v
```

Result after extension: **9 original pilot tests passed**, unittest time 0.432 s. No failures required repair.

| Criterion | Result | Evidence |
| --- | --- | --- |
| Valid generated CSV preserves x/y and fits via shipped API | PASS | Generated 91-row CSV round-trip, actual engine source-path check, independent centered-sums coefficients and manual residual/MSE oracle |
| Valid boundary sizes and arbitrary line | PASS | 20/300 rows, x spanning negative and positive values, slope −3/intercept 7 recovery |
| Header and row structure validation | PASS | Empty/wrong/reversed/duplicate/extra headers, whitespace-modified header, missing/extra values, malformed quotes, blank row rejected |
| Finite numeric values only | PASS | Nonnumeric, NaN, Inf, negative Infinity, overflow-to-Inf and empty cells in either column rejected |
| Row-count boundaries | PASS | 0/19/301/500 data rows rejected; 20/300 accepted |
| Deterministic valid split | PASS | 83 rows: 62 train/21 test, repeatability, disjoint/exhaustive coverage, different seed changes split |
| Seed/input validation | PASS | Out-of-range/fractional/bool/string/None seeds and nontext payloads rejected |
| Train-only fit and rank validation preserved | PASS | Perturb held-out responses without coefficient changes; constant x still rejected by engine |
| Existing pilot behavior preserved | PASS for automated evidence | Original 9 numerical/UI-Document tests pass; no production files edited |
| Browser CSV upload control/rendered residual comparison | NOT IMPLEMENTED / NOT RUN | Excluded by narrowed task; full original evaluation remains broader |

## Artifacts and limits

Artifacts: `csv_adapter.py`, `tests/test_csv_adapter.py`, `README.md`, retained `test-results.txt`, and this report. The extension has no new dependencies. Source path resolution deliberately expects the fixture to remain inside this repository; it is not packaged as a standalone distribution.

This validates a numerical input adaptation and residual evaluation, not browser upload UX, file transport/security policy, rendered comparison, two-session browser behavior, performance guarantees, curriculum gains, or agent productivity. It is an evaluated extension fixture, not a reviewed/approved corpus module. No silent promotion or corpus registration occurred. The evaluation case document's historical statement that no regression fixture exists is now stale, but it was left unchanged because it is outside this task's write scope; the orchestrator owns any status update.
