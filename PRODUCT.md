# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Developers working for a professor on the STEM VISUALIZATION project. They sign in (auth is deferred to deploy), prompt a team of agents (Project Manager, Researcher, Builder, Tester) and review plans, builds and QA evidence over long sessions. A later audience of viewers who only run released modules is planned but is not the design target of the console.

## Product Purpose

Module Foundry (UI brand: STEM VISUALIZATION) is an API-first multi-agent platform that builds interactive data-science teaching modules (fit, train, test, predict) in the style of the professor's SINDy exemplar. Success: a developer goes from an idea to a tested, working Bokeh module, then keeps refining it with changes and new features, without losing control of what the agents decided or did.

## Positioning

Every feature goes through a visible plan loop (research, design, tests, plan, human approval) before any code is written. Builds are verified by real test output, failures trigger bounded repair, failed changes roll back, and all decisions, questions and QA evidence are kept as structured run events. Generated modules are Bokeh-only. This is a controlled, auditable build process for teaching modules, not a general-purpose code generator.

## Operating Context

- Home lists projects; each project owns exactly one module and one shared workspace.
- Inside a project the developer chats with agents, answers agent questions, approves the plan, then watches the build. After a build, chat means "change this module"; "New feature" restarts the full plan loop on the existing module.
- One writer per project at a time. Runs stream as events (SSE).
- Today the console is a workflow viewer (chat, stage tracker, agent graph). Planned: the live module in the centre, collapsible chat on the left, status strip, criteria board, details drawer.

## Capabilities and Constraints

- Local-only for now; no auth. Backend is Python with JSON stores; the frontend is vanilla HTML/CSS/JS in `apps/web` with no build step.
- Modules are Bokeh only: no Flask shell, no HTML description pages (descriptions are in-app Bokeh text).
- Terms: project, module, run (kind "module" or "feature"), plan, build, revision, QA report, stage, agent.
- Undecided: live module preview embedding, multi-developer branches and merges, cost display, who approves releases.

## Brand Commitments

- Name: STEM VISUALIZATION. Logo: `apps/web/static/logo.jpg` (from the professor's project).
- UI language is English.

## Evidence on Hand

- Product docs: `docs/product-vision.md`, `docs/process.md`, `docs/deferred-decisions.md`.
- The SINDy module as golden exemplar (user's STEM VISUALIZATION repo).
- No real token-cost measurements, user research or testimonials yet; do not invent them.

## Product Principles

- Evidence over claims: show real test output and QA results, never an agent's say-so.
- Humans decide at gates: questions and plan approval are first-class states.
- Keep the module the hero: the console serves the module being built.
- Every action is traceable and reversible where possible (events, snapshots, rollback).
- Small, legible surfaces for long sessions; no decoration that competes with status.

## Accessibility & Inclusion

Full keyboard operation and WCAG AA contrast are required.
