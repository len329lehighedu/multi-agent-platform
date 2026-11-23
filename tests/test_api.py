import json
import tempfile
import unittest
from pathlib import Path

from module_platform.api import create_app
from module_platform.providers import ReplayProvider


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        replay = ReplayProvider(PROJECT_ROOT / "config" / "replay" / "demo.json")
        app = create_app(PROJECT_ROOT, Path(self.temporary.name), providers={"replay": replay}, stream_poll=0.01)
        app.testing = True
        self.client = app.test_client()

    def tearDown(self):
        self.temporary.cleanup()

    def create_run(self):
        response = self.client.post("/api/v1/runs", json={"goal": "Build a kinetics module"})
        self.assertEqual(response.status_code, 201)
        return response.get_json()

    def test_health(self):
        response = self.client.get("/api/v1/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_agent_catalog_hides_prompts(self):
        response = self.client.get("/api/v1/agents")

        self.assertEqual(response.status_code, 200)
        agents = response.get_json()["items"]
        self.assertEqual(agents[0]["id"], "orchestrator")
        self.assertNotIn("prompt", agents[0])

    def test_run_message_transition_and_event_cursor(self):
        run = self.create_run()
        self.assertEqual(run["stage"], "intake")
        self.assertTrue(Path(run["workspace_path"], "module").is_dir())

        response = self.client.post(
            f"/api/v1/runs/{run['id']}/messages",
            json={"content": "Use a packed-bed example", "target_agent": "scientific_architect"},
        )
        self.assertEqual(response.status_code, 201)

        response = self.client.post(
            f"/api/v1/runs/{run['id']}/transitions",
            json={"stage": "planning", "reason": "brief captured"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["stage"], "planning")

        response = self.client.get(f"/api/v1/runs/{run['id']}/events?after=2")
        events = response.get_json()["items"]
        self.assertTrue(events)
        self.assertTrue(all(event["sequence"] > 2 for event in events))

    def test_validation_errors_are_structured(self):
        response = self.client.post("/api/v1/runs", data=json.dumps({}), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "invalid_request")

        response = self.client.post("/api/v1/runs", json=["not", "an", "object"])
        self.assertEqual(response.status_code, 400)

        run = self.create_run()
        response = self.client.post(
            f"/api/v1/runs/{run['id']}/messages",
            json={"content": "hello", "target_agent": "imaginary"},
        )
        self.assertEqual(response.status_code, 400)

    def test_missing_run_is_404(self):
        response = self.client.get("/api/v1/runs/" + "a" * 32)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"]["code"], "run_not_found")


if __name__ == "__main__":
    unittest.main()
