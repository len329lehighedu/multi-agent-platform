---
name: stem-flask-bokeh
description: Designs and verifies Flask HTML shells that embed Python-backed Bokeh server modules with reproducible local startup and deployment configuration.
---

# Flask and Bokeh integration

Use SINDy's `flask_app.py`, `main.py`, and `run.sh` as reference patterns, then adapt routes and startup to the new module. Flask serves the HTML shell; the browser also connects directly to the Bokeh server. Define local and hosted Bokeh URLs and allowed WebSocket origins consistently.

Keep imports and scientific computation testable without launching servers. Isolate dependency environments per generated module and document verified interpreter/package versions. Avoid carrying over pySINDy or other unrelated dependencies.

Choose a launcher that reports readiness/failure, cleans up both services, and works on the intended OS. Do not assume a fixed sleep establishes readiness. Keep debug/deployment settings explicit.

Verify Flask routes and template rendering, Bokeh app construction, and browser-to-Bokeh interaction. A Flask 200 response or successful `server_document` generation is insufficient evidence of a working WebSocket connection. Record actual launch and shutdown results.
