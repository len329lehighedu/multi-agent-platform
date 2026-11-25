import json
import time
import unittest
from pathlib import Path

from module_platform import artifacts as checks
from module_platform.providers.base import ModelResponse
from test_workflow import FIXTURE, Helpers, Tweaked

ENGINE = "engine/sindy_model.py"
BROKEN = "def fit_line(xs, ys):\n    return 0.0, 0.0\n"


def reply(files, notes="test edit", message="Edited files."):
    data = {"message": message, "question": None, "handoff_summary": message,
            "artifact": {"files": [{"path": p, "content": c} for p, c in files.items()], "notes": notes}}
    return ModelResponse(text=json.dumps(data), structured_output=data, usage={})


class Scripted(Tweaked):
    """Replay provider whose Builder answers to build, repair and revision requests can be scripted by a test."""

    def __init__(self, on_build=None, on_repair=None, on_revision=None):
        super().__init__()
        self.handlers = {"build": on_build, "repair": on_repair, "revision": on_revision}
        self.builder_calls = []

    def generate(self, request):
        key = request.metadata.get("key", "")
        if request.agent_id == "builder" and key.startswith("file_set:"):
            kind = key.split(":")[1]
            self.builder_calls.append(kind)
            self.requests.append(request)
            if self.handlers.get(kind):
                return self.handlers.get(kind)(request.messages[0]["content"])
        return super().generate(request)


