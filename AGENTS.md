# Module Foundry development instructions

This repository is an API-first multi-agent product. Work from the repository root.

## Sources of truth

- Product behavior: `docs/product-vision.md`
- Architecture boundaries: `docs/architecture.md`
- HTTP contract: `docs/api-contract.md`
- Runtime agent definitions: `config/agents/`
- Runtime skill content: `config/skills/`
- Python implementation: `src/module_platform/`

Do not add generated learning modules to the product root. Runtime-created module code belongs in an isolated workspace under the configured data root. Do not make the orchestration core depend directly on a specific model vendor or web framework.

Preserve user decisions, agent messages, stage transitions, tool results, failures, and QA evidence as structured run events. Human questions are first-class workflow states, not exceptions hidden in chat history.

The earlier prototype is not in the working tree; recover it from git history if needed. Do not reintroduce dependencies on it.

Run foundation tests with:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```
