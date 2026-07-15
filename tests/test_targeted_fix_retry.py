from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from automation.orchestration.planned_runner import targeted_fix_retry
from automation.orchestration.planned_runner.failure_digest import build_failure_digest


def _spec_file(tmp_dir: Path) -> Path:
    spec_path = tmp_dir / "spec.json"
    spec_path.write_text(
        json.dumps(
            {
                "repo_path": tmp_dir.as_posix(),
                "expected_modified_files": ["calculator.py"],
                "expected_unmodified_files": [],
                "required_text": {"calculator.py": ["def subtract(a, b):"]},
                "forbidden_paths": [],
                "allow_extra_files": False,
            }
        ),
        encoding="utf-8",
    )
    return spec_path


def _fake_gate_factory(outcomes: list[str], calls: list[dict]):
    """outcomes[i] in {'success', 'effect_fail', 'token_fail'} for attempt i."""

    def _fake_gate(*, generated_prompt_path, out_dir, **kwargs):
        index = len(calls)
        outcome = outcomes[min(index, len(outcomes) - 1)]
        calls.append({"prompt": str(generated_prompt_path), "outcome": outcome})
        out_root = Path(out_dir)
        out_root.mkdir(parents=True, exist_ok=True)
        if outcome == "success":
            return {
                "status": "success",
                "codex_invoked": True,
                "stop_reason": "codex_completed",
                "effect_verification_status": "passed",
                "failure_digest_path": "",
            }
        if outcome == "effect_fail":
            state = {
                "status": "blocked",
                "stop_reason": "effect_verification_failed",
                "effect_verification_status": "failed",
                "effect_verification_errors": ["required text missing in calculator.py: 'def subtract(a, b):'"],
            }
        else:
            state = {"status": "disabled", "stop_reason": "disabled_missing_enable_token"}
        digest = build_failure_digest(state=state, out_dir=out_root, run_kind="live_codex_gate")
        return {
            **state,
            "codex_invoked": outcome != "token_fail",
            "failure_digest_path": digest["digest_path"],
        }

    return _fake_gate


class TargetedFixRetryTests(unittest.TestCase):
    def _run(self, tmp_dir: Path, outcomes: list[str], max_fix_attempts: int = 1):
        calls: list[dict] = []
        prompt = tmp_dir / "prompt.md"
        prompt.write_text("original task\n", encoding="utf-8")
        with mock.patch.object(
            targeted_fix_retry, "run_live_codex_gate", new=_fake_gate_factory(outcomes, calls)
        ):
            payload = targeted_fix_retry.run_targeted_fix_retry(
                generated_prompt_path=prompt,
                effect_spec_path=_spec_file(tmp_dir),
                out_dir=tmp_dir / "out",
                live_codex_enable_token="token",
                max_fix_attempts=max_fix_attempts,
            )
        return payload, calls

    def test_first_attempt_success_needs_no_fix(self):
        with tempfile.TemporaryDirectory() as raw:
            payload, calls = self._run(Path(raw), ["success"])
        self.assertTrue(payload["converged"])
        self.assertEqual(payload["fix_attempts_used"], 0)
        self.assertEqual(payload["stop_reason"], "first_attempt_succeeded")
        self.assertEqual(len(calls), 1)

    def test_effect_failure_then_fix_converges(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_dir = Path(raw)
            payload, calls = self._run(tmp_dir, ["effect_fail", "success"])
            fix_text = Path(payload["fix_prompt_paths"][0]).read_text(encoding="utf-8")
        self.assertTrue(payload["converged"])
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["fix_attempts_used"], 1)
        self.assertEqual(payload["stop_reason"], "fix_attempt_succeeded")
        self.assertEqual(len(calls), 2)
        self.assertIn("fix_prompt_attempt_1.md", calls[1]["prompt"])
        self.assertEqual(len(payload["fix_prompt_paths"]), 1)
        self.assertIn("def subtract(a, b):", fix_text)

    def test_bounded_by_max_fix_attempts(self):
        with tempfile.TemporaryDirectory() as raw:
            payload, calls = self._run(Path(raw), ["effect_fail", "effect_fail", "effect_fail"], max_fix_attempts=1)
        self.assertFalse(payload["converged"])
        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["stop_reason"], "max_fix_attempts_reached")
        self.assertEqual(len(calls), 2)

    def test_fix_attempts_hard_cap(self):
        with tempfile.TemporaryDirectory() as raw:
            payload, calls = self._run(Path(raw), ["effect_fail"] * 10, max_fix_attempts=99)
        self.assertEqual(payload["max_fix_attempts"], targeted_fix_retry.MAX_FIX_ATTEMPTS_CAP)
        self.assertEqual(len(calls), targeted_fix_retry.MAX_FIX_ATTEMPTS_CAP + 1)

    def test_non_retryable_failure_stops_without_fix(self):
        with tempfile.TemporaryDirectory() as raw:
            payload, calls = self._run(Path(raw), ["token_fail"])
        self.assertFalse(payload["converged"])
        self.assertTrue(payload["stop_reason"].startswith("non_retryable_failure:"))
        self.assertEqual(len(calls), 1)
        self.assertEqual(payload["fix_prompt_paths"], [])

    def test_never_commits_or_tags(self):
        with tempfile.TemporaryDirectory() as raw:
            payload, _ = self._run(Path(raw), ["effect_fail", "success"])
        self.assertFalse(payload["commit_performed"])
        self.assertFalse(payload["tag_performed"])
        self.assertTrue(payload["local_only"])


if __name__ == "__main__":
    unittest.main()
