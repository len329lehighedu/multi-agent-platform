# QA report

## Context

Run: `setup-smoke-codex-20261030-01`. Reviewer execution reference: `/root/smoke_qa`, independent Codex native subagent assigned explicit canonical role/skill files. Reviewed 2026-10-30. Scope: numerical setup smoke only, as defined in this run's `brief.md`, `learning-spec.md`, and `technical-plan.md`; `briefs/projectile-motion.md` supplies an additional analytical case, not the smoke acceptance scope.

Fixture: `runs/setup-smoke-codex-20261030-01/fixture/projectile.py`, SHA-256 `9ce35e42716a2e7ded0cda523f623260c285e3bce3e61c64582890eca7ba85eb`. Parent repository HEAD: `d58a9a9b315273e2675216593a1a4bb86a57ccb4`; platform is currently untracked, so HEAD alone does not identify these generated artifacts. Exact environment and command output are saved in `verification/execution.log`.

Explicitly read `AGENTS.md`, `agents/stem-qa-reviewer.md`, all three named skill files (`stem-module-examples`, `stem-lesson-design`, `stem-module-verification`), the QA template, run input artifacts, fixture, original validation source, corpus records, relevant pilot brief, setup/adapter scripts, generated QA adapters, and parent-authored dispatch evidence. No automatic discovery or preloading is inferred from these explicit reads. No fixture/spec/configuration edits, package installations, or delegation were performed.

## Criterion results

| Criterion ID | Mandatory? | Status: pass/fail/blocked/not-run | Method | Evidence path or observation | Limitation |
| --- | --- | --- | --- | --- | --- |
| SM-01 actual sequential agent execution | Yes | pass | Review parent dispatch record, stage artifacts and handoffs; execute independent QA stage | `execution-evidence.json`, `run.json`, three handoffs, this QA return | Parent observed actual dispatches; saved role IDs and dispatch records are orchestrator attestations, not exported raw runtime traces. QA cannot independently replay prior sessions. Parent must finalize QA returned status after this response. |
| SM-02 source-backed adaptation | Yes | pass | Independently inspect original validator, compare catalog hash and adaptation table | `../engine/check_datafile.py` relative to platform; `technical-plan.md`; `verification/execution.log` | Verified validation transfer only. UI/engine separation is a case-study observation, not independently revalidated runtime behavior. |
| SM-03 independent numerical and input checks | Yes | pass | Eight unittest methods using closed forms and physical invariants; 1e-12 relative/absolute tolerance for nonzero comparisons | `verification/test_projectile.py`; `verification/execution.log`, unittest exit 0 | Finite machine precision; subnormal underflow is allowed and not evidence of endpoint snapping. No trajectory API or UI exists in scope. |
| SM-04 saved outputs and honest limitations | Yes | pass | Inspect prior outputs and save independent tests, exact command/output evidence, and this report | Run brief/spec/plan/build report/handoffs/manifest/dispatch record plus QA artifacts | Final manifest/status assembly belongs to orchestrator; current in-progress state correctly represents QA before return. Human acceptance remains pending. |
| Shared setup / adapter consistency | Supplemental | pass | `python3 -B scripts/check_setup.py`; `python3 -B scripts/sync_runtime.py --check`; Codex runtime presence check | `verification/execution.log`: four roles, eight skills, zero static errors; no adapter drift; Codex on PATH | Script checks local metadata, referenced files, hashes and generated text; does not establish runtime schema support, role selection, tool permissions or skill loading. |
| Claude runtime availability | No, outside Codex smoke | fail | `python3 -B scripts/check_setup.py --require-runtime --runtime claude` | `verification/execution.log`: exit 1, Claude absent from PATH | Claude execution is not-run; static adapter consistency passed. No installation attempted. |
| Automatic discovery / preloading / custom-role selection | No | not-run | Explicit role-file assignment used throughout this run | Run records and parent dispatch evidence | Requires a separate fresh-session discovery experiment. |
| Full Flask/Bokeh pilot and browser acceptance | No | not-run | Explicitly excluded by smoke brief | No UI/services built or launched | PM-01–PM-08 are not accepted by this report. Numerical checks alone do not satisfy full PM-02 trajectory acceptance or browser criteria. |
| Instructional effectiveness / rendered lesson | No | not-run | Content inspection only | Learning spec states assumptions, objective and one misconception assessment | Appropriate to small smoke scope; complete pilot needs three questions and rendered/content review, and measured effectiveness needs separate study. |

## Findings

No scientific or implementation defects were found in the declared numerical contract. The fixture independently passed analytical cases `(20,30)`, `(10,45)`, `(50,90)`; 48 speed/angle grid combinations with range upper bound, complementary-angle symmetry and apex/time invariant; six speed-scaling cases; exact endpoints and positive zeros; four near-endpoint cases; 26 invalid-type checks and 18 invalid-number checks across both parameters; and fresh-dictionary isolation. Invalid values are rejected even when the other input would produce zero flight duration. Error messages identify the parameter and its range.

Independent oracle examples: at `(20,30)`, vertical velocity is exactly 10 m/s analytically, so T=20/9.81, R=200√3/9.81, H=50/9.81. The grid also checks H=gT²/8 and R≤v²/g; these are physical constraints rather than a copied helper or duplicate of the fixture algorithm.

Source adaptation is supported: original `validate_dataframe` rejects missing/NaN and infinite data with explanatory messages before downstream work; its SHA-256 matches catalog `79ee0bb486c3217963785a103feea964d6385f6d25441c9e4b566a72e1ac76af`. The scalar fixture applies the same early-feedback principle using scalar exceptions, bounds and type rules suited to this task. No source code was copied into tests or fixture by QA.

Runtime limitation L-01: Claude is absent, as independently confirmed by the explicit required-runtime check. Expected: available executable before Claude execution can be verified. Actual: absent from PATH. Owner: orchestrator/environment setup, only if Claude verification is requested. Recheck: not-run. This does not block the Codex smoke and is not an adapter defect.

Workflow limitation L-02: persistent dispatch evidence is parent-authored, accurately labeled, and contains input hashes. It is useful provenance but not a raw trace export. Prior automatic skill loading and project discovery remain unverified. Owner: orchestrator; preserve these distinctions in final reporting.

## Performance

Environment: macOS 26.1 arm64, Python 3.14.0, Clang 16.0.0; standard library only. CPU model, RAM and device utilization were not measured. Deterministic scalar calls; no dataset, training, epochs, seed, split or stopping condition applies. One test-suite execution reported eight test methods in 0.001 s; this is unittest duration, not a fixture benchmark, user-visible latency measurement or Python/dependency compatibility guarantee. No UI responsiveness, timeout, fit-time or service measurements were made.

## Recommendation

Ready for human review of the numerical Codex setup smoke only. All four smoke criteria pass within the evidence qualifications above; no repair cycle is needed. Orchestrator should finalize QA stage/dispatch return fields and the run status after receiving this report. Human acceptance and approval as a corpus exemplar remain separate and pending.

To establish excluded capabilities later: start a fresh platform-root session and demonstrate role/skill discovery without explicit file assignments; verify Claude in an actual installed Claude session; build the full pilot, launch both services from a fresh dependency environment, inspect control changes and WebSocket/console state in the embedded browser, test two sessions independently, inspect desktop and narrow viewports, and capture startup/shutdown and lesson-content evidence against PM-01–PM-08. These are follow-up verification steps, not work completed by this smoke.
