# Product vision

## Outcome

Module Foundry lets a cohort member describe a STEM learning module, collaborate with specialist agents throughout its development, inspect the implementation and evidence, and export a reviewable module repository.

The product is collaborative rather than a one-prompt generator. Users can ask why a scientific method was selected, answer clarification questions, change scope, review a preview, and send a defect back for repair without losing the run's history.

## Primary user journey

1. The user creates a run with a natural-language goal.
2. The orchestrator turns the goal into an intake conversation.
3. The Learning Planner asks only questions that materially affect the learner experience.
4. The user reviews the learning specification.
5. The Scientific Architect proposes the model, data contract, interactions, and verification plan.
6. The Builder works inside an isolated workspace and streams progress and artifacts.
7. The QA Reviewer independently checks science, runtime, browser behavior, and instructional coverage.
8. Defects enter a bounded repair loop.
9. The user receives a preview, source workspace, decision log, QA report, and explicit limitations.

## Interaction model

The user sees one coherent conversation. Every agent response identifies its source. The orchestrator routes messages to a specialist or interprets them as a decision, scope update, approval, question, or build instruction.

Messages do not restart a build. They mutate a persistent run when allowed by the workflow state. Every mutation produces an event.

## Product boundaries for the first API release

Included:

- one user and local development deployment;
- persistent runs and resumable conversations;
- Planner, Architect, Builder, and QA roles;
- repository-backed prompts and skills;
- one model-provider adapter;
- isolated local workspaces;
- streamed events and artifact metadata;
- human checkpoints and bounded repair cycles.

Deferred:

- multi-tenant hosting and billing;
- automatic public deployment;
- fine-tuning or model-weight learning;
- a vector database before retrieval needs are demonstrated;
- simultaneous writes to the same module workspace;
- arbitrary third-party agent plugins.

## Success criteria

- A new cohort member can create and resume a run without editing orchestration code.
- User questions and decisions remain traceable outside raw model transcripts.
- No provider credential reaches the browser or generated module.
- Each specialist receives only the context and tools required for its task.
- A failed mandatory QA criterion prevents a ready status.
- Provider usage, latency, tool calls, retries, and human interventions are measurable.
