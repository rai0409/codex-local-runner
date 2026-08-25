from __future__ import annotations
import hashlib, unittest
from automation.orchestration.repository_multi_cycle_replan import *
from automation.orchestration.repository_multi_cycle_task_spec import validate_repository_multi_cycle_task_spec

def queue(): return validate_repository_multi_cycle_task_spec({"schema_version":"1","tasks":[{"task_id":"one","prompt":"one","allowed_changed_paths":["one.py"],"commit_message":"One"},{"task_id":"two","prompt":"two","allowed_changed_paths":["two.py"],"commit_message":"Two","execution_timeout_seconds":3600,"completion_rework_timeout_seconds":7200},{"task_id":"three","prompt":"three","allowed_changed_paths":["three.py"],"commit_message":"Three"},{"task_id":"four","prompt":"four","allowed_changed_paths":["four.py"],"commit_message":"Four"}]})
def evidence(): return ReplanFailureEvidence(queue(),1,"single_task.task_completion.rework_exhausted","contract.missing",{"reason_code":"contract.missing","unsatisfied_criteria":["missing"],"raw_log":"SECRET"})
def replace(): return {"schema_version":"1","decision":"replace_failed_task","prompt":"repair three","allowed_changed_paths":["repair.py"],"commit_message":"Repair three"}

class ReplanTests(unittest.TestCase):
 def test_eligibility_and_strict_envelope(self):
  self.assertTrue(is_auto_replan_eligible("single_task.task_completion.rework_exhausted")); self.assertTrue(is_auto_replan_eligible("single_task.task_scope.recovery_exhausted")); self.assertFalse(is_auto_replan_eligible("single_task.changed_files.out_of_scope")); self.assertFalse(is_auto_replan_eligible("single_task.source.dirty")); self.assertEqual(validate_replan_envelope(replace()).decision,"replace_failed_task")
  for value in ({**replace(),"task_id":"model"},{**replace(),"execution_timeout_seconds":1},{**replace(),"extra":1},{**replace(),"schema_version":"2"},{**replace(),"decision":"bad"},{"schema_version":"1","decision":"stop","prompt":"no"}):
   with self.subTest(value=value), self.assertRaises(RepositoryMultiCycleReplanError): validate_replan_envelope(value)
  self.assertEqual(validate_replan_envelope({"schema_version":"1","decision":"stop"}).decision,"stop")
 def test_replacement_successor_and_serialization(self):
  plan=build_successor_queue(evidence(),validate_replan_envelope(replace()),1); self.assertEqual(plan.status,"replace_failed_task"); self.assertEqual(plan.replacement_task.task_id,"two-replan-1"); self.assertEqual(plan.replacement_task.execution_timeout_seconds,3600); self.assertEqual(plan.replacement_task.completion_rework_timeout_seconds,7200); self.assertEqual([x.task_id for x in plan.successor_queue.tasks],["two-replan-1","three","four"]); self.assertEqual(plan.successor_queue.tasks[1:],queue().tasks[2:]); self.assertEqual(plan.successor_queue_sha256,hashlib.sha256(plan.serialized_successor_queue.encode()).hexdigest()); self.assertEqual(plan,build_successor_queue(evidence(),validate_replan_envelope(replace()),1)); self.assertNotEqual(replacement_task_id("two",1),replacement_task_id("two",2))
 def test_stop_noneligible_paths_and_prompt_safety(self):
  self.assertEqual(build_successor_queue(evidence(),validate_replan_envelope({"schema_version":"1","decision":"stop"}),1).status,"stop"); bad=ReplanFailureEvidence(queue(),2,"single_task.source.dirty"); self.assertEqual(build_successor_queue(bad,validate_replan_envelope(replace()),1).status,"noneligible")
  for paths in (["/tmp/x.py"],["../x.py"],[".git/config"]):
   value=replace(); value["allowed_changed_paths"]=paths
   with self.assertRaises(Exception): build_successor_queue(evidence(),validate_replan_envelope(value),1)
  prompt=build_replan_planner_prompt(evidence()); self.assertIn("planning",prompt.lower()); self.assertIn("contract.missing",prompt); self.assertNotIn("SECRET",prompt)

 def test_scope_deficiency_prompt_exposes_only_bounded_scope_evidence(self):
  item=ReplanFailureEvidence(queue(),1,"single_task.task_scope.recovery_exhausted",completion_evidence={"declared_allowed_changed_paths":["a.py"],"effective_allowed_changed_paths":["a.py"],"scope_trimmed_paths":["b.py"],"raw_log":"SECRET"})
  prompt=build_replan_planner_prompt(item); self.assertIn("b.py",prompt); self.assertIn("exact paths",prompt); self.assertNotIn("SECRET",prompt)
  plan=build_successor_queue(item,validate_replan_envelope({"schema_version":"1","decision":"replace_failed_task","prompt":"repair","allowed_changed_paths":["a.py","b.py"],"commit_message":"Repair"}),1)
  self.assertEqual(plan.replacement_task.allowed_changed_paths,("a.py","b.py"))
  with self.assertRaisesRegex(RepositoryMultiCycleReplanError,"evidence_bounded"):
   build_successor_queue(item,validate_replan_envelope({"schema_version":"1","decision":"replace_failed_task","prompt":"repair","allowed_changed_paths":["a.py","unrelated.py"],"commit_message":"Repair"}),1)
