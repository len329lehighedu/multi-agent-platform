---
name: stem-module-verification
description: Verifies generated STEM modules using independent scientific checks, live interaction evidence, instructional criteria, reproducibility, and honest performance measurements.
---

# Independent acceptance review

Map every mandatory criterion to a verification method before evaluating. Use `templates/qa-report.md`. Record pass, fail, blocked, or not-run; only pass with evidence. Include environment and exact commands for automated checks.

Test scientific outputs against a known analytical result, trusted reference, or controlled synthetic dataset. Avoid an oracle that duplicates the same implementation. For ML, check preprocessing leakage, split validity, reproducibility, and whether the actual model output matches the promised scientific claim.

Check malformed input and relevant edge cases, route behavior, Bokeh callbacks, embedded browser interactions, learner-session isolation, launch/shutdown, instructional objectives, units, and assessment. Choose meaningful checks proportional to the module; do not substitute a checklist of headings for behavior verification.

Verify responsiveness and timing claims on representative inputs. Record device, data size, epochs and stopping rules, software versions, measured fit/end-to-end times, and failures. Differentiate estimate from measurement.

If browser or dependency access is missing, preserve unverified criteria as not-run or blocked and provide reproducible follow-up steps. Report defects with trigger, expected and actual behavior, severity, evidence, and recommended owner. Recheck repaired behavior before closing a defect. Do not rewrite application code while conducting independent QA.
