"""Prompt638B regression: a queued task whose effect verification failed must
not be committed/tagged, must get a blocked/failed run_report, must move to the
queue failed/ directory, and must never appear in done/.

This drives the real daemon main() against a /tmp queue + /tmp sandbox repo,
mocking only the live loop so the test needs no network. The mocked loop reports
status="success" with per_cycle_effect_verification_statuses=["failed"] to prove
the DAEMON-level strict gate independently blocks success (defense in depth).
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import run_task_queue_daemon as daemon  # noqa: E402

from automation.orchestration.planned_runner.autonomous_cycle import (  # noqa: E402
    AUTONOMOUS_CYCLE_ENABLE_TOKEN,
)
from automation.orchestration.planned_runner.commit_tag import (  # noqa: E402
    SANDBOX_COMMIT_TAG_ENABLE_TOKEN,
)
from automation.orchestration.planned_runner.daemon_queue import (  # noqa: E402
    enqueue_task,
    list_tasks,
)
from automation.orchestration.planned_runner.live_codex_gate import (  # noqa: E402
    LIVE_CODEX_GATE_ENABLE_TOKEN,
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@local", "-c", "user.name=t", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _make_sandbox_repo(root: Path) -> Path:
    repo = root / "sandbox_repo"
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "target.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init")
    return repo


def _effect_failed_loop_state(**_kwargs):
    # Loop wrongly reports success but records a failed effect status. The daemon
    # gate must still block.
    return {
        "status": "success",
        "stop_reason": "commit_tag_gate",
        "codex_invoked_count": 1,
        "per_cycle_effect_verification_statuses": ["failed"],
        "failure_digest_path": "",
    }


class DaemonQueueEffectFailedBlocksCommitTagTests(unittest.TestCase):
    def test_effect_failed_blocks_commit_tag_and_routes_to_failed(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            root = Path(raw)
            repo = _make_sandbox_repo(root)
            queue_dir = root / "queue"
            runs_dir = root / "runs"
            work_dir = root / "work"

            enqueue_task(
                queue_dir,
                {
                    "task_id": "effect-fail-task",
                    "kind": "add_function",
                    "repo_path": repo.as_posix(),
                    "target_file": "target.py",
                    "function_name": "added_fn",
                    "expression": "a + b",
                },
            )

            argv = [
                "--queue-dir", queue_dir.as_posix(),
                "--runs-dir", runs_dir.as_posix(),
                "--work-dir", work_dir.as_posix(),
                "--max-jobs", "1",
                "--max-cycles", "1",
                "--sandbox-commit-tag",
                "--autonomous-enable-token", AUTONOMOUS_CYCLE_ENABLE_TOKEN,
                "--live-codex-enable-token", LIVE_CODEX_GATE_ENABLE_TOKEN,
                "--commit-tag-enable-token", SANDBOX_COMMIT_TAG_ENABLE_TOKEN,
            ]

            with mock.patch.object(
                daemon, "run_autonomous_live_loop", new=_effect_failed_loop_state
            ):
                exit_code = daemon.main(argv)

            # Non-zero exit because the task was blocked.
            self.assertEqual(exit_code, 1)

            run_report = json.loads(
                (runs_dir / "effect-fail-task" / "run_report.json").read_text(encoding="utf-8")
            )
            self.assertIn(run_report["status"], {"blocked", "failed"})
            self.assertNotEqual(run_report["stage"], "done")
            self.assertFalse(run_report["sandbox_commit_performed"])
            self.assertFalse(run_report["sandbox_tag_performed"])
            self.assertEqual(run_report["per_cycle_effect_verification_statuses"], ["failed"])
            self.assertFalse(run_report.get("effect_gate_passed"))

            tasks = list_tasks(queue_dir)
            self.assertIn("effect-fail-task.json", tasks["failed"])
            self.assertNotIn("effect-fail-task.json", tasks["done"])

            # The sandbox repo must not have a new commit or a sandbox tag.
            tags = subprocess.run(
                ["git", "tag"], cwd=repo, check=True, capture_output=True, text=True
            ).stdout.split()
            self.assertEqual(tags, [])
            log_count = subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual(log_count, "1")


if __name__ == "__main__":
    unittest.main()
