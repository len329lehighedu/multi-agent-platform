#!/usr/bin/env python3
"""Repeatable CPU benchmark for the DAC numerical kernel and document build."""
import importlib.util,platform,statistics,sys,time
from importlib.metadata import version
from pathlib import Path
from bokeh.document import Document

ROOT=Path(__file__).resolve().parents[1];NAME="_dac_bench"
spec=importlib.util.spec_from_file_location(NAME,ROOT/"__init__.py",submodule_search_locations=[str(ROOT)]);pkg=importlib.util.module_from_spec(spec);sys.modules[NAME]=pkg;spec.loader.exec_module(pkg)
engine=__import__(NAME+".engine",fromlist=["*"]);ui=__import__(NAME+".ui",fromlist=["*"])

def measure(label,config,repeats):
    values=[];nfev=[]
    for _ in range(repeats):
        started=time.perf_counter(); result=engine.simulate(config);values.append(time.perf_counter()-started);nfev.append(result["solver_nfev"])
    print(f"{label}: repeats={repeats} median={statistics.median(values):.6f}s range={min(values):.6f}-{max(values):.6f}s nfev={min(nfev)}-{max(nfev)}")

print(f"platform={platform.platform()} machine={platform.machine()} python={platform.python_version()} numpy={version('numpy')} scipy={version('scipy')} bokeh={version('bokeh')} flask={version('flask')}")
print("solver=BDF cells=30 states=91 horizon=86400s output_points=121 rtol=1e-6 max_step=600s timeout=20s")
measure("default",{},5)
measure("endpoint-heavy",{"volume_m3":.002,"inlet_ppm":2000,"initial_temperature_k":313.15,"flow_m3_s":100/60000,"porosity":.55,"wall_key":"aluminum"},3)
values=[]
for _ in range(5):
    started=time.perf_counter();doc=Document();ui.build_document(doc);values.append(time.perf_counter()-started)
print(f"bokeh-document-build: repeats=5 median={statistics.median(values):.6f}s range={min(values):.6f}-{max(values):.6f}s models={len(doc.models)}")