class BuildTests(Helpers):
    def planned(self, provider):
        client, run_id, plan = self.run_to_end(provider)
        self.assertEqual(plan["status"], "ready_for_review")
        return client, run_id

    def get_run(self, client, run_id):
        return client.get(f"/api/v1/runs/{run_id}").get_json()

    def types(self, run):
        return [e["type"] for e in run["events"]]

    def test_cannot_approve_without_a_plan(self):
        client = self.make_client({"replay": Tweaked()})
        run = client.post("/api/v1/runs", json={"goal": "x"}).get_json()
        self.assertEqual(client.post(f"/api/v1/runs/{run['id']}/approve").status_code, 400)

    def test_chat_before_approval_explains_what_to_do(self):
        client, run_id = self.planned(Tweaked())
        response = client.post(f"/api/v1/runs/{run_id}/chat", json={"content": "make it blue"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("approve", response.get_json()["error"]["message"])

    def test_approval_builds_runs_tests_and_verifies(self):
        client, run_id = self.planned(Tweaked())
        self.assertEqual(client.post(f"/api/v1/runs/{run_id}/approve").status_code, 202)
        run = self.wait_settled(client, run_id)
        types = self.types(run)
        self.assertEqual(run["status"], "ready_for_review")
        self.assertEqual(run["stage"], "review")
        for expected in ("plan.approved", "build.files_written", "build.checks", "build.completed"):
            self.assertIn(expected, types)
        self.assertLess(types.index("plan.approved"), types.index("build.files_written"))
        self.assertLess(types.index("build.files_written"), types.index("build.checks"))
        checked = next(e for e in run["events"] if e["type"] == "build.checks")
        self.assertTrue(checked["data"]["passed"], checked["data"]["output"])
        files = client.get(f"/api/v1/runs/{run_id}/files").get_json()["items"]
        self.assertIn(ENGINE, [f["path"] for f in files])
        self.assertTrue(client.get(f"/api/v1/runs/{run_id}/files/{ENGINE}").data.decode().startswith('"""Demo stub'))
        self.assertEqual(client.get(f"/api/v1/runs/{run_id}/files/../run.json").status_code, 400)
        self.assertIn("qa_report", client.get(f"/api/v1/runs/{run_id}/artifacts").get_json())
        last = run["messages"][-1]
        self.assertIn("Automated checks: PASSED", last["content"])
        self.assertIn("Tell me what to change", last["content"])
        self.assertEqual(client.post(f"/api/v1/runs/{run_id}/approve").status_code, 400)

    def test_user_can_request_a_change_after_the_build(self):
        provider = Scripted()
        client, run_id = self.planned(provider)
        client.post(f"/api/v1/runs/{run_id}/approve")
        self.wait_settled(client, run_id)
        response = client.post(f"/api/v1/runs/{run_id}/chat", json={"content": "The Train page looks plain, make it clearer"})
        self.assertEqual(response.status_code, 202)
        run = self.wait_settled(client, run_id)
        self.assertEqual(run["status"], "ready_for_review")
        self.assertIn("revision.completed", self.types(run))
        self.assertEqual(provider.builder_calls[-1], "revision")
        page = client.get(f"/api/v1/runs/{run_id}/files/tabs/train_tab.py").data.decode()
        self.assertIn("Train a model", page)
        revision_request = next(r for r in provider.requests if r.agent_id == "builder" and "Change request" in r.messages[0]["content"])
        self.assertIn("The Train page looks plain", revision_request.messages[0]["content"])
        self.assertIn("--- engine/sindy_model.py", revision_request.messages[0]["content"])

    def test_failing_build_is_repaired_from_real_test_output(self):
        def broken_build(_text):
            from_fixture = json.loads(FIXTURE.read_text())["builder"][1]
            for item in from_fixture["artifact"]["files"]:
                if item["path"] == ENGINE:
                    item["content"] = BROKEN
            return ModelResponse(text=json.dumps(from_fixture), structured_output=from_fixture, usage={})

        fixed = json.loads(FIXTURE.read_text())["builder"][1]["artifact"]["files"]
        original = next(i["content"] for i in fixed if i["path"] == ENGINE)

        def repair(text):
            self.assertIn("test_fit_recovers_known_line", text)
            return reply({ENGINE: original}, "restored the least-squares fit")

        provider = Scripted(on_build=broken_build, on_repair=repair)
        client, run_id = self.planned(provider)
        client.post(f"/api/v1/runs/{run_id}/approve")
        run = self.wait_settled(client, run_id)
        results = [e["data"]["passed"] for e in run["events"] if e["type"] == "build.checks"]
        self.assertEqual(results, [False, True])
        self.assertIn("build.completed", self.types(run))
        self.assertEqual(provider.builder_calls.count("repair"), 1)

    def test_unfixable_build_ends_in_needs_review_not_success(self):
        def broken_build(_text):
            data = json.loads(FIXTURE.read_text())["builder"][1]
            for item in data["artifact"]["files"]:
                if item["path"] == ENGINE:
                    item["content"] = BROKEN
            return ModelResponse(text=json.dumps(data), structured_output=data, usage={})

        provider = Scripted(on_build=broken_build, on_repair=lambda _t: reply({ENGINE: BROKEN}))
        client, run_id = self.planned(provider)
        client.post(f"/api/v1/runs/{run_id}/approve")
        run = self.wait_settled(client, run_id)
        self.assertEqual(run["status"], "needs_review")
        self.assertIn("build.failed", self.types(run))
        self.assertNotIn("build.completed", self.types(run))
        self.assertEqual(provider.builder_calls.count("repair"), 2)
        self.assertNotIn("PASSED", run["messages"][-1]["content"])

    def test_change_request_works_after_a_build_that_failed_its_tests(self):
        original = next(i["content"] for i in json.loads(FIXTURE.read_text())["builder"][1]["artifact"]["files"] if i["path"] == ENGINE)

        def broken_build(_text):
            data = json.loads(FIXTURE.read_text())["builder"][1]
            for item in data["artifact"]["files"]:
                if item["path"] == ENGINE:
                    item["content"] = BROKEN
            return ModelResponse(text=json.dumps(data), structured_output=data, usage={})

        provider = Scripted(on_build=broken_build, on_repair=lambda _t: reply({ENGINE: BROKEN}),
                            on_revision=lambda _t: reply({ENGINE: original}, "restored the fit"))
        client, run_id = self.planned(provider)
        client.post(f"/api/v1/runs/{run_id}/approve")
        run = self.wait_settled(client, run_id)
        self.assertEqual(run["status"], "needs_review")
        self.assertEqual(run["stage"], "review")
        response = client.post(f"/api/v1/runs/{run_id}/chat", json={"content": "fix the fit so the tests pass"})
        self.assertEqual(response.status_code, 202)
        run = self.wait_settled(client, run_id)
        self.assertNotIn("agent.failed", self.types(run))
        self.assertIn("revision.completed", self.types(run))

    def test_revision_that_breaks_tests_is_rolled_back(self):
        provider = Scripted(on_revision=lambda _t: reply({ENGINE: BROKEN}), on_repair=lambda _t: reply({ENGINE: BROKEN}))
        client, run_id = self.planned(provider)
        client.post(f"/api/v1/runs/{run_id}/approve")
        self.wait_settled(client, run_id)
        before = client.get(f"/api/v1/runs/{run_id}/files/{ENGINE}").data.decode()
        client.post(f"/api/v1/runs/{run_id}/chat", json={"content": "make the fit faster"})
        run = self.wait_settled(client, run_id)
        self.assertEqual(run["status"], "ready_for_review")
        self.assertIn("revision.failed", self.types(run))
        self.assertNotIn("revision.completed", self.types(run))
        self.assertEqual(client.get(f"/api/v1/runs/{run_id}/files/{ENGINE}").data.decode(), before)
        self.assertIn("restored", run["messages"][-1]["content"])


class FileSetChecks(unittest.TestCase):
    def test_rejects_unsafe_paths_and_types(self):
        bad = {"files": [{"path": "../x.py", "content": "x"}, {"path": "/etc/a.py", "content": "x"}, {"path": "run.exe", "content": "x"},
                         {"path": ".git/config", "content": "x"}], "notes": "n"}
        self.assertEqual(len(checks.check_file_set(bad)), 4)

    def test_html_and_flask_are_disabled(self):
        design = {"files": [{"path": "a.py"}]}
        errors = checks.check_file_set({"files": [{"path": "page.html", "content": "<p>x</p>"}], "notes": "n"})
        self.assertTrue(any("file type not allowed" in e for e in errors))
        task = {"acceptance_criteria": []}
        brief = {"hyperparameters": []}
        full = {"criteria_map": [], "tabs": [], "files": [{"path": "flask_app.py"}, {"path": "templates/fragment/a.html"}, {"path": "engine/m.py"}, {"path": "tests/t.py"}]}
        problems = checks.check_design(task, brief, full)
        self.assertEqual(sum("HTML pages and Flask are disabled" in e for e in problems), 2)

    def test_first_build_must_cover_the_design(self):
        design = {"files": [{"path": "a.py"}, {"path": "b.py"}]}
        errors = checks.check_file_set({"files": [{"path": "a.py", "content": "x = 1"}], "notes": "n"}, design)
        self.assertEqual(errors, ["design file not written: b.py"])

    def test_deleting_a_missing_file_is_rejected(self):
        errors = checks.check_file_set({"files": [{"path": "a.py", "content": "x = 1"}], "delete": ["gone.py"], "notes": "n"}, None, {"a.py"})
        self.assertEqual(errors, ["delete: gone.py does not exist"])


if __name__ == "__main__":
    unittest.main()


class FailOnce(Tweaked):
    """The first Builder call fails like a provider error; later calls use the recorded replay."""

    def __init__(self):
        super().__init__()
        self.failed = False

    def generate(self, request):
        if request.agent_id == "builder" and request.metadata.get("key", "").startswith("file_set:") and not self.failed:
            self.failed = True
            from module_platform.providers.base import ProviderError
            raise ProviderError("Claude hit the output limit before finishing")
        return super().generate(request)


class RetryTests(Helpers):
    def test_failed_build_can_be_retried_without_replanning(self):
        client, run_id, plan = self.run_to_end(FailOnce())
        self.assertEqual(client.post(f"/api/v1/runs/{run_id}/approve").status_code, 202)
        run = self.wait_settled(client, run_id)
        self.assertEqual(run["status"], "failed")
        self.assertEqual(client.post(f"/api/v1/runs/{run_id}/retry").status_code, 202)
        run = self.wait_settled(client, run_id)
        types = [e["type"] for e in run["events"]]
        self.assertEqual(run["status"], "ready_for_review", run["events"][-3:])
        self.assertIn("build.retried", types)
        self.assertIn("build.completed", types)

    def test_retry_is_refused_when_nothing_failed(self):
        client, run_id, plan = self.run_to_end(FailOnce())
        self.assertEqual(client.post(f"/api/v1/runs/{run_id}/retry").status_code, 400)


class AppLoadCheckTests(unittest.TestCase):
    """Unit tests can pass while Bokeh rejects the app itself; the build must catch that."""

    def run_check(self, main_source):
        import tempfile
        from module_platform.build import ModuleBuilder

        module = Path(tempfile.mkdtemp())
        (module / "tests").mkdir()
        (module / "tests" / "test_ok.py").write_text("import unittest\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n")
        (module / "main.py").write_text(main_source)
        return ModuleBuilder._run_checks(module)

    def test_bad_callback_signature_fails_the_build_check(self):
        result = self.run_check("from bokeh.io import curdoc\nfrom bokeh.models import Slider\n"
                                "def update(attr=None, old=None, new=None):\n    pass\n"
                                "s = Slider(start=0, end=1, value=0)\ns.on_change('value', update)\ncurdoc().add_root(s)\n")
        self.assertFalse(result["passed"])
        self.assertIn("signature", result["output"])

    def test_valid_app_passes(self):
        result = self.run_check("from bokeh.io import curdoc\nfrom bokeh.models import Slider\n"
                                "def update(attr, old, new):\n    pass\n"
                                "s = Slider(start=0, end=1, value=0)\ns.on_change('value', update)\ncurdoc().add_root(s)\n")
        self.assertTrue(result["passed"], result["output"])


class ManualEditTests(Helpers):
    def built(self):
        client, run_id, plan = self.run_to_end(Tweaked())
        client.post(f"/api/v1/runs/{run_id}/approve")
        run = self.wait_settled(client, run_id)
        self.assertEqual(run["status"], "ready_for_review")
        return client, run_id

    def test_saved_edit_is_checked_snapshotted_and_recorded(self):
        client, run_id = self.built()
        original = client.get(f"/api/v1/runs/{run_id}/files/{ENGINE}").data.decode()
        response = client.put(f"/api/v1/runs/{run_id}/files/{ENGINE}", json={"content": original + "\n# edited by hand\n"})
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["saved"])
        self.assertTrue(body["checks"]["passed"], body["checks"]["output"])
        self.assertTrue(body["commit"])
        self.assertIn("# edited by hand", client.get(f"/api/v1/runs/{run_id}/files/{ENGINE}").data.decode())
        events = [e["type"] for e in client.get(f"/api/v1/runs/{run_id}").get_json()["events"]]
        self.assertIn("file.edited", events)

    def test_breaking_edit_is_kept_with_failing_checks_and_can_be_reverted(self):
        client, run_id = self.built()
        original = client.get(f"/api/v1/runs/{run_id}/files/{ENGINE}").data.decode()
        body = client.put(f"/api/v1/runs/{run_id}/files/{ENGINE}", json={"content": BROKEN}).get_json()
        self.assertFalse(body["checks"]["passed"])
        undone = client.post(f"/api/v1/runs/{run_id}/revert-edit", json={"commit": body["commit"]})
        self.assertEqual(undone.status_code, 200, undone.get_json())
        self.assertTrue(undone.get_json()["checks"]["passed"])
        self.assertEqual(client.get(f"/api/v1/runs/{run_id}/files/{ENGINE}").data.decode(), original)

    def test_unsafe_or_wrong_edits_are_refused(self):
        client, run_id = self.built()
        for path in ("../run.json", ".git/config", "evil.exe"):
            self.assertEqual(client.put(f"/api/v1/runs/{run_id}/files/{path}", json={"content": "x"}).status_code, 400, path)
        self.assertEqual(client.put(f"/api/v1/runs/{run_id}/files/{ENGINE}", json={"content": 5}).status_code, 400)

    def test_only_the_latest_manual_edit_can_be_reverted(self):
        client, run_id = self.built()
        self.assertEqual(client.post(f"/api/v1/runs/{run_id}/revert-edit", json={"commit": "abc123"}).status_code, 400)
