"""A failing threshold becomes a question for the user instead of a blocked build."""

import json
import unittest

from module_platform.build import ModuleBuilder
from module_platform.providers.base import ModelResponse
from test_build import Scripted, reply
from test_workflow import FIXTURE, Helpers

CRITERION_TEST = "tests/test_criteria.py"


def criterion_test(high: int) -> str:
    return ("import unittest\n\n\nclass CriterionTests(unittest.TestCase):\n"
            "    def test_ac1_best_degree_in_range(self):\n"
            "        measured = 8\n"
            f"        self.assertTrue(3 <= measured <= {high}, f\"best degree {{measured}} outside [3,{high}]\")\n")


def build_with_strict_test(_text):
    data = json.loads(FIXTURE.read_text())["builder"][1]
    data["artifact"]["files"].append({"path": CRITERION_TEST, "content": criterion_test(6)})
    return ModelResponse(text=json.dumps(data), structured_output=data, usage={})


def proposal(verdict="threshold", measured="best degree 8", criterion="AC1"):
    data = {"message": "Checked.", "question": None, "handoff_summary": "Checked.",
            "artifact": {"verdict": verdict, "criterion_id": criterion, "measured": measured, "current": "3 to 6",
                         "proposed": "3 to 9", "reason": "With 30 noisy points the best degree is 7 or 8 on most seeds."}}
    return ModelResponse(text=json.dumps(data), structured_output=data, usage={})


class CriterionScripted(Scripted):
    def __init__(self, on_proposal, on_amend=None, **handlers):
        super().__init__(**handlers)
        self.on_proposal, self.on_amend = on_proposal, on_amend
        self.proposals = 0

    def generate(self, request):
        key = request.metadata.get("key", "")
        if request.agent_id == "builder" and key == "criterion_proposal":
            self.proposals += 1
            return self.on_proposal()
        if request.agent_id == "builder" and key == "file_set:amend":
            self.builder_calls.append("amend")
            return self.on_amend(request.messages[0]["content"])
        return super().generate(request)


class CriterionQuestionTests(Helpers):
    def build(self, provider):
        client, run_id, plan = self.run_to_end(provider)
        self.assertEqual(plan["status"], "ready_for_review")
        client.post(f"/api/v1/runs/{run_id}/approve")
        return client, run_id, self.wait_settled(client, run_id)

    def types(self, run):
        return [e["type"] for e in run["events"]]

    def provider(self, **extra):
        defaults = dict(on_proposal=proposal, on_build=build_with_strict_test,
                        on_repair=lambda _t: reply({CRITERION_TEST: criterion_test(6)}, "kept the criterion"))
        defaults.update(extra)
        return CriterionScripted(**defaults)

    def test_unreachable_threshold_asks_then_accept_finishes_the_build(self):
        def amend(text):
            self.assertIn("3 to 9", text)
            return reply({CRITERION_TEST: criterion_test(9)}, "threshold changed to 3..9")

        provider = self.provider(on_amend=amend)
        client, run_id, run = self.build(provider)
        self.assertEqual(run["status"], "awaiting_user")
        question = next(e["data"] for e in run["events"] if e["type"] == "criterion.question")
        self.assertEqual((question["criterion_id"], question["proposed"]), ("AC1", "3 to 9"))
        self.assertEqual(provider.builder_calls.count("repair"), 1, "one honest repair before asking")
        self.assertEqual(client.post(f"/api/v1/runs/{run_id}/chat", json={"content": "hi"}).status_code, 400)

        self.assertEqual(client.post(f"/api/v1/runs/{run_id}/criterion", json={"decision": "accept"}).status_code, 202)
        run = self.wait_settled(client, run_id)
        types = self.types(run)
        self.assertEqual(run["status"], "ready_for_review", run["events"][-3:])
        for expected in ("criterion.answered", "criterion.amended", "build.completed"):
            self.assertIn(expected, types)
        self.assertIn("AC1: 3 to 6 -> 3 to 9", run["messages"][-1]["content"])

    def test_stop_ends_the_build_and_keeps_the_module(self):
        client, run_id, run = self.build(self.provider())
        client.post(f"/api/v1/runs/{run_id}/criterion", json={"decision": "stop"})
        run = self.wait_settled(client, run_id)
        self.assertEqual(run["status"], "needs_review")
        self.assertIn("build.failed", self.types(run))
        self.assertNotIn("build.completed", self.types(run))

    def test_keep_gives_the_builder_more_repairs(self):
        provider = self.provider()
        client, run_id, run = self.build(provider)
        client.post(f"/api/v1/runs/{run_id}/criterion", json={"decision": "keep"})
        run = self.wait_settled(client, run_id)
        self.assertIn("criterion.kept", self.types(run))
        self.assertEqual(run["status"], "needs_review")
        self.assertEqual(provider.proposals, 1, "only one question per build")
        self.assertGreater(provider.builder_calls.count("repair"), 1)

    def test_code_bug_verdict_does_not_ask(self):
        client, run_id, run = self.build(self.provider(on_proposal=lambda: proposal(verdict="code_bug")))
        self.assertNotIn("criterion.question", self.types(run))
        self.assertEqual(run["status"], "needs_review")

    def test_invented_measurement_is_rejected(self):
        client, run_id, run = self.build(self.provider(on_proposal=lambda: proposal(measured="best degree 5.5")))
        self.assertNotIn("criterion.question", self.types(run))
        checked = next(e["data"] for e in run["events"] if e["type"] == "criterion.checked")
        self.assertTrue(any("measured" in error for error in checked["errors"]))

    def test_answer_without_a_question_is_refused(self):
        client, run_id, plan = self.run_to_end(self.provider())
        self.assertEqual(client.post(f"/api/v1/runs/{run_id}/criterion", json={"decision": "accept"}).status_code, 400)


class CriterionFailureTests(unittest.TestCase):
    SPEC = {"acceptance_criteria": [{"id": "AC1"}, {"id": "AC12"}]}

    def test_only_named_assertion_failures_count(self):
        output = "FAIL: test_ac1_best_degree (tests.T)\nAssertionError: best degree 8"
        self.assertEqual(ModuleBuilder.criterion_failures(output, self.SPEC), ["AC1"])

    def test_a_crash_or_an_unnamed_test_is_never_a_criterion_question(self):
        self.assertEqual(ModuleBuilder.criterion_failures("ERROR: test_ac1_x (t)\nTraceback", self.SPEC), [])
        self.assertEqual(ModuleBuilder.criterion_failures("FAIL: test_fit_works (t)", self.SPEC), [])
        self.assertEqual(ModuleBuilder.criterion_failures("FAIL: test_ac1_x (t)\nmain.py failed to load as a Bokeh app", self.SPEC), [])

    def test_ids_match_whole_tokens(self):
        self.assertEqual(ModuleBuilder.criterion_failures("FAIL: test_ac12_rate (t)", self.SPEC), ["AC12"])


if __name__ == "__main__":
    unittest.main()
