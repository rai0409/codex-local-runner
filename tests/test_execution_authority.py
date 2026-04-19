from __future__ import annotations

import unittest

from automation.control.execution_authority import ALL_FIRST_CLASS_ACTION_TOKENS
from automation.control.execution_authority import evaluate_action_authority
from automation.control.execution_authority import get_action_authority
from automation.control.execution_authority import get_operation_authority
from automation.control.execution_authority import LANE_DETERMINISTIC_PYTHON
from automation.control.execution_authority import LANE_GITHUB_DETERMINISTIC
from automation.control.execution_authority import LANE_LLM_BACKED
from automation.control.execution_authority import normalize_requested_lane_input
from automation.control.execution_authority import resolve_action_routing
from automation.control.execution_authority import ROUTING_CLASS_CONTROL
from automation.control.execution_authority import ROUTING_CLASS_EXECUTOR
from automation.control.execution_authority import ROUTING_CLASS_RETRY


class ExecutionAuthorityTests(unittest.TestCase):
    def test_all_first_class_tokens_are_explicitly_classified(self) -> None:
        expected = {
            "same_prompt_retry",
            "repair_prompt_retry",
            "signal_recollect",
            "wait_for_checks",
            "prompt_recompile",
            "roadmap_replan",
            "escalate_to_human",
            "proceed_to_pr",
            "github.pr.update",
            "proceed_to_merge",
            "rollback_required",
        }
        self.assertEqual(set(ALL_FIRST_CLASS_ACTION_TOKENS), expected)
        for token in expected:
            self.assertIsNotNone(get_action_authority(token))

    def test_bounded_github_write_tokens_are_deterministic_not_llm_required(self) -> None:
        for token in ("proceed_to_pr", "github.pr.update", "proceed_to_merge", "rollback_required"):
            with self.subTest(token=token):
                authority = get_action_authority(token)
                assert authority is not None
                self.assertEqual(authority.default_lane, LANE_GITHUB_DETERMINISTIC)
                self.assertTrue(authority.deterministic_only)
                self.assertEqual(authority.llm_policy, "disallowed")
                self.assertEqual(authority.routing_class, ROUTING_CLASS_EXECUTOR)

    def test_control_plane_deterministic_actions_are_not_llm_required(self) -> None:
        for token in ("wait_for_checks", "escalate_to_human"):
            with self.subTest(token=token):
                authority = get_action_authority(token)
                assert authority is not None
                self.assertEqual(authority.default_lane, LANE_DETERMINISTIC_PYTHON)
                self.assertNotEqual(authority.llm_policy, "required")
                self.assertIn(authority.routing_class, {ROUTING_CLASS_RETRY, ROUTING_CLASS_CONTROL})

    def test_llm_required_actions_are_marked_clearly(self) -> None:
        for token in ("same_prompt_retry", "repair_prompt_retry", "signal_recollect", "prompt_recompile", "roadmap_replan"):
            with self.subTest(token=token):
                authority = get_action_authority(token)
                assert authority is not None
                self.assertEqual(authority.default_lane, LANE_LLM_BACKED)
                self.assertEqual(authority.llm_policy, "required")
                self.assertEqual(authority.routing_class, ROUTING_CLASS_RETRY)

    def test_default_routing_resolution_for_bounded_github_actions(self) -> None:
        for token in ("proceed_to_pr", "github.pr.update", "proceed_to_merge", "rollback_required"):
            with self.subTest(token=token):
                routed = resolve_action_routing(token)
                self.assertTrue(routed["known_action"])
                self.assertTrue(routed["allowed"])
                self.assertEqual(routed["resolved_lane"], LANE_GITHUB_DETERMINISTIC)
                self.assertEqual(routed["routing_class"], ROUTING_CLASS_EXECUTOR)

    def test_default_routing_resolution_for_deterministic_control_plane_actions(self) -> None:
        wait_route = resolve_action_routing("wait_for_checks")
        self.assertEqual(wait_route["resolved_lane"], LANE_DETERMINISTIC_PYTHON)
        self.assertEqual(wait_route["routing_class"], ROUTING_CLASS_RETRY)

        escalate_route = resolve_action_routing("escalate_to_human")
        self.assertEqual(escalate_route["resolved_lane"], LANE_DETERMINISTIC_PYTHON)
        self.assertEqual(escalate_route["routing_class"], ROUTING_CLASS_CONTROL)

    def test_default_routing_resolution_for_llm_required_actions(self) -> None:
        for token in ("same_prompt_retry", "repair_prompt_retry", "signal_recollect", "prompt_recompile", "roadmap_replan"):
            with self.subTest(token=token):
                routed = resolve_action_routing(token)
                self.assertTrue(routed["known_action"])
                self.assertTrue(routed["allowed"])
                self.assertEqual(routed["resolved_lane"], LANE_LLM_BACKED)
                self.assertEqual(routed["routing_class"], ROUTING_CLASS_RETRY)

    def test_explicit_requested_lane_is_accepted_when_allowed(self) -> None:
        routed = resolve_action_routing(
            "proceed_to_pr",
            policy_snapshot={"requested_execution_lane": "github_deterministic"},
        )
        self.assertTrue(routed["known_action"])
        self.assertTrue(routed["allowed"])
        self.assertEqual(routed["resolved_lane"], LANE_GITHUB_DETERMINISTIC)

    def test_disallowed_lane_request_fails_conservatively(self) -> None:
        evaluation = evaluate_action_authority(
            "proceed_to_pr",
            policy_snapshot={"requested_execution_lane": "llm_backed"},
        )
        self.assertTrue(evaluation["known_action"])
        self.assertFalse(evaluation["allowed"])
        self.assertEqual(evaluation["reason"], "requested_lane_not_allowed")

    def test_contradictory_lane_requests_fail_conservatively(self) -> None:
        evaluation = evaluate_action_authority(
            "same_prompt_retry",
            policy_snapshot={"requested_execution_lane": "llm_backed"},
            handoff_payload={"requested_execution_lane": "deterministic_python"},
        )
        self.assertTrue(evaluation["known_action"])
        self.assertFalse(evaluation["allowed"])
        self.assertEqual(evaluation["reason"], "requested_lane_conflict")

    def test_semantically_equivalent_requested_lane_inputs_normalize_identically(self) -> None:
        normalized_legacy = normalize_requested_lane_input(
            "proceed_to_pr",
            policy_snapshot={"requested_execution_lane": "github_deterministic"},
        )
        normalized_canonical = normalize_requested_lane_input(
            "proceed_to_pr",
            policy_snapshot={
                "requested_execution": {
                    "requested_lane": "github_deterministic",
                }
            },
        )
        self.assertEqual(
            normalized_legacy["routing_input_fingerprint"],
            normalized_canonical["routing_input_fingerprint"],
        )
        self.assertEqual(normalized_legacy["requested_lane"], "github_deterministic")
        self.assertEqual(normalized_canonical["requested_lane"], "github_deterministic")

    def test_requested_lane_conflict_within_single_surface_is_conservative(self) -> None:
        evaluation = evaluate_action_authority(
            "proceed_to_pr",
            policy_snapshot={
                "requested_execution": {
                    "requested_lane": "github_deterministic",
                    "requested_lanes": {"proceed_to_pr": "llm_backed"},
                }
            },
        )
        self.assertTrue(evaluation["known_action"])
        self.assertFalse(evaluation["allowed"])
        self.assertEqual(evaluation["reason"], "requested_lane_conflict")

    def test_github_executor_actions_cannot_drift_to_llm_via_alternate_surface(self) -> None:
        evaluation = evaluate_action_authority(
            "proceed_to_pr",
            handoff_payload={
                "requested_execution": {
                    "requested_lanes": {"proceed_to_pr": "llm_backed"},
                }
            },
        )
        self.assertTrue(evaluation["known_action"])
        self.assertFalse(evaluation["allowed"])
        self.assertEqual(evaluation["reason"], "requested_lane_not_allowed")

    def test_github_operation_authority_is_explicit(self) -> None:
        read_op = get_operation_authority("github.read.compare_refs")
        write_op = get_operation_authority("github.write.update_existing_pr")
        assert read_op is not None
        assert write_op is not None
        self.assertEqual(read_op.default_lane, LANE_GITHUB_DETERMINISTIC)
        self.assertEqual(write_op.default_lane, LANE_GITHUB_DETERMINISTIC)
        self.assertTrue(read_op.deterministic_only)
        self.assertTrue(write_op.deterministic_only)


if __name__ == "__main__":
    unittest.main()
