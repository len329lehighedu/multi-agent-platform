import copy
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


class Tweaked(ReplayProvider):
    """Replay provider that lets a test corrupt chosen responses before serving them."""

    def __init__(self, tweak=None, repeat_bad=False):
        super().__init__(FIXTURE)
        self.tweak, self.repeat_bad, self.requests = tweak, repeat_bad, []
        self._served: dict[str, int] = {}

    def generate(self, request):
        self.requests.append(request)
        response = super().generate(request)
        if self.tweak and request.agent_id == self.tweak[0]:
            n = self._served[request.agent_id] = self._served.get(request.agent_id, 0) + 1
            if n == 1 or self.repeat_bad:
                data = copy.deepcopy(response.structured_output)
                self.tweak[1](data)
                return ModelResponse(text=json.dumps(data), structured_output=data, usage=response.usage)
        return response


class Helpers(unittest.TestCase):
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

    def start(self, client, goal="Discover equations from pendulum data"):
        run = client.post("/api/v1/runs", json={"goal": goal}).get_json()
        response = client.post(f"/api/v1/runs/{run['id']}/chat", json={"content": goal})
        self.assertEqual(response.status_code, 202)
        return run["id"]

    def run_to_end(self, provider):
        client = self.make_client({"replay": provider})
        run_id = self.start(client)
        paused = self.wait_settled(client, run_id)
        self.assertEqual(paused["status"], "awaiting_user")
        client.post(f"/api/v1/runs/{run_id}/chat", json={"content": "Use built-in systems"})
        return client, run_id, self.wait_settled(client, run_id)


