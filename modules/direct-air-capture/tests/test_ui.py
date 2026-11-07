"""Bokeh construction, state isolation, metadata, and platform checks."""
import importlib.util,json
from pathlib import Path
import sys,unittest
from bokeh.document import Document
from bokeh.events import ButtonClick
from bokeh.models import Column
from unittest.mock import patch

MODULE_ROOT=Path(__file__).resolve().parents[1]; PROJECT_ROOT=MODULE_ROOT.parents[1]; NAME="_dac_ui_tests"
spec=importlib.util.spec_from_file_location(NAME,MODULE_ROOT/"__init__.py",submodule_search_locations=[str(MODULE_ROOT)])
package=importlib.util.module_from_spec(spec);sys.modules[NAME]=package;spec.loader.exec_module(package)
ui=__import__(NAME+".ui",fromlist=["*"])
engine=__import__(NAME+".engine",fromlist=["*"])
sys.path.insert(0,str(PROJECT_ROOT))
from stem_platform.runtime import create_app,discover_modules


def model(doc,name): return doc.select_one({"name":name})


class UiTests(unittest.TestCase):
    def test_document_contract_and_isolation(self):
        first,second=Document(),Document();ui.build_document(first);ui.build_document(second)
        self.assertFalse(set(first.models)&set(second.models))
        names=["volume_l","inlet_ppm","initial_temperature_c","flow_l_min","porosity","wall_material","run_simulation","reset_simulation","selected_time","status","time_source","profile_source","metrics","model_details"]
        for name in names: self.assertIsNotNone(model(first,name),name)
        # Keep narrow-screen geometry inside Bokeh's layout engine. CSS-reflowed
        # Rows can retain desktop height and intercept later controls.
        for name in ("controls_and_settings","time_plots","profile_plots"):
            self.assertIsInstance(model(first,name),Column)
        model(first,"volume_l").value=1.2
        self.assertEqual(model(second,"volume_l").value,.5)
        self.assertIn("pending",model(first,"status").text.lower()) if model(first,"time_source").data["time_h"] else None
        self.assertTrue(model(first,"selected_time").disabled)

    def test_atomic_publication_pending_slider_and_failure(self):
        class FakeJob:
            instances=[]
            def __init__(self,payload,done): self.payload=payload;self.done=done;self.cancelled=False;self.instances.append(self)
            def start(self): return self
            def cancel(self): self.cancelled=True
        doc=Document()
        with patch.object(ui,"WorkerJob",FakeJob):
            ui.build_document(doc)
            button=model(doc,"run_simulation");button._trigger_event(ButtonClick(model=button))
            self.assertTrue(button.disabled);self.assertEqual(len(FakeJob.instances),1)
            result=engine.simulate({**FakeJob.instances[-1].payload["config"],"horizon_s":3600,"output_points":21})
            result["worker_seconds"]=.1;FakeJob.instances[-1].done({"ok":True,"result":result})
            for callback in list(doc.session_callbacks):
                if callback.__class__.__name__=="NextTickCallback": doc.remove_next_tick_callback(callback);callback.callback()
            self.assertEqual(len(model(doc,"time_source").data["time_h"]),21)
            self.assertEqual(len(model(doc,"profile_source").data["z_m"]),30)
            self.assertIn("Closure",model(doc,"metrics").text);self.assertFalse(model(doc,"selected_time").disabled)
            old_metrics=model(doc,"metrics").text
            model(doc,"volume_l").value=.8;self.assertIn("pending",model(doc,"status").text.lower())
            button._trigger_event(ButtonClick(model=button));FakeJob.instances[-1].done({"ok":False,"error":"controlled failure"})
            for callback in list(doc.session_callbacks):
                if callback.__class__.__name__=="NextTickCallback": doc.remove_next_tick_callback(callback);callback.callback()
            self.assertEqual(model(doc,"metrics").text,old_metrics);self.assertIn("failed",model(doc,"status").text.lower())

    def test_metadata_discovery_and_route(self):
        metadata=json.loads((MODULE_ROOT/"module.json").read_text())
        self.assertEqual(metadata["id"],"direct-air-capture")
        self.assertGreaterEqual(len(metadata["objectives"]),6);self.assertGreaterEqual(len(metadata["questions"]),6)
        ids={item["id"] for item in discover_modules(PROJECT_ROOT)};self.assertIn("direct-air-capture",ids)
        client=create_app(PROJECT_ROOT).test_client()
        self.assertEqual(client.get("/modules/direct-air-capture/").status_code,200)
        self.assertIn("Direct Air Capture Packed-Bed Lab",client.get("/").get_data(as_text=True))


if __name__=="__main__":unittest.main()
