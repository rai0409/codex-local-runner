from __future__ import annotations

from datetime import datetime
from pathlib import Path
import tempfile
import unittest

from automation.execution.codex_live_transport import CodexLiveExecutionTransport


class CodexLiveTransportTests(unittest.TestCase):
    def _fixed_now(self) -> datetime:
        return datetime(2026, 4, 18, 10, 0, 0)

    def test_live_transport_success_with_verify_passed(self) -> None:
        execute_calls: list[dict[str, object]] = []
        verify_calls: list[dict[str, object]] = []

        def execute_fn(*, task, prompt, work_root, timeout_seconds):
            execute_calls.append(
                {
                    "task": task,
                    "prompt": prompt,
                    "work_root": work_root,
                    "timeout_seconds": timeout_seconds,
                }
            )
            return {
                "status": "completed",
                "started_at": "2026-04-18T10:00:00",
                "finished_at": "2026-04-18T10:00:03",
                "stdout_path": "/tmp/stdout.txt",
                "stderr_path": "/tmp/stderr.txt",
                "changed_files": ["automation/execution/codex_executor_adapter.py"],
                "additions": 7,
                "deletions": 2,
                "generated_patch_summary": "applied planned changes",
                "artifacts": [{"name": "stdout", "path": "/tmp/stdout.txt"}],
                "error": "",
            }

        def verify_fn(commands, cwd):
            verify_calls.append({"commands": list(commands), "cwd": cwd})
            return {
                "status": "passed",
                "reason": "validation_passed",
                "command_results": [{"command": "python3 -m unittest tests.test_codex_executor_adapter -v"}],
            }

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            prompt_path = root / "compiled_prompt.md"
            prompt_path.write_text("prompt content", encoding="utf-8")
            work_dir = root / "unit"
            work_dir.mkdir(parents=True, exist_ok=True)

            transport = CodexLiveExecutionTransport(
                repo_path=str(root),
                execute_fn=execute_fn,
                verify_fn=verify_fn,
                now=self._fixed_now,
            )
            launch = transport.launch_job(
                job_id="job-live",
                pr_id="pr-01",
                prompt_path=str(prompt_path),
                work_dir=str(work_dir),
                metadata={"validation_commands": ["python3 -m unittest tests.test_codex_executor_adapter -v"]},
            )
            polled = transport.poll_status(run_id=str(launch["run_id"]))
            artifacts = transport.collect_artifacts(run_id=str(launch["run_id"]))

        self.assertEqual(launch["status"], "completed")
        self.assertEqual(polled["status"], "completed")
        self.assertEqual(polled["verify"]["status"], "passed")
        self.assertIsNone(polled["failure_type"])
        self.assertIsNone(polled["failure_message"])
        self.assertEqual(polled["additions"], 7)
        self.assertEqual(polled["deletions"], 2)
        self.assertEqual(len(execute_calls), 1)
        self.assertEqual(len(verify_calls), 1)
        self.assertIn("raw_transport", artifacts)

    def test_execution_failure_is_classified_deterministically(self) -> None:
        def execute_fn(*, task, prompt, work_root, timeout_seconds):
            return {
                "status": "failed",
                "error": "codex exited with return code 2",
                "stdout_path": "/tmp/stdout.txt",
                "stderr_path": "/tmp/stderr.txt",
                "artifacts": [],
            }

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            prompt_path = root / "compiled_prompt.md"
            prompt_path.write_text("prompt content", encoding="utf-8")
            work_dir = root / "unit"
            work_dir.mkdir(parents=True, exist_ok=True)

            transport = CodexLiveExecutionTransport(
                repo_path=str(root),
                execute_fn=execute_fn,
                now=self._fixed_now,
            )
            launch = transport.launch_job(
                job_id="job-live-fail",
                pr_id="pr-01",
                prompt_path=str(prompt_path),
                work_dir=str(work_dir),
                metadata={},
            )
            polled = transport.poll_status(run_id=str(launch["run_id"]))

        self.assertEqual(polled["status"], "failed")
        self.assertEqual(polled["failure_type"], "execution_failure")
        self.assertIn("return code 2", polled["failure_message"])
        self.assertEqual(polled["verify"]["status"], "not_run")

    def test_timeout_is_not_treated_as_success(self) -> None:
        def execute_fn(*, task, prompt, work_root, timeout_seconds):
            return {
                "status": "timed_out",
                "error": "Codex timed out after 600 seconds.",
                "stdout_path": "/tmp/stdout.txt",
                "stderr_path": "/tmp/stderr.txt",
                "artifacts": [],
            }

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            prompt_path = root / "compiled_prompt.md"
            prompt_path.write_text("prompt content", encoding="utf-8")
            work_dir = root / "unit"
            work_dir.mkdir(parents=True, exist_ok=True)

            transport = CodexLiveExecutionTransport(
                repo_path=str(root),
                execute_fn=execute_fn,
                now=self._fixed_now,
            )
            run_id = str(
                transport.launch_job(
                    job_id="job-live-timeout",
                    pr_id="pr-01",
                    prompt_path=str(prompt_path),
                    work_dir=str(work_dir),
                    metadata={},
                )["run_id"]
            )
            polled = transport.poll_status(run_id=run_id)

        self.assertEqual(polled["status"], "timed_out")
        self.assertEqual(polled["failure_type"], "transport_timeout")

    def test_missing_prompt_is_transport_submission_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            work_dir = root / "unit"
            work_dir.mkdir(parents=True, exist_ok=True)
            missing_prompt = root / "missing_prompt.md"

            transport = CodexLiveExecutionTransport(
                repo_path=str(root),
                now=self._fixed_now,
            )
            launch = transport.launch_job(
                job_id="job-live-missing",
                pr_id="pr-01",
                prompt_path=str(missing_prompt),
                work_dir=str(work_dir),
                metadata={},
            )
            polled = transport.poll_status(run_id=str(launch["run_id"]))

        self.assertEqual(polled["status"], "not_started")
        self.assertEqual(polled["failure_type"], "transport_submission_failure")
        self.assertIn("compiled prompt not found", polled["failure_message"])

    def test_missing_verify_evidence_is_conservative(self) -> None:
        def execute_fn(*, task, prompt, work_root, timeout_seconds):
            return {
                "status": "completed",
                "stdout_path": "/tmp/stdout.txt",
                "stderr_path": "/tmp/stderr.txt",
                "artifacts": [],
                "error": "",
            }

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            prompt_path = root / "compiled_prompt.md"
            prompt_path.write_text("prompt content", encoding="utf-8")
            work_dir = root / "unit"
            work_dir.mkdir(parents=True, exist_ok=True)

            transport = CodexLiveExecutionTransport(
                repo_path=str(root),
                execute_fn=execute_fn,
                now=self._fixed_now,
            )
            run_id = str(
                transport.launch_job(
                    job_id="job-live-no-verify",
                    pr_id="pr-01",
                    prompt_path=str(prompt_path),
                    work_dir=str(work_dir),
                    metadata={},
                )["run_id"]
            )
            polled = transport.poll_status(run_id=run_id)

        self.assertEqual(polled["status"], "completed")
        self.assertEqual(polled["verify"]["status"], "not_run")
        self.assertEqual(polled["failure_type"], "missing_signal")

    def test_deterministic_output_for_equivalent_mocked_live_response(self) -> None:
        def execute_fn(*, task, prompt, work_root, timeout_seconds):
            return {
                "status": "failed",
                "error": "execution failed",
                "stdout_path": "/tmp/stdout.txt",
                "stderr_path": "/tmp/stderr.txt",
                "artifacts": [],
            }

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            prompt_path = root / "compiled_prompt.md"
            prompt_path.write_text("prompt content", encoding="utf-8")
            work_dir = root / "unit"
            work_dir.mkdir(parents=True, exist_ok=True)

            transport_a = CodexLiveExecutionTransport(
                repo_path=str(root),
                execute_fn=execute_fn,
                now=self._fixed_now,
            )
            run_id_a = str(
                transport_a.launch_job(
                    job_id="job-live-deterministic",
                    pr_id="pr-01",
                    prompt_path=str(prompt_path),
                    work_dir=str(work_dir),
                    metadata={},
                )["run_id"]
            )
            payload_a = transport_a.poll_status(run_id=run_id_a)

            transport_b = CodexLiveExecutionTransport(
                repo_path=str(root),
                execute_fn=execute_fn,
                now=self._fixed_now,
            )
            run_id_b = str(
                transport_b.launch_job(
                    job_id="job-live-deterministic",
                    pr_id="pr-01",
                    prompt_path=str(prompt_path),
                    work_dir=str(work_dir),
                    metadata={},
                )["run_id"]
            )
            payload_b = transport_b.poll_status(run_id=run_id_b)

        comparable_keys = (
            "status",
            "failure_type",
            "failure_message",
            "verify",
            "attempt_count",
            "started_at",
            "finished_at",
        )
        self.assertEqual({k: payload_a[k] for k in comparable_keys}, {k: payload_b[k] for k in comparable_keys})


if __name__ == "__main__":
    unittest.main()
