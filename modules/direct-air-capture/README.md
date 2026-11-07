# Direct Air Capture Packed-Bed Lab

An interactive, deterministic adsorption-phase model for undergraduate chemical-engineering learning. It couples a Toth adsorption rate to one-dimensional gas CO2 and packed-bed energy balances. This is an illustrative model, not a validated equipment-design tool.

## Run

From the platform root with the verified environment:

```bash
.venv/bin/python scripts/serve.py
```

Open `http://127.0.0.1:8080/modules/direct-air-capture/`. The browser connects to Flask on port 8080 and the Bokeh server on port 5006.

## Scientific and numerical scope

SI units internally; 30 first-order upwind finite volumes; 24-hour horizon; SciPy BDF (`rtol=1e-6`, component absolute tolerances, maximum internal step 600 s). The initial regenerated bed contains feed gas and zero solid loading. Dry air, constant properties, no pressure drop/dispersion/radial gradients/humidity/degradation/regeneration. Wall choices map to assumed effective coefficients. Toth parameters follow Bos et al., DOI 10.1016/j.cej.2018.11.072, but the ambient-pressure kinetic scale is pedagogical and unvalidated.

## Verify

```bash
.venv/bin/python -m unittest discover -s modules/direct-air-capture/tests -p 'test_*.py' -v
.venv/bin/python modules/direct-air-capture/tests/benchmark.py
.venv/bin/python scripts/test_all.py
```

Numerical mass closure demonstrates accounting consistency under this model; it does not validate real DAC performance, lifecycle removal, or storage permanence.
