"""Five-repeat engine and document callback benchmark; prints JSON evidence."""

import importlib.util
from importlib.metadata import version
import json
import platform
from pathlib import Path
import statistics
import sys
import time

import numpy as np
from bokeh.document import Document
from bokeh.events import ButtonClick
import bokeh


ROOT = Path(__file__).resolve().parents[1]
NAME = "_rl_gridworld_benchmark"
spec = importlib.util.spec_from_file_location(NAME, ROOT / "__init__.py", submodule_search_locations=[str(ROOT)])
package = importlib.util.module_from_spec(spec); sys.modules[NAME] = package; spec.loader.exec_module(package)
engine = __import__(NAME + ".engine", fromlist=["*"])
ui = __import__(NAME + ".ui", fromlist=["*"])


def stats(values):
    return {"repetitions": len(values), "seconds": values, "median_seconds": statistics.median(values), "min_seconds": min(values), "max_seconds": max(values)}


def benchmark_kernel():
    values = []
    item = engine.transition(12, 3, 0)
    for _ in range(5):
        q = engine.new_q_table(); started = time.perf_counter()
        for _ in range(20_000):
            engine.apply_q_update(q, item, .3, .95)
        values.append(time.perf_counter() - started)
    return stats(values)


def benchmark_training():
    values, transitions = [], []
    for _ in range(5):
        q = engine.new_q_table(); rng = np.random.default_rng(42); started = time.perf_counter()
        summaries = engine.train_episodes(q, rng, 500, .3, .95, .2)
        values.append(time.perf_counter() - started)
        transitions.append(sum(item.steps for item in summaries))
    return {**stats(values), "episodes": 500, "transition_counts": transitions, "maximum_allowed_transitions": 20_000}


def benchmark_callback():
    values = []
    for _ in range(5):
        doc = Document(); ui.build_document(doc)
        episode_widget = doc.select_one({"name": "episodes"}); episode_widget.value = 500
        button = doc.select_one({"name": "train_episodes"})
        started = time.perf_counter(); button._trigger_event(ButtonClick(model=button)); values.append(time.perf_counter() - started)
        assert len(doc.select_one({"name": "episode_curve_source"}).data["episode"]) == 500
    return {**stats(values), "episodes": 500, "includes_evaluation_and_model_publication": True}


if __name__ == "__main__":
    print(json.dumps({
        "runtime": {"python": platform.python_version(), "platform": platform.platform(), "machine": platform.machine(), "numpy": np.__version__, "bokeh": bokeh.__version__, "flask": version("flask")},
        "configuration": {"seed": 42, "alpha": .3, "gamma": .95, "epsilon": .2, "device": "CPU"},
        "kernel_20000_updates": benchmark_kernel(),
        "train_500_episodes": benchmark_training(),
        "callback_500_episodes": benchmark_callback(),
    }, indent=2))
