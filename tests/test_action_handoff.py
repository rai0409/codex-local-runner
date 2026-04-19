from __future__ import annotations

from datetime import datetime
from pathlib import Path
import tempfile
import unittest

from automation.control.action_handoff import build_action_handoff_payload
from automation.control.retry_context_store import FileRetryContextStore


class ActionHandoffTests(unittest.TestCase):
    def _fixed_now(self) -> datetime:
        return datetime(2026, 4, 18, 12, 0, 0)

    def test_handoff_generation_is_deterministic(self) -> None:
        decision = {
            "next_action": "signal_recollect",
            "reason": "dry_run_completed does not imply execution success",
            "whether_human_required": False,
            "retry_budget_remaining": 1,
            "updated_retry_context": {
                "prior_attempt_count": 0,
                "prior_retry_class": None,
                "missing_signal_count": 1,
                "retry_budget_remaining": 1,
            },
        }
        first = build_action_handoff_payload(
            job_id="job-1",
            decision_payload=decision,
            now=self._fixed_now,
        )
        second = build_action_handoff_payload(
            job_id="job-1",
            decision_payload=decision,
            now=self._fixed_now,
        )
        self.assertEqual(first, second)

    def test_unsupported_action_marking_is_explicit(self) -> None:
        payload = build_action_handoff_payload(
            job_id="job-unsupported",
            decision_payload={
                "next_action": "not_real_action",
                "reason": "all units completed with passing verification signals",
                "whether_human_required": False,
                "retry_budget_remaining": 1,
                "updated_retry_context": {
                    "prior_attempt_count": 0,
                    "prior_retry_class": None,
                    "missing_signal_count": 0,
                    "retry_budget_remaining": 1,
                },
            },
            now=self._fixed_now,
        )
        self.assertFalse(payload["action_consumable"])
        self.assertIn("unsupported next_action token", payload["unsupported_reason"])

    def test_proceed_to_pr_is_consumable_in_bounded_executor_phase(self) -> None:
        payload = build_action_handoff_payload(
            job_id="job-pr",
            decision_payload={
                "next_action": "proceed_to_pr",
                "reason": "all units completed with passing verification signals",
                "whether_human_required": False,
                "retry_budget_remaining": 1,
                "updated_retry_context": {
                    "prior_attempt_count": 0,
                    "prior_retry_class": None,
                    "missing_signal_count": 0,
                    "retry_budget_remaining": 1,
                },
            },
            now=self._fixed_now,
        )
        self.assertTrue(payload["action_consumable"])
        self.assertIsNone(payload["unsupported_reason"])

    def test_missing_retry_context_is_conservative(self) -> None:
        payload = build_action_handoff_payload(
            job_id="job-missing-retry",
            decision_payload={
                "next_action": "signal_recollect",
                "reason": "missing signals",
                "whether_human_required": False,
            },
            now=self._fixed_now,
        )
        self.assertEqual(payload["updated_retry_context"]["retry_budget_remaining"], 1)
        self.assertLessEqual(payload["retry_budget_remaining"], 1)

    def test_retry_context_store_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "retry_context_store.json"
            store = FileRetryContextStore(path)
            self.assertIsNone(store.get("job-1"))
            persisted = store.set(
                job_id="job-1",
                retry_context={
                    "prior_attempt_count": 1,
                    "prior_retry_class": "same_prompt_retry",
                    "missing_signal_count": 0,
                    "retry_budget_remaining": 0,
                },
                updated_at="2026-04-18T12:00:00",
            )
            reloaded = store.get("job-1")

        self.assertEqual(persisted["retry_budget_remaining"], 0)
        self.assertEqual(reloaded["prior_retry_class"], "same_prompt_retry")

    def test_external_evidence_statuses_are_handled_conservatively(self) -> None:
        decision = {
            "next_action": "signal_recollect",
            "reason": "missing signals",
            "whether_human_required": False,
            "retry_budget_remaining": 1,
            "updated_retry_context": {
                "prior_attempt_count": 0,
                "prior_retry_class": None,
                "missing_signal_count": 1,
                "retry_budget_remaining": 1,
            },
        }
        expected_constraints = {
            "success": "github_checks_state:pending",
            "empty": "github_evidence_empty:get_pr_status_summary",
            "not_found": "github_evidence_not_found:get_pr_status_summary",
            "auth_failure": "github_evidence_auth_failure:get_pr_status_summary",
            "api_failure": "github_evidence_api_failure:get_pr_status_summary",
            "unsupported_query": "github_evidence_unsupported_query:get_pr_status_summary",
        }

        for status, expected_constraint in expected_constraints.items():
            with self.subTest(status=status):
                payload = build_action_handoff_payload(
                    job_id=f"job-{status}",
                    decision_payload=decision,
                    now=self._fixed_now,
                    external_evidence={
                        "operation": "get_pr_status_summary",
                        "status": status,
                        "data": {"checks_state": "pending"} if status == "success" else {},
                    },
                )
                self.assertIn(expected_constraint, payload["evidence_constraints"])
                self.assertEqual(payload["evidence_summary"]["status_counts"][status], 1)

    def test_external_evidence_cannot_create_false_success(self) -> None:
        payload = build_action_handoff_payload(
            job_id="job-false-success",
            decision_payload={
                "next_action": "not_real_action",
                "reason": "all units completed with passing verification signals",
                "whether_human_required": False,
                "retry_budget_remaining": 1,
                "updated_retry_context": {
                    "prior_attempt_count": 0,
                    "prior_retry_class": None,
                    "missing_signal_count": 0,
                    "retry_budget_remaining": 1,
                },
            },
            now=self._fixed_now,
            external_evidence={
                "operation": "get_pr_status_summary",
                "status": "success",
                "data": {"checks_state": "passing"},
            },
        )
        self.assertFalse(payload["action_consumable"])
        self.assertIn("unsupported next_action token", payload["unsupported_reason"])

    def test_merge_and_rollback_actions_are_consumable_in_this_phase(self) -> None:
        merge_payload = build_action_handoff_payload(
            job_id="job-merge",
            decision_payload={
                "next_action": "proceed_to_merge",
                "reason": "all checks passing and mergeable clean",
                "whether_human_required": False,
                "retry_budget_remaining": 1,
                "updated_retry_context": {
                    "prior_attempt_count": 0,
                    "prior_retry_class": None,
                    "missing_signal_count": 0,
                    "retry_budget_remaining": 1,
                },
            },
            now=self._fixed_now,
        )
        rollback_payload = build_action_handoff_payload(
            job_id="job-rollback",
            decision_payload={
                "next_action": "rollback_required",
                "reason": "explicit rollback requirement signaled",
                "whether_human_required": True,
                "retry_budget_remaining": 1,
                "updated_retry_context": {
                    "prior_attempt_count": 0,
                    "prior_retry_class": None,
                    "missing_signal_count": 0,
                    "retry_budget_remaining": 1,
                },
            },
            now=self._fixed_now,
        )
        self.assertTrue(merge_payload["action_consumable"])
        self.assertIsNone(merge_payload["unsupported_reason"])
        self.assertTrue(rollback_payload["action_consumable"])
        self.assertIsNone(rollback_payload["unsupported_reason"])

    def test_pr_update_action_is_consumable(self) -> None:
        payload = build_action_handoff_payload(
            job_id="job-pr-update",
            decision_payload={
                "next_action": "github.pr.update",
                "reason": "bounded update requested",
                "whether_human_required": False,
                "retry_budget_remaining": 1,
                "updated_retry_context": {
                    "prior_attempt_count": 0,
                    "prior_retry_class": None,
                    "missing_signal_count": 0,
                    "retry_budget_remaining": 1,
                },
            },
            now=self._fixed_now,
        )
        self.assertTrue(payload["action_consumable"])
        self.assertIsNone(payload["unsupported_reason"])

    def test_retry_class_annotation(self) -> None:
        payload = build_action_handoff_payload(
            job_id="job-retry-class",
            decision_payload={
                "next_action": "same_prompt_retry",
                "reason": "execution failure",
                "whether_human_required": False,
                "retry_budget_remaining": 0,
                "updated_retry_context": {
                    "prior_attempt_count": 1,
                    "prior_retry_class": "same_prompt_retry",
                    "missing_signal_count": 0,
                    "retry_budget_remaining": 0,
                },
            },
            now=self._fixed_now,
        )
        self.assertEqual(payload["retry_class"], "same_prompt_retry")


if __name__ == "__main__":
    unittest.main()
