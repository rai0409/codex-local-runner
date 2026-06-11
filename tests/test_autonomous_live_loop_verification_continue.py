from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from automation.orchestration.planned_runner import autonomous_live_loop
from automation.orchestration.planned_runner.autonomous_cycle import (
    AUTONOMOUS_CYCLE_ENABLE_TOKEN,
)
from automation.orchestration.planned_runner.live_codex_gate import (
    LIVE_CODEX_GATE_ENABLE_TOKEN,
)


def _clean_dirty_state(**_kwargs):
    return {
        "status": "ready",
        "next_action": "continue_loop",
        "blocked_reason": "none",
        "dirty_paths": [],
        "dirty_paths_outside_allowed_artifacts": [],
    }


def _fake_live_gate_factory(invocations: list[int]):
    def _fake_live_gate(*, generated_prompt_path, out_dir, **_kwargs):
        invocations.append(1)
        output_root = Path(out_dir)
        result_path = output_root / "codex_execution_result.json"
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(
                {
                    "status": "success",
                    "returncode": 0,
                    "returncode_classification": "success",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return {
            "status": "success",
            "codex_invoked": True,
            "codex_result_path": result_path.as_posix(),
            "next_action": "commit_tag_gate",
            "stop_reason": "codex_completed",
        }

    return _fake_live_gate


class AutonomousLiveLoopVerificationContinueTests(unittest.TestCase):
    def _run_loop(self, *, tmp_dir: str, verification_continue: bool, max_cycles: int = 2):
        invocations: list[int] = []
        prompt_path = Path(tmp_dir) / "generated_prompt.md"
        prompt_path.write_text("safe prompt\n", encoding="utf-8")
        with mock.patch.object(
            autonomous_live_loop,
            "run_live_codex_gate",
            new=_fake_live_gate_factory(invocations),
        ), mock.patch.object(
            autonomous_live_loop,
            "dirty_paths_outside_allowed_artifacts",
            new=_clean_dirty_state,
        ):
            payload = autonomous_live_loop.run_autonomous_live_loop(
                repo_path=tmp_dir,
                out_dir=Path(tmp_dir) / "out",
                generated_prompt_path=prompt_path,
                max_cycles=max_cycles,
                max_seconds=120,
                autonomous_enable_token=AUTONOMOUS_CYCLE_ENABLE_TOKEN,
                live_codex_enable_token=LIVE_CODEX_GATE_ENABLE_TOKEN,
                live_loop_timeout_seconds=10,
                verification_continue=verification_continue,
            )
        return payload, len(invocations)

    def test_default_commit_tag_gate_stops_after_first_cycle(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            payload, gate_calls = self._run_loop(tmp_dir=tmp_dir, verification_continue=False)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["cycle_count"], 1)
        self.assertEqual(payload["codex_invoked_count"], 1)
        self.assertEqual(gate_calls, 1)
        self.assertEqual(payload["stop_reason"], "commit_tag_gate")
        self.assertEqual(payload["next_action"], "commit_tag_gate")
        self.assertFalse(payload["verification_only"])
        self.assertFalse(payload["verification_continue_after_commit_gate"])

    def test_verification_continue_runs_to_max_cycles(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            payload, gate_calls = self._run_loop(tmp_dir=tmp_dir, verification_continue=True)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["cycle_count"], 2)
        self.assertEqual(payload["codex_invoked_count"], 2)
        self.assertEqual(gate_calls, 2)
        self.assertEqual(payload["stop_reason"], "verification_max_cycles_reached")
        self.assertEqual(payload["next_action"], "commit_tag_gate")
        self.assertTrue(payload["verification_only"])
        self.assertTrue(payload["verification_continue_after_commit_gate"])
        self.assertEqual(payload["commit_tag_gate_observed_count"], 2)
        self.assertEqual(payload["commit_tag_gate_observed_cycles"], [1, 2])
        self.assertEqual(len(payload["per_cycle_result_paths"]), 2)
        self.assertEqual(len(payload["per_cycle_state_paths"]), 2)

    def test_runtime_never_commits_or_tags_in_either_mode(self):
        for verification_continue in (False, True):
            with tempfile.TemporaryDirectory() as tmp_dir:
                payload, _ = self._run_loop(
                    tmp_dir=tmp_dir, verification_continue=verification_continue
                )
            self.assertFalse(payload["commit_performed"])
            self.assertFalse(payload["tag_performed"])
            self.assertTrue(payload["local_only"])

    def test_verification_mode_still_requires_enable_tokens(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            prompt_path = Path(tmp_dir) / "generated_prompt.md"
            prompt_path.write_text("safe prompt\n", encoding="utf-8")
            payload = autonomous_live_loop.run_autonomous_live_loop(
                repo_path=tmp_dir,
                out_dir=Path(tmp_dir) / "out",
                generated_prompt_path=prompt_path,
                max_cycles=2,
                max_seconds=120,
                autonomous_enable_token="",
                live_codex_enable_token=LIVE_CODEX_GATE_ENABLE_TOKEN,
                verification_continue=True,
            )
        self.assertEqual(payload["status"], "disabled")
        self.assertEqual(payload["stop_reason"], "missing_autonomous_enable_token")
        self.assertEqual(payload["codex_invoked_count"], 0)
        self.assertTrue(payload["verification_only"])
        self.assertEqual(payload["commit_tag_gate_observed_count"], 0)


if __name__ == "__main__":
    unittest.main()
