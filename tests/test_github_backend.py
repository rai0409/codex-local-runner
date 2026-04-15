from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from orchestrator.github_backend import ArtifactGitHubStateBackend
from orchestrator.github_backend import LiveReadOnlyGitHubStateBackend
from orchestrator.github_backend import build_github_progression_receipt
from orchestrator.github_backend import resolve_github_state_backend


class GitHubBackendTests(unittest.TestCase):
    def test_backend_collect_is_deterministic_for_same_inputs(self) -> None:
        backend = ArtifactGitHubStateBackend()
        request_payload = {
            "repo": "codex-local-runner",
            "metadata": {
                "execution_target": {
                    "target_ref": "refs/heads/main",
                    "source_sha": "a" * 40,
                    "base_sha": "b" * 40,
                }
            },
        }
        result_payload = {
            "github_state": {
                "repository": "rai0409/codex-local-runner",
                "required_checks": ["unit", "lint"],
                "passing_checks": ["lint", "unit"],
                "review_state": "approved",
                "required_approvals": 1,
                "approvals": 1,
                "mergeable": True,
                "is_draft": False,
                "pr_number": 42,
            }
        }

        first = backend.collect(request_payload=request_payload, result_payload=result_payload)
        second = backend.collect(request_payload=request_payload, result_payload=result_payload)

        self.assertEqual(first, second)
        self.assertEqual(first["mode"], "read_only")
        self.assertFalse(first["write_actions_allowed"])
        self.assertEqual(first["progression"]["state"], "ready")
        self.assertEqual(first["source"]["kind"], "artifact")

    def test_missing_github_state_is_conservative(self) -> None:
        backend = ArtifactGitHubStateBackend()
        snapshot = backend.collect(
            request_payload={"repo": "codex-local-runner"},
            result_payload={},
        )

        self.assertFalse(snapshot["state_available"])
        self.assertEqual(snapshot["progression"]["state"], "unavailable")
        self.assertIn("github_state_unavailable", snapshot["progression"]["conservative_reasons"])
        self.assertFalse(snapshot["write_actions_allowed"])
        self.assertEqual(snapshot["source"]["kind"], "artifact")

    def test_policy_link_does_not_expand_auto_pr_candidate(self) -> None:
        backend = ArtifactGitHubStateBackend()
        signals = backend.collect(
            request_payload={"repo": "codex-local-runner"},
            result_payload={},
        )

        receipt = build_github_progression_receipt(
            github_signals=signals,
            progression_state="manual_only",
            policy_eligible=False,
            auto_pr_candidate=False,
        )

        self.assertFalse(
            receipt["policy_link"]["ready_for_future_auto_pr_progression"],
        )
        self.assertFalse(receipt["policy_link"]["auto_pr_candidate_ready"])
        self.assertEqual(receipt["mode"], "read_only")
        self.assertFalse(receipt["write_actions_allowed"])

    def test_live_read_only_backend_uses_live_state_when_available(self) -> None:
        backend = LiveReadOnlyGitHubStateBackend(
            fetch_state=lambda **_: {
                "repository": "rai0409/codex-local-runner",
                "target_ref": "refs/heads/main",
                "required_checks": ["unit"],
                "passing_checks": ["unit"],
                "review_state": "approved",
                "mergeability_state": "clean",
                "is_draft": False,
                "pr_number": 21,
            }
        )
        snapshot = backend.collect(
            request_payload={
                "repo": "codex-local-runner",
                "metadata": {"execution_target": {"target_ref": "refs/heads/main"}},
            },
            result_payload={},
        )

        self.assertEqual(snapshot["backend"], "live_read_only")
        self.assertEqual(snapshot["mode"], "read_only")
        self.assertFalse(snapshot["write_actions_allowed"])
        self.assertEqual(snapshot["state_source"], "live.read_only")
        self.assertEqual(snapshot["source"]["kind"], "live_read_only")
        self.assertEqual(snapshot["progression"]["state"], "ready")

    def test_live_read_only_backend_falls_back_to_artifact_conservatively(self) -> None:
        backend = LiveReadOnlyGitHubStateBackend(fetch_state=lambda **_: {})
        snapshot = backend.collect(
            request_payload={"repo": "codex-local-runner"},
            result_payload={
                "github_state": {
                    "repository": "rai0409/codex-local-runner",
                    "target_ref": "refs/heads/main",
                    "required_checks": ["unit"],
                    "passing_checks": ["unit"],
                    "review_state": "approved",
                    "mergeability_state": "clean",
                    "is_draft": False,
                }
            },
        )

        self.assertEqual(snapshot["backend"], "live_read_only")
        self.assertEqual(snapshot["source"]["kind"], "artifact_fallback")
        self.assertTrue(snapshot["source"]["fallback_to_artifact"])
        self.assertTrue(snapshot["state_source"].startswith("artifact_fallback:"))
        self.assertIn("github_live_state_unavailable", snapshot["progression"]["conservative_reasons"])
        self.assertEqual(snapshot["progression"]["state"], "blocked")
        self.assertFalse(snapshot["write_actions_allowed"])

    def test_backend_resolution_defaults_to_artifact_and_supports_live_mode(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            backend = resolve_github_state_backend()
            self.assertIsInstance(backend, ArtifactGitHubStateBackend)

        with patch.dict(os.environ, {"CODEX_GITHUB_STATE_BACKEND": "live_read_only"}, clear=True):
            backend = resolve_github_state_backend()
            self.assertIsInstance(backend, LiveReadOnlyGitHubStateBackend)


if __name__ == "__main__":
    unittest.main()
