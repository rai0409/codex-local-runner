from __future__ import annotations

from datetime import datetime
import unittest

from automation.control.retry_decision import evaluate_retry_decision
from automation.control.retry_policy import DECISION_ESCALATE_TO_HUMAN
from automation.control.retry_policy import DECISION_PAUSE_AND_WAIT
from automation.control.retry_policy import DECISION_RETRY_NOW
from automation.control.retry_policy import DECISION_TERMINAL_REFUSAL


class RetryDecisionTests(unittest.TestCase):
    def _fixed_now(self) -> datetime:
        return datetime(2026, 4, 18, 16, 0, 0)

    def test_provider_usage_exhausted_maps_to_pause_and_wait(self) -> None:
        decision = evaluate_retry_decision(
            provider_name="codex",
            operation_class="execution",
            failure_type="provider_usage_exhausted",
            retry_context={"retry_budget_remaining": 2},
            now=self._fixed_now,
        )
        self.assertEqual(decision["decision_kind"], DECISION_PAUSE_AND_WAIT)
        self.assertEqual(decision["pause_state"], "waiting_for_provider_capacity")

    def test_rate_limit_with_retry_after_maps_to_pause_and_wait(self) -> None:
        decision = evaluate_retry_decision(
            provider_name="codex",
            operation_class="execution",
            retry_after_seconds=90,
            retry_context={"retry_budget_remaining": 2},
            reason="429 too many requests",
            now=self._fixed_now,
        )
        self.assertEqual(decision["decision_kind"], DECISION_PAUSE_AND_WAIT)
        self.assertEqual(decision["pause_state"], "waiting_for_rate_limit_reset")
        self.assertEqual(decision["pause_retry_after_seconds"], 90)
        self.assertEqual(decision["next_eligible_at"], "2026-04-18T16:01:30")

    def test_transport_timeout_maps_to_retry_now_with_bounded_attempts(self) -> None:
        decision = evaluate_retry_decision(
            provider_name="codex",
            operation_class="execution",
            failure_type="transport_timeout",
            retry_class="same_prompt_retry",
            retry_context={"retry_budget_remaining": 2, "prior_attempt_count": 0, "prior_retry_class": None},
            now=self._fixed_now,
        )
        self.assertEqual(decision["decision_kind"], DECISION_RETRY_NOW)
        self.assertGreaterEqual(int(decision["remaining_attempts"]), 1)
        self.assertEqual(decision["retry_class"], "same_prompt_retry")

    def test_auth_failure_is_not_retry_now(self) -> None:
        decision = evaluate_retry_decision(
            provider_name="github",
            operation_class="merge",
            failure_type="auth_failure",
            retry_context={"retry_budget_remaining": 3},
            now=self._fixed_now,
        )
        self.assertIn(decision["decision_kind"], {DECISION_TERMINAL_REFUSAL, DECISION_ESCALATE_TO_HUMAN})
        self.assertNotEqual(decision["decision_kind"], DECISION_RETRY_NOW)

    def test_missing_policy_uses_conservative_fallback(self) -> None:
        decision = evaluate_retry_decision(
            provider_name="unknown-provider",
            operation_class="execution",
            failure_type="unknown_failure",
            retry_context={"retry_budget_remaining": 2},
            policy={},
            now=self._fixed_now,
        )
        self.assertEqual(decision["decision_kind"], DECISION_ESCALATE_TO_HUMAN)

    def test_malformed_policy_uses_conservative_fallback(self) -> None:
        malformed_policy = {
            "schema_version": "v1",
            "defaults": {"decision_kind": "retry_now"},
            "policies": [
                {
                    "id": "unsafe",
                    "provider_class": "*",
                    "operation_class": "*",
                    "failure_type": "*",
                    "decision_kind": "retry_now",
                }
            ],
        }
        decision = evaluate_retry_decision(
            provider_name="codex",
            operation_class="execution",
            failure_type="provider_usage_exhausted",
            retry_context={"retry_budget_remaining": 2},
            policy=malformed_policy,
            now=self._fixed_now,
        )
        self.assertEqual(decision["decision_kind"], DECISION_PAUSE_AND_WAIT)

    def test_same_retry_class_exhaustion_prevents_retry_now(self) -> None:
        decision = evaluate_retry_decision(
            provider_name="codex",
            operation_class="execution",
            failure_type="transport_timeout",
            retry_class="same_prompt_retry",
            retry_context={
                "retry_budget_remaining": 1,
                "prior_retry_class": "same_prompt_retry",
                "prior_attempt_count": 3,
            },
            now=self._fixed_now,
        )
        self.assertNotEqual(decision["decision_kind"], DECISION_RETRY_NOW)

    def test_active_non_eligible_pause_is_not_reinterpreted_as_retry_now(self) -> None:
        decision = evaluate_retry_decision(
            provider_name="codex",
            operation_class="execution",
            failure_type="transport_timeout",
            retry_class="same_prompt_retry",
            retry_context={"retry_budget_remaining": 2},
            pause_state_payload={
                "lifecycle_state": "paused",
                "pause_state": "waiting_for_rate_limit_reset",
                "next_eligible_at": "2026-04-18T16:30:00",
                "whether_human_required": False,
            },
            now=self._fixed_now,
        )
        self.assertEqual(decision["decision_kind"], DECISION_PAUSE_AND_WAIT)

    def test_equivalent_structured_signals_map_consistently(self) -> None:
        direct = evaluate_retry_decision(
            provider_name="codex",
            operation_class="execution",
            failure_type="provider_rate_limited",
            retry_context={"retry_budget_remaining": 2},
            now=self._fixed_now,
        )
        structured = evaluate_retry_decision(
            provider_name="codex",
            operation_class="execution",
            structured_result={"failure_type": "provider_rate_limited"},
            retry_context={"retry_budget_remaining": 2},
            now=self._fixed_now,
        )
        self.assertEqual(direct["decision_kind"], structured["decision_kind"])
        self.assertEqual(direct["pause_state"], structured["pause_state"])


if __name__ == "__main__":
    unittest.main()
