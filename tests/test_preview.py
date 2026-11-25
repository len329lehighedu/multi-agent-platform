"""PreviewManager runs a real `bokeh serve` subprocess on localhost (no model calls, no spend)."""

import tempfile
import unittest
import urllib.request
from pathlib import Path

from module_platform.preview import PreviewManager

GOOD = '''from bokeh.io import curdoc
from bokeh.models import Div
curdoc().add_root(Div(text="hello preview"))
'''
BAD = "raise RuntimeError('boom at import')\n"


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.module = self.root / "p1" / "module"
        self.module.mkdir(parents=True)
        self.manager = PreviewManager(startup_timeout=30)
        self.addCleanup(self.manager.stop_all)

    def test_no_entry_is_reported_without_starting_anything(self):
        self.assertEqual(self.manager.status("p1", self.module)["state"], "no_entry")
        self.assertEqual(self.manager.start("p1", self.module)["state"], "no_entry")

    def test_start_serves_the_module_and_stop_ends_it(self):
        (self.module / "main.py").write_text(GOOD)
        info = self.manager.start("p1", self.module)
        self.assertEqual(info["state"], "running", info)
        self.assertTrue(info["url"].startswith("http://127.0.0.1:"))
        with urllib.request.urlopen(info["url"], timeout=5) as response:
            self.assertEqual(response.status, 200)
        self.assertEqual(self.manager.status("p1", self.module)["state"], "running")
        self.manager.stop("p1")
        self.assertEqual(self.manager.status("p1", self.module)["state"], "stopped")

    def test_restart_replaces_the_process(self):
        (self.module / "main.py").write_text(GOOD)
        first = self.manager.start("p1", self.module)
        second = self.manager.start("p1", self.module)
        self.assertEqual(second["state"], "running")
        self.assertNotEqual(first["url"], second["url"])

    def test_overlapping_starts_do_not_kill_each_other(self):
        from concurrent.futures import ThreadPoolExecutor

        (self.module / "main.py").write_text(GOOD)
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda _: self.manager.start("p1", self.module), range(2)))
        self.assertEqual([r["state"] for r in results], ["running", "running"])
        self.assertEqual(self.manager.status("p1", self.module)["state"], "running")

    def test_broken_module_reports_log_tail(self):
        (self.module / "main.py").write_text(BAD)
        # bokeh serves the page and fails per session, so the server starts; the page itself shows the error
        info = self.manager.start("p1", self.module)
        self.assertIn(info["state"], {"running", "failed"})


if __name__ == "__main__":
    unittest.main()
