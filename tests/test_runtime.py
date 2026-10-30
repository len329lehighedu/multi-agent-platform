"""Verify the reusable scaffold, web integration and actual process lifecycle."""

import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.error import URLError
from urllib.request import urlopen

from bokeh.document import Document

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from create_module import create
from stem_platform.runtime import create_app, load_document_builder, module_metadata


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / "templates/module-scaffold", self.root / "templates/module-scaffold")
        shutil.copytree(ROOT / "web", self.root / "web")
        create("starter", "A working starter", self.root)

    def test_scaffold_runs_and_does_not_overwrite(self):
        with self.assertRaises(FileExistsError):
            create("starter", "Other", self.root)
        with self.assertRaises(ValueError):
            create("../outside", "Other", self.root)
        builder = load_document_builder(self.root, "starter")
        first, second = Document(), Document()
        builder(first)
        builder(second)
        a = first.get_model_by_name("coefficient")
        b = second.get_model_by_name("coefficient")
        a.value = 3
        self.assertEqual(first.get_model_by_name("exploration").data["y"][-1], 30)
        self.assertEqual(b.value, 1)
        self.assertEqual(second.get_model_by_name("exploration").data["y"][-1], 10)

    def test_flask_shell_health_content_and_escaping(self):
        metadata_path = self.root / "modules/starter/module.json"
        data = json.loads(metadata_path.read_text())
        data["title"] = "<script>alert(1)</script>"
        metadata_path.write_text(json.dumps(data))
        client = create_app(self.root).test_client()
        self.assertEqual(client.get("/health").json, {"status": "ok", "modules": ["starter"]})
        response = client.get("/modules/starter/")
        self.assertEqual(response.status_code, 200)
        text = response.get_data(as_text=True)
        self.assertIn("&lt;script&gt;", text)
        self.assertNotIn("<script>alert(1)", text)
        self.assertEqual(text.count("<details>"), 3)
        self.assertIn("/lesson/starter/autoload.js", text)
        self.assertEqual(client.get("/modules/missing/").status_code, 404)
        asset = client.get("/static/lesson.css")
        self.assertEqual(asset.status_code, 200)
        asset.close()

    def test_metadata_requires_feedback_and_valid_id(self):
        with self.assertRaises(ValueError):
            module_metadata(self.root, "../starter")
        path = self.root / "modules/starter/module.json"
        data = json.loads(path.read_text())
        data["questions"] = []
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "three questions"):
            module_metadata(self.root, "starter")

    def launch(self, port, bokeh_port):
        command = [sys.executable, "-u", "-c",
                   "from pathlib import Path; import sys; from stem_platform.runtime import serve; "
                   "serve(Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]))",
                   str(self.root), str(port), str(bokeh_port)]
        process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        def cleanup():
            if process.poll() is None:
                process.kill()
            process.communicate()
        self.addCleanup(cleanup)
        return process

    def test_real_startup_both_endpoints_and_shutdown(self):
        port, backend = free_port(), free_port()
        while backend == port:
            backend = free_port()
        process = self.launch(port, backend)
        deadline = time.monotonic() + 25
        for url in (f"http://127.0.0.1:{port}/health", f"http://127.0.0.1:{backend}/lesson/starter"):
            while True:
                try:
                    with urlopen(url, timeout=1) as response:
                        self.assertEqual(response.status, 200)
                    break
                except (URLError, TimeoutError, ConnectionError):
                    if process.poll() is not None:
                        self.fail(process.communicate()[0])
                    if time.monotonic() > deadline:
                        self.fail("Services did not become ready")
                    time.sleep(.1)
        process.send_signal(signal.SIGTERM)
        output, _ = process.communicate(timeout=10)
        self.assertEqual(process.returncode, 0, output)
        self.assertIn("STOPPED", output)
        for value in (port, backend):
            with socket.socket() as sock:
                self.assertNotEqual(sock.connect_ex(("127.0.0.1", value)), 0)

    def test_partial_startup_failure_releases_web_port(self):
        port = free_port()
        with socket.socket() as occupied:
            occupied.bind(("127.0.0.1", 0))
            occupied.listen()
            process = self.launch(port, occupied.getsockname()[1])
            output, _ = process.communicate(timeout=15)
        self.assertNotEqual(process.returncode, 0, output)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", port))


if __name__ == "__main__":
    unittest.main()
