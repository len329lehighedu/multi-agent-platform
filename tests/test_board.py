"""The home page's pipeline board: each project lands in the column of its latest run."""

import unittest

from module_platform.board import short_goal
from test_workflow import Helpers, Tweaked


class BoardTests(Helpers):
    def project(self, client, name="Board"):
        return client.post("/api/v1/projects", json={"name": name}).get_json()

    def summary(self, client, project_id):
        return client.get(f"/api/v1/projects/{project_id}").get_json()

    def test_columns_follow_the_run(self):
        client = self.make_client({"replay": Tweaked()})
        project = self.project(client)
        empty = self.summary(client, project["id"])
        self.assertEqual((empty["column"], empty["strip"]), ("planning", ["todo"] * 6))

        run = client.post("/api/v1/runs", json={"goal": "Build a module where learners discover equations from pendulum data.", "project_id": project["id"]}).get_json()
        client.post(f"/api/v1/runs/{run['id']}/chat", json={"content": "Discover equations from pendulum data"})
        self.wait_settled(client, run["id"])
        asked = self.summary(client, project["id"])
        self.assertEqual(asked["column"], "needs_you")
        self.assertIn("waiting", asked["strip"])

        client.post(f"/api/v1/runs/{run['id']}/chat", json={"content": "Use built-in systems"})
        self.wait_settled(client, run["id"])
        plan = self.summary(client, project["id"])
        self.assertEqual((plan["column"], plan["reason"]), ("needs_you", "Plan ready for your approval"))

        client.post(f"/api/v1/runs/{run['id']}/approve")
        self.wait_settled(client, run["id"])
        built = self.summary(client, project["id"])
        self.assertEqual(built["column"], "ready")
        self.assertEqual(built["strip"], ["done"] * 6)
        self.assertEqual(built["versions"], 1)
        self.assertTrue(built["has_module"])
        self.assertEqual(built["summary"], "Discover equations from pendulum data.")


class ShortGoalTests(unittest.TestCase):
    def test_drops_boilerplate_and_keeps_the_first_sentence(self):
        self.assertEqual(short_goal("Build a module where learners explore kNN. Train tab: sliders."), "Explore kNN.")
        self.assertTrue(short_goal("x" * 300).endswith("…"))


if __name__ == "__main__":
    unittest.main()
