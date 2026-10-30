# Builder → QA

Run: setup-smoke-codex-20261030-01. Producer: /root/smoke_builder, actual Codex native subagent. Status: ready for independent verification.

Inputs: specifications and handoff-02. Outputs: fixture/projectile.py, build-report.md with exact initial checks on Python 3.14.0. Criteria: SM-01–04. No reported defect.

Next: independently inspect implementation, add meaningful tests under verification/, run them, verify adapter/configuration consistency and source adaptation, and save qa-report.md plus execution results. Distinguish numerical smoke acceptance from full pilot, browser, custom-role discovery, and Claude runtime acceptance. Do not change application fixture or specifications. Actual native dispatches are observed by the parent conversation; persisted role IDs are orchestrator attestations, not exported raw traces.
