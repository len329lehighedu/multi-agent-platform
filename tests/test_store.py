import tempfile
import unittest
from pathlib import Path

from module_platform.domain import RunRecord
from module_platform.store import JsonRunStore, RunNotFound


class JsonRunStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.store = JsonRunStore(Path(self.temporary.name))

    def tearDown(self):
        self.temporary.cleanup()

    def test_create_save_get_and_list(self):
        run = self.store.create(RunRecord.create("A module"))
        run.append_event("changed")
        self.store.save(run)

        self.assertEqual(self.store.get(run.id).revision, run.revision)
        self.assertEqual([item.id for item in self.store.list()], [run.id])

    def test_unknown_and_unsafe_ids_are_not_found(self):
        for run_id in ("missing", "../secrets", "f" * 31):
            with self.subTest(run_id=run_id), self.assertRaises(RunNotFound):
                self.store.get(run_id)


if __name__ == "__main__":
    unittest.main()