class WorkflowTests(Helpers):
    def test_pauses_for_question_then_produces_project_plan(self):
        client = self.make_client({"replay": ReplayProvider(FIXTURE)})
        run_id = self.start(client)
        paused = self.wait_settled(client, run_id)
        self.assertEqual(paused["stage"], "planning")
        self.assertIn("question.asked", [e["type"] for e in paused["events"]])
        self.assertNotIn("artifact.accepted", [e["type"] for e in paused["events"]])

        client.post(f"/api/v1/runs/{run_id}/chat", json={"content": "Use built-in systems"})
        done = self.wait_settled(client, run_id)

        self.assertEqual(done["status"], "ready_for_review")
        self.assertEqual(done["stage"], "review")
        events = done["events"]
        requested = [e["data"]["to"] for e in events if e["type"] == "handoff.requested"]
        returned = [e["data"]["from"] for e in events if e["type"] == "handoff.returned"]
        self.assertEqual(requested, ["researcher", "builder", "tester"])
        self.assertEqual(returned, requested)
        accepted = [e["data"]["name"] for e in events if e["type"] == "artifact.accepted"]
        self.assertEqual(accepted, ["task_spec", "research_brief", "design_spec", "test_plan", "project_plan"])
        self.assertIn("plan.ready", [e["type"] for e in events])
        self.assertEqual([e["sequence"] for e in events], list(range(1, len(events) + 1)))
        self.assertEqual(events[-1]["type"], "workflow.completed")
        self.assertFalse(events[-1]["data"]["built"])
        agents = [m["agent_id"] for m in done["messages"] if m["role"] == "agent"]
        self.assertEqual(agents, ["project_manager", "project_manager", "researcher", "builder", "tester", "project_manager"])

        plan_message = done["messages"][-1]["content"]
        for heading in ("PROJECT PLAN:", "What the module will do", "Algorithm:", "How success is defined",
                        "What you can do with the MVP", "Nothing has been built or run yet"):
            self.assertIn(heading, plan_message)
        stored = client.get(f"/api/v1/runs/{run_id}/artifacts").get_json()
        self.assertEqual(sorted(stored), sorted(accepted))
        self.assertTrue((Path(done["workspace_path"]) / "artifacts" / "project_plan.json").is_file())

    def test_skills_and_references_are_loaded_by_the_orchestrator(self):
        provider = Tweaked()
        _, _, done = self.run_to_end(provider)
        started = {}
        for e in done["events"]:
            if e["type"] == "agent.started":
                started.setdefault(e["data"]["agent_id"], []).append(e["data"])
        self.assertIn("model-selection", started["researcher"][0]["skills"])
        self.assertTrue(any("equation-discovery" in r for r in started["researcher"][0]["references"]))
        self.assertTrue(any("reference-layout" in r for r in started["builder"][0]["references"]))
        self.assertEqual(started["project_manager"][-1]["skills"], ["plan-synthesis", "stage-gating-and-handoff"])
        self.assertEqual(started["project_manager"][-1]["references"], [])
        self.assertGreater(started["researcher"][0]["prompt_tokens_est"], 800)

    def test_requests_use_artifacts_not_chat_history_and_json_mode(self):
        provider = Tweaked()
        self.run_to_end(provider)
        by_agent = {}
        for request in provider.requests:
            by_agent.setdefault(request.agent_id, []).append(request)
            self.assertTrue(request.metadata["json"])
            self.assertIn("json", request.messages[0]["content"].lower())
        self.assertEqual(by_agent["project_manager"][0].metadata["tier"], "strong")
        self.assertEqual(by_agent["researcher"][0].metadata["tier"], "fast")
        researcher_input = by_agent["researcher"][0].messages[0]["content"]
        self.assertIn("task_spec (accepted)", researcher_input)
        self.assertNotIn("Reply with one JSON", researcher_input)
        final_input = by_agent["project_manager"][-1].messages[0]["content"]
        self.assertIn("design_spec (accepted)", final_input)
        self.assertNotIn('"responsibility"', final_input)  # condensed, not the full design
        self.assertIn("artifact", by_agent["builder"][0].system_prompt)

    def test_invalid_artifact_gets_one_repair_then_succeeds(self):
        provider = Tweaked(("researcher", lambda data: data["artifact"].pop("oracle")))
        _, _, done = self.run_to_end(provider)

        self.assertEqual(done["status"], "ready_for_review")
        rejected = [e for e in done["events"] if e["type"] == "artifact.rejected"]
        self.assertEqual(len(rejected), 1)
        self.assertIn("oracle", " ".join(rejected[0]["data"]["errors"]))
        completed = [e for e in done["events"] if e["type"] == "agent.completed" and e["data"]["agent_id"] == "researcher"]
        self.assertEqual(completed[0]["data"]["attempts"], 2)
        repair = [r for r in provider.requests if r.agent_id == "researcher"][1]
        self.assertEqual(len(repair.messages), 3)

    def test_consistency_failure_is_caught_by_code_and_repaired(self):
        provider = Tweaked(("builder", lambda data: data["artifact"]["criteria_map"].pop()))
        _, _, done = self.run_to_end(provider)

        rejected = [e for e in done["events"] if e["type"] == "artifact.rejected"]
        self.assertEqual(done["status"], "ready_for_review")
        self.assertIn("AC5", " ".join(rejected[0]["data"]["errors"]))

    def test_second_failure_ends_the_run(self):
        provider = Tweaked(("tester", lambda data: data["artifact"].update(oracle_checks=[])), repeat_bad=True)
        _, _, done = self.run_to_end(provider)

        self.assertEqual(done["status"], "failed")
        self.assertEqual(done["events"][-1]["type"], "agent.failed")
        self.assertIn("rejected after repair", done["events"][-1]["data"]["error"])
        self.assertEqual(len([e for e in done["events"] if e["type"] == "artifact.rejected"]), 2)

    def test_plan_must_cover_every_criterion_and_name_the_researchers_algorithm(self):
        def tweak(data):
            data["artifact"]["algorithm"]["name"] = "Something else"
            data["artifact"]["success_definition"].pop()
        provider = Tweaked(("project_manager", None))
        provider.tweak = None
        calls = {"n": 0}
        original = provider.generate

        def generate(request):
            response = original(request)
            if request.agent_id == "project_manager" and response.structured_output.get("artifact") and "success_definition" in response.structured_output["artifact"]:
                calls["n"] += 1
                if calls["n"] == 1:
                    data = copy.deepcopy(response.structured_output)
                    tweak(data)
                    return ModelResponse(text=json.dumps(data), structured_output=data)
            return response
        provider.generate = generate
        _, _, done = self.run_to_end(provider)

        rejected = [e for e in done["events"] if e["type"] == "artifact.rejected"]
        self.assertEqual(done["status"], "ready_for_review")
        joined = " ".join(rejected[0]["data"]["errors"])
        self.assertIn("AC5", joined)
        self.assertIn("algorithm.name", joined)

    def test_cannot_resubmit_finished_run(self):
        client, run_id, _ = self.run_to_end(ReplayProvider(FIXTURE))
        response = client.post(f"/api/v1/runs/{run_id}/chat", json={"content": "again"})
        self.assertEqual(response.status_code, 400)

    def test_provider_failure_is_a_failed_run_with_event(self):
        client = self.make_client({"replay": FailingProvider()})
        run = self.wait_settled(client, self.start(client))

        self.assertEqual(run["status"], "failed")
        failure = run["events"][-1]
        self.assertEqual(failure["type"], "agent.failed")
        self.assertEqual(failure["data"]["agent_id"], "project_manager")
        self.assertIn("upstream unavailable", failure["data"]["error"])

    def test_unknown_provider_is_rejected(self):
        client = self.make_client({"replay": ReplayProvider(FIXTURE)})
        response = client.post("/api/v1/runs", json={"goal": "x", "provider": "nope"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(client.get("/api/v1/config").get_json()["default_provider"], "replay")

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

    def test_replay_provider_serves_responses_in_order_per_run(self):
        provider = ReplayProvider(FIXTURE)
        request = ModelRequest("r1", "project_manager", "", ())
        self.assertIsNotNone(provider.generate(request).structured_output["question"])
        self.assertIsNone(provider.generate(request).structured_output["question"])
        other = ModelRequest("r2", "project_manager", "", ())
        self.assertIsNotNone(provider.generate(other).structured_output["question"])


if __name__ == "__main__":
    unittest.main()
