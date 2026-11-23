---
name: stem-module-examples
description: Learns reusable UI, input/output, data-flow, and implementation patterns from the project's existing STEM module corpus when designing, building, or reviewing another module.
---

# Learn from existing modules

Read `corpus/catalog.json` from the project workspace. Select examples by task needs rather than treating SINDy as the universal design. Read the linked case study, then the relevant original files. Record source revision/hash and limitations if files have drifted or are inaccessible.

Build a small adaptation table in the run's spec/plan/report:

| Requirement | Exemplar source | Observed pattern | Adaptation and reason | How to verify |
| --- | --- | --- | --- | --- |

Cover the parts relevant to the request: layout and learner flow, input schema/controls, preprocessing, scientific method, state management, plots/diagnostics, output explanation, runtime behavior, and assessment. Do not force every category into a small change.

Separate observed source behavior from proposed improvements. Existing code may contain limitations; source code alone does not establish usability or runtime performance. Use screenshots or recorded browser review when making claims about rendered appearance.

Use model reasoning and current official technical sources to fill gaps. For a neural-network equation-discovery request, SINDy's upload/history/diagnostic patterns may transfer while its algorithm does not. Define the equation representation, method and package, data splits, output diagnostics, and benchmark plan specifically for the new task.

When adding another module, use `corpus/module-card-template.md`; register its source paths and hashes and label its review status honestly. Preserve feedback as proposed revisions with evidence. Do not call generated modules validated exemplars until reviewed. This corpus supplies examples in context; it does not update model weights.
