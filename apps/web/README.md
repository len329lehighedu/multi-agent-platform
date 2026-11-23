# Developer console

Single-page workflow viewer served at `/` (Jinja shell, vanilla JS, no build step).
It renders the conversation, a stage tracker, an agent graph with animated
handoffs, and the run timeline, all driven by the versioned HTTP/SSE contract.
It holds no orchestration rules and no provider credentials.

A frontend framework has not been chosen; revisit when the change-set review and
multi-user surfaces are designed.
