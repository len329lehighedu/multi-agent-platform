import unittest

from module_platform.domain import RunRecord, RunStage


class RunRecordTests(unittest.TestCase):
    def test_valid_transition_is_recorded(self):
        run = RunRecord.create("Teach heat transfer")

        run.transition(RunStage.PLANNING, "requirements are sufficient")

        self.assertEqual(run.stage, RunStage.PLANNING)
        self.assertEqual(run.events[-1].type, "run.stage_changed")
        self.assertEqual(run.events[-1].data["from"], "intake")

    def test_invalid_transition_is_rejected(self):
        run = RunRecord.create("Teach heat transfer")

        with self.assertRaisesRegex(ValueError, "cannot transition"):
            run.transition(RunStage.BUILDING, "skip design")

    def test_serialization_round_trip_preserves_types(self):
        run = RunRecord.create("Teach heat transfer")
        run.append_event("example", {"verified": True})

        restored = RunRecord.from_dict(run.to_dict())

        self.assertEqual(restored.to_dict(), run.to_dict())
        self.assertIsInstance(restored.stage, RunStage)


if __name__ == "__main__":
    unittest.main()
