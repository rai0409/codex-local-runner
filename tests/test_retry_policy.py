from __future__ import annotations

import unittest

from automation.control.retry_policy import load_retry_policy
from automation.control.retry_policy import normalize_retry_policy
from automation.control.retry_policy import resolve_retry_policy_entry


class RetryPolicyTests(unittest.TestCase):
    def test_load_retry_policy_contains_expected_entries(self) -> None:
        policy = load_retry_policy()
        entries = policy.get("entries")
        assert isinstance(entries, list)
        ids = {entry["id"] for entry in entries if isinstance(entry, dict)}
        self.assertIn("codex_execution_usage_exhausted", ids)
        self.assertIn("codex_execution_rate_limited", ids)
        self.assertIn("generic_execution_transport_timeout", ids)
        self.assertIn("generic_auth_failure_terminal", ids)

    def test_normalization_is_deterministic_for_equivalent_input(self) -> None:
        raw_a = {
            "schema_version": "v1",
            "defaults": {"decision_kind": "retry_now", "max_attempts": "2", "backoff_seconds": [10, "20"]},
            "policies": [
                {
                    "id": "a",
                    "match": {
                        "provider_class": "codex",
                        "operation_class": "execution",
                        "failure_type": "transport_timeout",
                    },
                    "decision": {
                        "decision_kind": "retry_now",
                        "max_attempts": "2",
                        "backoff_seconds": [10, 20],
                    },
                }
            ],
        }
        raw_b = {
            "schema_version": "v1",
            "defaults": {"decision_kind": "retry_now", "max_attempts": 2, "backoff_seconds": [10, 20]},
            "policies": [
                {
                    "id": "a",
                    "provider_class": "codex",
                    "operation_class": "execution",
                    "failure_type": "transport_timeout",
                    "decision_kind": "retry_now",
                    "max_attempts": 2,
                    "backoff_seconds": [10, 20],
                }
            ],
        }
        self.assertEqual(normalize_retry_policy(raw_a), normalize_retry_policy(raw_b))

    def test_malformed_policy_entry_is_ignored_conservatively(self) -> None:
        normalized = normalize_retry_policy(
            {
                "schema_version": "v1",
                "defaults": {"decision_kind": "escalate_to_human", "max_attempts": 1},
                "policies": [
                    {
                        "id": "unsafe_wildcard_retry",
                        "provider_class": "*",
                        "operation_class": "*",
                        "failure_type": "*",
                        "decision_kind": "retry_now",
                    }
                ],
            }
        )
        entries = normalized.get("entries")
        assert isinstance(entries, list)
        self.assertEqual(entries, [])

    def test_policy_precedence_provider_operation_failure_retry_class(self) -> None:
        policy = normalize_retry_policy(
            {
                "schema_version": "v1",
                "defaults": {"decision_kind": "escalate_to_human", "max_attempts": 1},
                "policies": [
                    {
                        "id": "generic_timeout",
                        "provider_class": "*",
                        "operation_class": "*",
                        "failure_type": "transport_timeout",
                        "decision_kind": "retry_now",
                        "max_attempts": 1,
                    },
                    {
                        "id": "codex_execution_timeout",
                        "provider_class": "codex",
                        "operation_class": "execution",
                        "failure_type": "transport_timeout",
                        "decision_kind": "retry_now",
                        "max_attempts": 2,
                    },
                    {
                        "id": "codex_execution_timeout_repair",
                        "match": {
                            "provider_class": "codex",
                            "operation_class": "execution",
                            "failure_type": "transport_timeout",
                            "retry_class": "repair_prompt_retry",
                        },
                        "decision": {
                            "decision_kind": "retry_now",
                            "max_attempts": 3,
                        },
                    },
                ],
            }
        )
        resolved = resolve_retry_policy_entry(
            policy,
            provider_class="codex",
            operation_class="execution",
            failure_type="transport_timeout",
            retry_class="repair_prompt_retry",
        )
        assert resolved is not None
        self.assertEqual(resolved["id"], "codex_execution_timeout_repair")


if __name__ == "__main__":
    unittest.main()
