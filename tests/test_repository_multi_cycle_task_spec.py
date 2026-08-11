from __future__ import annotations
import unittest
from automation.orchestration.repository_multi_cycle_task_spec import RepositoryMultiCycleTaskSpecValidationError, serialize_repository_multi_cycle_task_spec, validate_repository_multi_cycle_task_spec


def valid(): return {"schema_version":"1","tasks":[{"task_id":"one","prompt":"one","allowed_changed_paths":["b.py","a.py"],"commit_message":"one"},{"task_id":"two","prompt":"two","allowed_changed_paths":["c.py"],"commit_message":"two"}]}


class QueueSpecTests(unittest.TestCase):
    def test_order_and_determinism(self):
        spec=validate_repository_multi_cycle_task_spec(valid())
        self.assertEqual([task.task_id for task in spec.tasks],["one","two"])
        self.assertEqual(spec.tasks[0].allowed_changed_paths,("a.py","b.py"))
        self.assertEqual(serialize_repository_multi_cycle_task_spec(spec),serialize_repository_multi_cycle_task_spec(spec))
    def test_strict_rejections(self):
        for mutate in (lambda x:x.update(tasks=[]), lambda x:x.update(extra=1), lambda x:x["tasks"].append(x["tasks"][0]), lambda x:x["tasks"][0].update(expected_head_sha="a"*40), lambda x:x["tasks"][0].update(task_id="BAD")):
            value=valid(); mutate(value)
            with self.subTest(value=value), self.assertRaises(RepositoryMultiCycleTaskSpecValidationError): validate_repository_multi_cycle_task_spec(value)
