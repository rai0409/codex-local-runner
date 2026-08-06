from __future__ import annotations
import unittest
from automation.orchestration.repository_single_task_spec import RepositorySingleTaskSpecValidationError, serialize_repository_single_task_spec, validate_repository_single_task_spec

def valid(): return {"schema_version":"1","task_id":"task-1","expected_head_sha":"a"*40,"prompt":"implement\nwithout mutation","allowed_changed_paths":["b.py","a.py"],"commit_message":"Add task"}

class RepositorySingleTaskSpecTests(unittest.TestCase):
 def test_normalizes_immutably_and_serializes(self):
  raw=valid(); spec=validate_repository_single_task_spec(raw)
  self.assertEqual(spec.allowed_changed_paths,("a.py","b.py")); self.assertEqual(raw["allowed_changed_paths"],["b.py","a.py"]); self.assertEqual(serialize_repository_single_task_spec(spec),serialize_repository_single_task_spec(spec))
 def test_strict_rejections(self):
  for change, code in [({"extra":1},"unknown_field"),({"expected_head_sha":"A"*40},"expected_head_sha.invalid"),({"allowed_changed_paths":["../a.py"]},"allowed_changed_paths.invalid"),({"allowed_changed_paths":["a.py","a.py"]},"allowed_changed_paths.duplicate")]:
   raw=valid(); raw.update(change)
   with self.assertRaises(RepositorySingleTaskSpecValidationError) as caught: validate_repository_single_task_spec(raw)
   self.assertIn(code,caught.exception.reason_code)
