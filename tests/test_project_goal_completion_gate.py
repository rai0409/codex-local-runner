from __future__ import annotations

import copy
import json
import unittest

from automation.orchestration.project_goal_completion_gate import (
    ProjectGoalContractValidationError, decision_to_mapping, evaluate_project_completion,
    serialize_completion_decision, validate_project_goal_contract, validate_project_observation,
)


def contract_data(**overrides):
    value = {"schema_version": "1", "project_id": "project-a", "goal": "安全に出荷する", "repository_path": "/work/project-a", "required_capabilities": [{"capability_id": "cap-b", "description": "B", "required": True}, {"capability_id": "cap-a", "description": "A", "required": True}, {"capability_id": "optional", "description": "optional", "required": False}], "completion_gates": {"require_all_required_capabilities": True, "require_no_critical_gaps": True, "require_no_active_tasks": True, "require_no_blocked_critical_tasks": True, "require_acceptance_verification": True, "require_known_clean_worktree": True}, "constraints": {"automatic_commit": False, "remote_operations": False, "max_files_per_task": 3}}
    value.update(overrides)
    return value


def observation_data(**overrides):
    value = {"schema_version": "1", "capabilities": {"cap-a": {"status": "satisfied", "evidence": ["証拠 A"]}, "cap-b": {"status": "satisfied", "evidence": ["proof B"]}, "optional": {"status": "unsatisfied", "evidence": []}}, "critical_gap_count": 0, "active_task_count": 0, "blocked_critical_task_count": 0, "acceptance_verification": "passed", "acceptance_blocked": False, "worktree_state": "known_clean", "blocking_reasons": []}
    value.update(overrides)
    return value


class ValidationTests(unittest.TestCase):
    def test_valid_contract_and_observation(self):
        contract = validate_project_goal_contract(contract_data())
        self.assertEqual(validate_project_observation(contract, observation_data()).schema_version, "1")

    def test_contract_validation_rejects_missing_unknown_nested_type_bool_duplicate_and_max(self):
        cases = [({key: value for key, value in contract_data().items() if key != "goal"}), contract_data(extra=True), contract_data(required_capabilities=[{"capability_id": "x", "description": "x", "required": "true"}]), contract_data(required_capabilities=[{"capability_id": "x", "description": "x", "required": True}, {"capability_id": "x", "description": "y", "required": False}]), contract_data(constraints={"automatic_commit": False, "remote_operations": False, "max_files_per_task": True}), contract_data(constraints={"automatic_commit": False, "remote_operations": False, "max_files_per_task": 0})]
        nested = contract_data(); nested["completion_gates"]["extra"] = True; cases.append(nested)
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(ProjectGoalContractValidationError) as raised:
                    validate_project_goal_contract(payload)
                self.assertTrue(raised.exception.reason_code)

    def test_observation_validation_rejects_unknown_capability_evidence_inconsistency_and_counts(self):
        cases = [observation_data(capabilities={"other": {"status": "unknown", "evidence": []}}), observation_data(capabilities={"cap-a": {"status": "satisfied", "evidence": []}}), observation_data(acceptance_verification="blocked", acceptance_blocked=False), observation_data(acceptance_verification="passed", acceptance_blocked=True), observation_data(critical_gap_count=-1), observation_data(active_task_count=True)]
        nested = observation_data(); nested["capabilities"]["cap-a"]["extra"] = True; cases.append(nested)
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(ProjectGoalContractValidationError):
                    validate_project_observation(contract_data(), payload)


