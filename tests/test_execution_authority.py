from __future__ import annotations

import unittest

from automation.control.execution_authority import ALL_FIRST_CLASS_ACTION_TOKENS
from automation.control.execution_authority import evaluate_action_authority
from automation.control.execution_authority import get_action_authority
from automation.control.execution_authority import get_operation_authority
from automation.control.execution_authority import LANE_DETERMINISTIC_PYTHON
from automation.control.execution_authority import LANE_GITHUB_DETERMINISTIC
from automation.control.execution_authority import LANE_LLM_BACKED


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

    def test_control_plane_deterministic_actions_are_not_llm_required(self) -> None:
        for token in ("wait_for_checks", "escalate_to_human"):
            with self.subTest(token=token):
                authority = get_action_authority(token)
                assert authority is not None
                self.assertEqual(authority.default_lane, LANE_DETERMINISTIC_PYTHON)
                self.assertNotEqual(authority.llm_policy, "required")

    def test_llm_required_actions_are_marked_clearly(self) -> None:
        for token in ("same_prompt_retry", "repair_prompt_retry", "signal_recollect", "prompt_recompile", "roadmap_replan"):
            with self.subTest(token=token):
                authority = get_action_authority(token)
                assert authority is not None
                self.assertEqual(authority.default_lane, LANE_LLM_BACKED)
                self.assertEqual(authority.llm_policy, "required")

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

