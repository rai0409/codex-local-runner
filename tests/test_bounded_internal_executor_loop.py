from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from automation.execution.codex_executor_adapter import CodexExecutorAdapter
from automation.orchestration.planned_runner.bounded_internal_executor_loop import (
    ProofCodexExecutionTransport,
    build_synthetic_prompt662_cycles,
    run_bounded_internal_executor_loop,
)


class BoundedInternalExecutorLoopTests(unittest.TestCase):
    def _run(self, tmp: Path, cycles=None, **kwargs):
        out = tmp / "out"
        if cycles is None:
            cycles = build_synthetic_prompt662_cycles(out)
        return run_bounded_internal_executor_loop(
            repo_root=tmp,
            out_dir=out,
            cycles=cycles,
            **kwargs,
        )

    def test_successful_bounded_two_cycle_local_proof(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp = Path(raw)
            result = self._run(tmp)
        self.assertEqual(result["status"], "success", msg=result["errors"])
        self.assertTrue(result["internal_codex_executor_used"])
        self.assertEqual(result["cycle_count"], 2)
        self.assertEqual(result["stop_reason"], "max_cycles_reached")
        self.assertTrue(result["local_only_evidence_captured"])
        self.assertEqual(len(result["artifact_paths"]), 2)

    def test_internal_codex_executor_route_detected(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            result = self._run(Path(raw))
        self.assertTrue(result["internal_codex_executor_available"])
        self.assertEqual(
            result["internal_codex_executor_entrypoint"],
            "automation.execution.codex_executor_adapter.CodexExecutorAdapter",
        )

    def test_approved_for_execution_false_blocks_execution(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp = Path(raw)
            cycles = build_synthetic_prompt662_cycles(tmp / "out")
            cycles[0]["approved_for_execution"] = False
            result = self._run(tmp, cycles=cycles)
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["internal_codex_executor_used"])
        self.assertEqual(result["cycle_count"], 0)
        self.assertEqual(result["stop_reason"], "approval_missing")

    def test_missing_approval_blocks_execution(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp = Path(raw)
            cycles = build_synthetic_prompt662_cycles(tmp / "out")
            del cycles[0]["approved_for_execution"]
            result = self._run(tmp, cycles=cycles)
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["internal_codex_executor_used"])
        self.assertEqual(result["stop_reason"], "approval_missing")

    def test_duplicate_prompt_fingerprint_stop(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp = Path(raw)
            cycles = build_synthetic_prompt662_cycles(tmp / "out")
            cycles[1]["prompt_path"] = cycles[0]["prompt_path"]
            result = self._run(tmp, cycles=cycles)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["cycle_count"], 1)
        self.assertEqual(result["stop_reason"], "duplicate_prompt_fingerprint")

    def test_max_cycles_stop_and_hard_cap(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp = Path(raw)
            out = tmp / "out"
            cycles = build_synthetic_prompt662_cycles(out)
            for index in (3, 4):
                prompt_path = out / "prompts" / f"prompt662_cycle_{index}_local_proof.md"
                prompt_path.parent.mkdir(parents=True, exist_ok=True)
                prompt_path.write_text(f"cycle {index} unique local proof\n", encoding="utf-8")
                cycles.append(
                    {
                        "prompt_id": f"prompt662_cycle_{index}_local_proof",
                        "prompt_path": prompt_path.as_posix(),
                        "approved_for_execution": True,
                        "evidence_path": f"artifacts/autonomous_runtime/prompt662/cycle_{index}_evidence.json",
                    }
                )
            result = self._run(tmp, cycles=cycles, max_cycles=99)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["cycle_count"], 3)
        self.assertTrue(result["max_cycles_enforced"])
        self.assertEqual(result["max_cycles"], 3)

    def test_failure_threshold_stop(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp = Path(raw)
            out = tmp / "out"
            transport = ProofCodexExecutionTransport(out_dir=out, fail_on_cycle=1)
            result = run_bounded_internal_executor_loop(
                repo_root=tmp,
                out_dir=out,
                cycles=build_synthetic_prompt662_cycles(out),
                executor_adapter=CodexExecutorAdapter(transport=transport),
                failure_threshold=1,
            )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["stop_reason"], "failure_threshold_reached")
        self.assertEqual(result["cycle_count"], 1)

    def test_unsafe_artifact_path_rejection(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp = Path(raw)
            cycles = build_synthetic_prompt662_cycles(tmp / "out")
            cycles[0]["evidence_path"] = "../outside.json"
            result = self._run(tmp, cycles=cycles)
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["internal_codex_executor_used"])
        self.assertEqual(result["stop_reason"], "safety_gate_failed")

    def test_remote_action_prohibition(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp = Path(raw)
            cycles = build_synthetic_prompt662_cycles(tmp / "out")
            Path(cycles[0]["prompt_path"]).write_text("git push origin main\n", encoding="utf-8")
            result = self._run(tmp, cycles=cycles)
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["internal_codex_executor_used"])

    def test_destructive_action_prohibition(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp = Path(raw)
            cycles = build_synthetic_prompt662_cycles(tmp / "out")
            Path(cycles[0]["prompt_path"]).write_text("rm -rf /tmp/example\n", encoding="utf-8")
            result = self._run(tmp, cycles=cycles)
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["internal_codex_executor_used"])

    def test_secret_cookie_browser_profile_env_private_session_path_rejection(self):
        bad_paths = [
            "artifacts/autonomous_runtime/.env/cycle.json",
            "artifacts/autonomous_runtime/cookies/cycle.json",
            "artifacts/autonomous_runtime/browser_profiles/cycle.json",
            "artifacts/autonomous_runtime/private_sessions/cycle.json",
            "artifacts/autonomous_runtime/credentials/cycle.json",
        ]
        for bad_path in bad_paths:
            with self.subTest(bad_path=bad_path), tempfile.TemporaryDirectory(dir="/tmp") as raw:
                tmp = Path(raw)
                cycles = build_synthetic_prompt662_cycles(tmp / "out")
                cycles[0]["evidence_path"] = bad_path
                result = self._run(tmp, cycles=cycles)
            self.assertEqual(result["status"], "blocked")
            self.assertFalse(result["internal_codex_executor_used"])

    def test_per_cycle_evidence_report_presence_and_terminal_stop_reason(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            result = self._run(Path(raw))
            self.assertEqual(result["stop_reason"], "max_cycles_reached")
            for artifact_path in result["artifact_paths"]:
                self.assertTrue(Path(artifact_path).is_file())


if __name__ == "__main__":
    unittest.main()
