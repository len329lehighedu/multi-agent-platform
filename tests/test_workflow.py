import json
import tempfile
import time
import unittest
from pathlib import Path

from module_platform.api import create_app
from module_platform.providers import ReplayProvider
from module_platform.providers.base import ModelRequest, ModelResponse, ProviderError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = PROJECT_ROOT / "config" / "replay" / "demo.json"


class FailingProvider:
    def generate(self, request: ModelRequest) -> ModelResponse:
        raise ProviderError("upstream unavailable")


class WorkflowTests(unittest.TestCase):
    def make_client(self, providers):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        app = create_app(PROJECT_ROOT, Path(temporary.name), providers=providers, stream_poll=0.01)
        app.testing = True
        return app.test_client()

    def wait_settled(self, client, run_id):
        for _ in range(300):
            run = client.get(f"/api/v1/runs/{run_id}").get_json()
            if run["status"] != "active":
                return run
            time.sleep(0.01)
        self.fail("run did not settle")

    def start(self, client, goal="Fit a SINDy model to pendulum data"):
        run = client.post("/api/v1/runs", json={"goal": goal}).get_json()
        response = client.post(f"/api/v1/runs/{run['id']}/chat", json={"content": goal})
        self.assertEqual(response.status_code, 202)
        return run["id"]

    def test_pauses_for_question_then_resumes_to_plan_ready(self):
        client = self.make_client({"replay": ReplayProvider(FIXTURE)})
        run_id = self.start(client)

        paused = self.wait_settled(client, run_id)
        self.assertEqual(paused["status"], "awaiting_user")
        self.assertEqual(paused["stage"], "planning")
        types = [e["type"] for e in paused["events"]]
        self.assertIn("question.asked", types)
        self.assertNotIn("handoff.returned", types)

        response = client.post(f"/api/v1/runs/{run_id}/chat", json={"content": "Use a built-in pendulum"})
        self.assertEqual(response.status_code, 202)
        done = self.wait_settled(client, run_id)

        self.assertEqual(done["status"], "ready_for_review")
        self.assertEqual(done["stage"], "review")
        events = done["events"]
        returned = [e["data"]["from"] for e in events if e["type"] == "handoff.returned"]
        self.assertEqual(returned, ["learning_planner", "scientific_architect", "builder", "qa_reviewer"])
        requested = [e["data"]["to"] for e in events if e["type"] == "handoff.requested"]
        self.assertEqual(requested, returned)
        self.assertEqual([e["sequence"] for e in events], list(range(1, len(events) + 1)))
        self.assertEqual(events[-1]["type"], "workflow.completed")
        self.assertFalse(events[-1]["data"]["built"])
        agents = [m["agent_id"] for m in done["messages"] if m["role"] == "agent"]
        self.assertEqual(agents, ["learning_planner", "learning_planner", "scientific_architect", "builder", "qa_reviewer", "orchestrator"])

    def test_cannot_resubmit_finished_run_or_message_while_active(self):
        client = self.make_client({"replay": ReplayProvider(FIXTURE)})
        run_id = self.start(client)
        self.wait_settled(client, run_id)
        client.post(f"/api/v1/runs/{run_id}/chat", json={"content": "pendulum"})
        self.wait_settled(client, run_id)

        response = client.post(f"/api/v1/runs/{run_id}/chat", json={"content": "again"})
        self.assertEqual(response.status_code, 400)

    def test_provider_failure_is_a_failed_run_with_event(self):
        client = self.make_client({"replay": FailingProvider()})
        run_id = self.start(client)

        run = self.wait_settled(client, run_id)

        self.assertEqual(run["status"], "failed")
        failure = run["events"][-1]
        self.assertEqual(failure["type"], "agent.failed")
        self.assertEqual(failure["data"]["agent_id"], "learning_planner")
        self.assertIn("upstream unavailable", failure["data"]["error"])

    def test_unknown_provider_is_rejected(self):
        client = self.make_client({"replay": ReplayProvider(FIXTURE)})
        response = client.post("/api/v1/runs", json={"goal": "x", "provider": "nope"})
        self.assertEqual(response.status_code, 400)
        config = client.get("/api/v1/config").get_json()
        self.assertEqual(config["default_provider"], "replay")

    def test_event_stream_replays_from_cursor_and_ends_when_paused(self):
        client = self.make_client({"replay": ReplayProvider(FIXTURE)})
        run_id = self.start(client)
        self.wait_settled(client, run_id)

        body = client.get(f"/api/v1/runs/{run_id}/events/stream?after=0").get_data(as_text=True)
        sequences = [int(line.split(": ")[1]) for line in body.splitlines() if line.startswith("id: ")]
        self.assertEqual(sequences, sorted(sequences))
        self.assertTrue(body.rstrip().endswith("event: end\ndata: {}"))
        payloads = [json.loads(line[6:]) for line in body.splitlines() if line.startswith("data: ") and line != "data: {}"]
        self.assertEqual(payloads[-1]["type"], "workflow.paused")

        tail = client.get(f"/api/v1/runs/{run_id}/events/stream?after={sequences[-1]}").get_data(as_text=True)
        self.assertEqual(tail.strip(), "event: end\ndata: {}")

    def test_every_request_mentions_json_in_input_for_json_mode_providers(self):
        seen = []

        class Recorder(ReplayProvider):
            def generate(self, request):
                seen.append(request)
                return super().generate(request)

        client = self.make_client({"replay": Recorder(FIXTURE)})
        run_id = self.start(client)
        self.wait_settled(client, run_id)
        client.post(f"/api/v1/runs/{run_id}/chat", json={"content": "pendulum"})
        self.wait_settled(client, run_id)

        self.assertEqual(len(seen), 6)
        for request in seen:
            self.assertTrue(request.metadata["json"])
            self.assertIn("json", request.messages[0]["content"].lower())

    def test_replay_provider_serves_responses_in_order_per_run(self):
        provider = ReplayProvider(FIXTURE)
        request = ModelRequest("r1", "learning_planner", "", ())
        self.assertIsNotNone(provider.generate(request).structured_output["question"])
        self.assertIsNone(provider.generate(request).structured_output["question"])
        other = ModelRequest("r2", "learning_planner", "", ())
        self.assertIsNotNone(provider.generate(other).structured_output["question"])


if __name__ == "__main__":
    unittest.main()
