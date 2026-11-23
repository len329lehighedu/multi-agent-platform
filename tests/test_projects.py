import unittest
from pathlib import Path

from test_build import BROKEN, Scripted, reply
from test_workflow import Helpers, Tweaked

ENGINE = "engine/sindy_model.py"


class ProjectTests(Helpers):
    def project(self, client, name="Pendulum"):
        response = client.post("/api/v1/projects", json={"name": name})
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()

    def feature_run(self, client, project_id, goal="Add a bootstrap tab"):
        run = client.post("/api/v1/runs", json={"goal": goal, "project_id": project_id}).get_json()
        client.post(f"/api/v1/runs/{run['id']}/chat", json={"content": goal})
        paused = self.wait_settled(client, run["id"])
        if paused["status"] == "awaiting_user":
            client.post(f"/api/v1/runs/{run['id']}/chat", json={"content": "Use built-in systems"})
            self.wait_settled(client, run["id"])
        return run["id"]

    def test_projects_need_distinct_names(self):
        client = self.make_client({"replay": Tweaked()})
        self.project(client, "Pendulum")
        self.assertEqual(client.post("/api/v1/projects", json={"name": " pendulum "}).status_code, 400)
        self.assertEqual(client.post("/api/v1/projects", json={"name": "  "}).status_code, 400)
        self.assertEqual(client.get("/api/v1/projects/" + "0" * 32).status_code, 404)
        self.assertEqual(len(client.get("/api/v1/projects").get_json()["items"]), 1)

    def test_run_in_a_project_builds_into_the_project_module(self):
        client = self.make_client({"replay": Tweaked()})
        project = self.project(client)
        run_id = self.feature_run(client, project["id"], "Build the module")
        run = client.get(f"/api/v1/runs/{run_id}").get_json()
        self.assertEqual((run["kind"], run["project_id"]), ("module", project["id"]))
        client.post(f"/api/v1/runs/{run_id}/approve")
        self.wait_settled(client, run_id)
        summary = client.get(f"/api/v1/projects/{project['id']}").get_json()
        self.assertEqual((summary["versions"], summary["run_count"]), (1, 1))
        self.assertGreater(summary["files"], 10)
        self.assertIn(ENGINE, [f["path"] for f in client.get(f"/api/v1/runs/{run_id}/files").get_json()["items"]])

    def test_new_run_in_a_built_project_is_a_feature_that_sees_existing_files(self):
        provider = Tweaked()
        client = self.make_client({"replay": provider})
        project = self.project(client)
        first = self.feature_run(client, project["id"], "Build the module")
        client.post(f"/api/v1/runs/{first}/approve")
        self.wait_settled(client, first)
        before = len(provider.requests)
        second = self.feature_run(client, project["id"], "Add a bootstrap tab")
        run = client.get(f"/api/v1/runs/{second}").get_json()
        self.assertEqual(run["kind"], "feature")
        self.assertEqual(run["module_path"], client.get(f"/api/v1/runs/{first}").get_json()["module_path"])
        planning = [r for r in provider.requests[before:] if r.agent_id == "project_manager"]
        first_prompt = planning[0].messages[0]["content"]
        self.assertIn("NEW FEATURE", first_prompt)
        self.assertIn("- engine/sindy_model.py", first_prompt)
        self.assertIn("Build the module", first_prompt)

    def test_two_modules_cannot_both_be_built_into_one_project(self):
        client = self.make_client({"replay": Tweaked()})
        project = self.project(client)
        a = self.feature_run(client, project["id"], "First")
        b = self.feature_run(client, project["id"], "Second")
        client.post(f"/api/v1/runs/{a}/approve")
        self.wait_settled(client, a)
        response = client.post(f"/api/v1/runs/{b}/approve")
        self.assertEqual(response.status_code, 400)
        self.assertIn("new feature", response.get_json()["error"]["message"])

    def test_failed_feature_restores_the_module(self):
        class Failing(Scripted):
            def generate(inner, request):
                key = request.metadata.get("key", "")
                if key == "file_set:repair":
                    return reply({ENGINE: BROKEN}, "break the engine")
                response = super().generate(request)
                if key == "file_set:build" and "Existing module files" in request.messages[0]["content"]:
                    for item in response.structured_output["artifact"]["files"]:
                        if item["path"] == ENGINE:
                            item["content"] = BROKEN
                return response

        client = self.make_client({"replay": Failing()})
        project = self.project(client)
        first = self.feature_run(client, project["id"], "Build the module")
        client.post(f"/api/v1/runs/{first}/approve")
        self.wait_settled(client, first)
        good = client.get(f"/api/v1/runs/{first}/files/{ENGINE}").data
        second = self.feature_run(client, project["id"], "Add a bootstrap tab")
        client.post(f"/api/v1/runs/{second}/approve")
        run = self.wait_settled(client, second)
        self.assertEqual(run["status"], "needs_review")
        failed = next(e for e in run["events"] if e["type"] == "build.failed")
        self.assertTrue(failed["data"]["rolled_back"])
        self.assertEqual(client.get(f"/api/v1/runs/{second}/files/{ENGINE}").data, good)
        self.assertEqual(client.post(f"/api/v1/runs/{second}/chat", json={"content": "fix it"}).status_code, 400)
        self.assertEqual(client.get(f"/api/v1/projects/{project['id']}").get_json()["versions"], 1)

    def test_deleting_a_project_removes_module_and_runs(self):
        client = self.make_client({"replay": Tweaked()})
        project = self.project(client)
        run_id = self.feature_run(client, project["id"], "Build the module")
        client.post(f"/api/v1/runs/{run_id}/approve")
        self.wait_settled(client, run_id)
        module = Path(client.get(f"/api/v1/runs/{run_id}").get_json()["module_path"])
        other = self.project(client, "Other")
        self.assertTrue(module.is_dir())
        response = client.delete(f"/api/v1/projects/{project['id']}")
        self.assertEqual((response.status_code, response.get_json()["runs_removed"]), (200, 1))
        self.assertFalse(module.exists())
        self.assertEqual(client.get(f"/api/v1/runs/{run_id}").status_code, 404)
        self.assertEqual(client.get(f"/api/v1/projects/{project['id']}").status_code, 404)
        self.assertEqual([p["id"] for p in client.get("/api/v1/projects").get_json()["items"]], [other["id"]])

    def test_cannot_delete_a_project_while_a_run_is_working(self):
        client = self.make_client({"replay": Tweaked()})
        project = self.project(client)
        run = client.post("/api/v1/runs", json={"goal": "x", "project_id": project["id"]}).get_json()
        client.post(f"/api/v1/runs/{run['id']}/chat", json={"content": "x"})
        response = client.delete(f"/api/v1/projects/{project['id']}")
        self.assertEqual(response.status_code, 400)
        self.assertIn("still working", response.get_json()["error"]["message"])
        self.wait_settled(client, run["id"])


if __name__ == "__main__":
    unittest.main()
