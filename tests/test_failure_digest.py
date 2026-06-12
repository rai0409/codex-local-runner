from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from automation.orchestration.planned_runner import live_codex_gate
from automation.orchestration.planned_runner.failure_digest import (
    FAILURE_DIGEST_FILENAME,
    build_failure_digest,
    classify_failure,
)


class FailureClassificationTests(unittest.TestCase):
    def test_classifies_known_failure_classes(self):
        cases = {
            "disabled_missing_enable_token": "enable_token_missing",
            "missing_generated_prompt": "missing_input",
            "effect_spec_invalid": "invalid_input",
            "invalid_prompt_manifest": "invalid_input",
            "codex_cli_unavailable": "environment_unavailable",
            "codex_timeout": "codex_timeout",
            "codex_failed": "codex_execution_failed",
            "effect_verification_failed": "effect_verification_failed",
            "dirty_worktree_outside_allowed_artifacts": "dirty_worktree",
            "targeted_fix_required": "targeted_fix_required",
            "no_progress": "no_progress",
            "max_cycles_reached": "budget_exhausted",
        }
        for stop_reason, expected in cases.items():
            state = {"status": "blocked", "stop_reason": stop_reason}
            self.assertEqual(classify_failure(state), expected, msg=stop_reason)

    def test_success_state_classifies_as_none(self):
        self.assertEqual(classify_failure({"status": "success", "stop_reason": "commit_tag_gate"}), "none")

    def test_unknown_stop_reason_classifies_as_unknown(self):
        self.assertEqual(classify_failure({"status": "blocked", "stop_reason": "mystery"}), "unknown")

    def test_blocked_reason_fallback(self):
        state = {"status": "blocked", "stop_reason": "", "blocked_reason": "no_progress"}
        self.assertEqual(classify_failure(state), "no_progress")


class FailureDigestBuildTests(unittest.TestCase):
    def test_digest_written_with_required_fields(self):
        state = {
            "status": "blocked",
            "stop_reason": "effect_verification_failed",
            "next_action": "inspect_missing_expected_effects",
            "cycle_count": 1,
            "stdout_path": "/tmp/x/codex_stdout.txt",
            "stderr_path": "/tmp/x/codex_stderr.txt",
            "codex_result_path": "/tmp/x/codex_execution_result.json",
            "effect_verification_status": "failed",
            "effect_verification_errors": ["expected modified file did not change: calculator.py"],
            "effect_spec_path": "/tmp/x/spec.json",
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            digest = build_failure_digest(state=state, out_dir=tmp_dir, run_kind="live_codex_gate")
            on_disk = json.loads((Path(tmp_dir) / FAILURE_DIGEST_FILENAME).read_text(encoding="utf-8"))
        self.assertEqual(digest["failure_class"], "effect_verification_failed")
        self.assertTrue(digest["retryable"])
        self.assertEqual(digest["recommended_next_action"], "build_targeted_fix_prompt")
        self.assertIn("/tmp/x/codex_stdout.txt", digest["evidence_paths"])
        self.assertEqual(on_disk["failure_class"], "effect_verification_failed")
        self.assertEqual(on_disk["effect_verification_errors"], state["effect_verification_errors"])

    def test_non_retryable_classes(self):
        for stop_reason in ("disabled_missing_enable_token", "dirty_worktree_outside_allowed_artifacts"):
            with tempfile.TemporaryDirectory() as tmp_dir:
                digest = build_failure_digest(
                    state={"status": "blocked", "stop_reason": stop_reason},
                    out_dir=tmp_dir,
                )
            self.assertFalse(digest["retryable"], msg=stop_reason)


class GateDigestWiringTests(unittest.TestCase):
    def test_failed_gate_run_writes_digest(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp_dir = Path(raw)
            # missing generated prompt -> blocked without invoking codex
            state = live_codex_gate.run_live_codex_gate(
                generated_prompt_path=tmp_dir / "does_not_exist.md",
                out_dir=tmp_dir / "out",
                live_codex_enable_token=live_codex_gate.LIVE_CODEX_GATE_ENABLE_TOKEN,
            )
            digest_path = Path(state["failure_digest_path"])
            self.assertTrue(digest_path.is_file())
            digest = json.loads(digest_path.read_text(encoding="utf-8"))
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(digest["failure_class"], "missing_input")
        self.assertEqual(digest["run_kind"], "live_codex_gate")

    def test_successful_gate_run_has_empty_digest_path(self):
        def _fake_codex(**kwargs):
            stdout_path = kwargs["stdout_path"]
            stderr_path = kwargs["stderr_path"]
            stdout_path.parent.mkdir(parents=True, exist_ok=True)
            stdout_path.write_text("ok\n", encoding="utf-8")
            stderr_path.write_text("", encoding="utf-8")
            result = live_codex_gate._base_result(
                status="success",
                returncode=0,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                stop_reason="codex_completed",
                started_at="2026-01-01T00:00:00Z",
                finished_at="2026-01-01T00:00:01Z",
            )
            return result, ["codex", "exec"], True

        with tempfile.TemporaryDirectory() as raw:
            tmp_dir = Path(raw)
            prompt = tmp_dir / "prompt.md"
            prompt.write_text("safe\n", encoding="utf-8")
            with mock.patch.object(live_codex_gate, "_run_codex_once", new=_fake_codex):
                state = live_codex_gate.run_live_codex_gate(
                    generated_prompt_path=prompt,
                    out_dir=tmp_dir / "out",
                    live_codex_enable_token=live_codex_gate.LIVE_CODEX_GATE_ENABLE_TOKEN,
                )
        self.assertEqual(state["status"], "success")
        self.assertEqual(state["failure_digest_path"], "")


if __name__ == "__main__":
    unittest.main()