class EvaluationTests(unittest.TestCase):
    def evaluate(self, **overrides):
        return evaluate_project_completion(contract_data(), observation_data(**overrides))

    def test_completed_and_json_utf8_round_trip(self):
        result = self.evaluate()
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.completion_ratio, 1.0)
        mapped = decision_to_mapping(result)
        self.assertEqual(json.loads(json.dumps(mapped, ensure_ascii=False)), mapped)
        self.assertIn("no_action_required", json.dumps(mapped, ensure_ascii=False))

    def test_incomplete_blocked_and_insufficient_truth(self):
        self.assertEqual(self.evaluate(critical_gap_count=1).status, "incomplete")
        self.assertEqual(self.evaluate(blocked_critical_task_count=1).status, "blocked")
        self.assertEqual(self.evaluate(worktree_state="unknown").status, "insufficient_truth")

    def test_disabled_gates_and_zero_enabled_gates(self):
        contract = contract_data(); contract["completion_gates"] = {key: False for key in contract["completion_gates"]}
        observation = observation_data(capabilities={"cap-a": {"status": "blocked", "evidence": []}}, critical_gap_count=1)
        result = evaluate_project_completion(contract, observation)
        self.assertEqual((result.status, result.completion_ratio, result.blocked_required_capabilities, result.unknown_required_capabilities), ("insufficient_truth", 0.0, ("cap-a",), ("cap-b",)))
        self.assertEqual(result.status_reason_code, "no_completion_gates_enabled")
        self.assertEqual(result.next_required_action.action_id, "configure_completion_gates")
        self.assertEqual(result.next_required_action.target_id, "completion_gates")
        self.assertEqual(result.next_required_action.reason_code, "completion_gates.not_enabled")
        self.assertEqual(result.next_required_action.reason, "Enable at least one completion gate before evaluating project completion")
        self.assertEqual(evaluate_project_completion(contract, observation), result)
        mapped = decision_to_mapping(result)
        self.assertEqual(mapped["next_required_action"], {"action_id": "configure_completion_gates", "target_id": "completion_gates", "reason_code": "completion_gates.not_enabled", "reason": "Enable at least one completion gate before evaluating project completion"})
        self.assertEqual(json.loads(serialize_completion_decision(result))["next_required_action"], mapped["next_required_action"])

    def test_no_action_required_is_reserved_for_completed(self):
        completed = self.evaluate()
        incomplete = self.evaluate(critical_gap_count=1)
        blocked = self.evaluate(blocked_critical_task_count=1)
        insufficient_truth = self.evaluate(worktree_state="unknown")
        self.assertEqual(completed.next_required_action.action_id, "no_action_required")
        for result in (incomplete, blocked, insufficient_truth):
            with self.subTest(status=result.status):
                self.assertNotEqual(result.next_required_action.action_id, "no_action_required")

    def test_precedence_ratio_and_action_precedence(self):
        result = self.evaluate(capabilities={"cap-a": {"status": "unknown", "evidence": []}, "cap-b": {"status": "unsatisfied", "evidence": []}}, critical_gap_count=1, active_task_count=1, blocked_critical_task_count=1, acceptance_verification="blocked", acceptance_blocked=True, worktree_state="unknown", blocking_reasons=["z", "a", "a"])
        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.blocking_reasons, ("a", "z"))
        self.assertEqual(result.next_required_action.action_id, "resolve_explicit_blocking_reason")
        self.assertEqual(result.next_required_action.target_id, "a")
        self.assertEqual(result.completion_ratio, 0.0)
        ratio = self.evaluate(critical_gap_count=1)
        self.assertEqual(ratio.completion_ratio, round(5 / 6, 6))
        self.assertEqual(ratio.failed_gates, ("critical_gaps",))

    def test_action_order_and_determinism_input_immutability(self):
        contract, observation = contract_data(), observation_data(capabilities={"cap-b": {"status": "unsatisfied", "evidence": []}, "cap-a": {"status": "unknown", "evidence": []}}, critical_gap_count=1)
        before = copy.deepcopy((contract, observation))
        first, second = evaluate_project_completion(contract, observation), evaluate_project_completion(contract, observation)
        self.assertEqual(first, second)
        self.assertEqual((contract, observation), before)
        self.assertEqual(first.unknown_required_capabilities, ("cap-a",))
        self.assertEqual(first.next_required_action.action_id, "gather_required_capability_evidence")


if __name__ == "__main__":
    unittest.main()
