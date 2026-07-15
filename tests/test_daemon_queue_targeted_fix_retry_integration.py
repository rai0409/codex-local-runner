"""Prompt643 regression: the daemon queue runner automatically invokes
run_targeted_fix_retry on effect-verification failure when --max-fix-attempts > 0,
and the strict effect gate stays authoritative.

Drives the real daemon main() against a /tmp queue + /tmp sandbox repo, mocking
run_targeted_fix_retry (and, for the backward-compat case, run_autonomous_live_loop)
so the tests need no network.
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

TARGET = "automation/orchestration/planned_runner/sandbox_cleanup.py"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@local", "-c", "user.name=t", *args],
        cwd=repo, check=True, capture_output=True,
    )


def _make_sandbox_repo(root: Path) -> Path:
    repo = root / "sandbox_repo"
    (repo / "automation/orchestration/planned_runner").mkdir(parents=True, exist_ok=True)
    (repo / TARGET).write_text("x = 1\n", encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init")
    return repo


def _enqueue(queue_dir: Path, repo: Path, task_id: str) -> None:
    enqueue_task(
        queue_dir,
        {
            "task_id": task_id,
            "kind": "add_function",
            "repo_path": repo.as_posix(),
            "target_file": TARGET,
            "function_name": "p643_marker",
            "expression": "a + b",
        },
    )


def _argv(root: Path, *, max_fix_attempts: int) -> list[str]:
    return [
        "--queue-dir", (root / "queue").as_posix(),
        "--runs-dir", (root / "runs").as_posix(),
        "--work-dir", (root / "work").as_posix(),
        "--max-jobs", "1", "--max-cycles", "1",
        "--max-fix-attempts", str(max_fix_attempts),
        "--sandbox-commit-tag",
        "--autonomous-enable-token", AUTONOMOUS_CYCLE_ENABLE_TOKEN,
        "--live-codex-enable-token", LIVE_CODEX_GATE_ENABLE_TOKEN,
        "--commit-tag-enable-token", SANDBOX_COMMIT_TAG_ENABLE_TOKEN,
    ]


def _resolved_retry(*, generated_prompt_path, effect_spec_path, out_dir, **kwargs):
    """Simulate Codex: attempt 0 effect-failed, fix attempt 1 modifies the file and passes."""
    spec = json.loads(Path(effect_spec_path).read_text(encoding="utf-8"))
    repo = Path(spec["repo_path"])
    tgt = repo / spec["expected_modified_files"][0]
    tgt.write_text(tgt.read_text(encoding="utf-8") + "\ndef p643_marker(a, b):\n    return a + b\n", encoding="utf-8")
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    (out / "targeted_fix_retry_state.json").write_text("{}", encoding="utf-8")
    return {
        "status": "success", "converged": True, "stop_reason": "fix_attempt_succeeded",
        "fix_attempts_used": 1, "codex_invoked_count": 2, "next_action": "commit_tag_gate",
        "commit_performed": False, "tag_performed": False,
        "attempts": [
            {"attempt_index": 0, "is_fix_attempt": False, "status": "blocked", "effect_verification_status": "failed", "failure_digest_path": ""},
            {"attempt_index": 1, "is_fix_attempt": True, "status": "success", "effect_verification_status": "passed", "failure_digest_path": ""},
        ],
    }


def _unresolved_retry(*, generated_prompt_path, effect_spec_path, out_dir, **kwargs):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    (out / "targeted_fix_retry_state.json").write_text("{}", encoding="utf-8")
    return {
        "status": "blocked", "converged": False, "stop_reason": "max_fix_attempts_reached",
        "fix_attempts_used": 1, "codex_invoked_count": 2, "next_action": "manual_review_required",
        "commit_performed": False, "tag_performed": False,
        "attempts": [
            {"attempt_index": 0, "is_fix_attempt": False, "status": "blocked", "effect_verification_status": "failed", "failure_digest_path": "d0.json"},
            {"attempt_index": 1, "is_fix_attempt": True, "status": "blocked", "effect_verification_status": "failed", "failure_digest_path": "d1.json"},
        ],
    }


def _false_success_retry(*, generated_prompt_path, effect_spec_path, out_dir, **kwargs):
    """Adversarial: claims converged but the final attempt's effect did NOT pass."""
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    (out / "targeted_fix_retry_state.json").write_text("{}", encoding="utf-8")
    return {
        "status": "success", "converged": True, "stop_reason": "fix_attempt_succeeded",
        "fix_attempts_used": 1, "codex_invoked_count": 2,
        "attempts": [
            {"attempt_index": 1, "is_fix_attempt": True, "status": "success", "effect_verification_status": "failed", "failure_digest_path": ""},
        ],
    }


def _loop_success(**_kwargs):
    return {"status": "success", "stop_reason": "commit_tag_gate", "codex_invoked_count": 1,
            "per_cycle_effect_verification_statuses": ["passed"], "failure_digest_path": ""}


class DaemonQueueTargetedFixRetryIntegrationTests(unittest.TestCase):
    def _run(self, root: Path, *, max_fix_attempts, retry_fake=None, loop_fake=None):
        patches = []
        if retry_fake is not None:
            patches.append(mock.patch.object(daemon, "run_targeted_fix_retry", new=retry_fake))
        if loop_fake is not None:
            patches.append(mock.patch.object(daemon, "run_autonomous_live_loop", new=loop_fake))
        for p in patches:
            p.start()
        try:
            code = daemon.main(_argv(root, max_fix_attempts=max_fix_attempts))
        finally:
            for p in patches:
                p.stop()
        return code

    def test_effect_failed_triggers_retry_and_resolves_to_done(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            root = Path(raw)
            repo = _make_sandbox_repo(root)
            _enqueue(root / "queue", repo, "fix-resolves")
            code = self._run(root, max_fix_attempts=1, retry_fake=_resolved_retry)
            self.assertEqual(code, 0)
            rep = json.loads((root / "runs" / "fix-resolves" / "run_report.json").read_text())
            self.assertTrue(rep["targeted_fix_invoked"])
            self.assertTrue(rep["targeted_fix_converged"])
            self.assertEqual(rep["status"], "success")
            self.assertEqual(rep["stage"], "done")
            self.assertTrue(rep["sandbox_commit_performed"])
            self.assertTrue(rep["sandbox_tag_performed"])
            self.assertTrue(rep["post_retry_effect_gate_passed"])
            self.assertEqual(rep["per_cycle_effect_verification_statuses"][-1], "passed")
            tasks = list_tasks(root / "queue")
            self.assertIn("fix-resolves.json", tasks["done"])
            self.assertNotIn("fix-resolves.json", tasks["failed"])
            # commit/tag only after passed fix: a sandbox tag exists now.
            tags = subprocess.run(["git", "tag"], cwd=repo, capture_output=True, text=True).stdout.split()
            self.assertIn("sandbox-fix-resolves", tags)

    def test_unresolved_retry_goes_to_failed_no_commit_tag(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            root = Path(raw)
            repo = _make_sandbox_repo(root)
            _enqueue(root / "queue", repo, "fix-unresolved")
            code = self._run(root, max_fix_attempts=1, retry_fake=_unresolved_retry)
            self.assertEqual(code, 1)
            rep = json.loads((root / "runs" / "fix-unresolved" / "run_report.json").read_text())
            self.assertTrue(rep["targeted_fix_invoked"])
            self.assertFalse(rep["targeted_fix_converged"])
            self.assertIn(rep["status"], {"blocked", "failed"})
            self.assertEqual(rep["stage"], "targeted_fix_unresolved")
            self.assertFalse(rep["sandbox_commit_performed"])
            self.assertFalse(rep["sandbox_tag_performed"])
            self.assertTrue(rep["targeted_fix_state_path"])
            tasks = list_tasks(root / "queue")
            self.assertIn("fix-unresolved.json", tasks["failed"])
            self.assertNotIn("fix-unresolved.json", tasks["done"])
            tags = subprocess.run(["git", "tag"], cwd=repo, capture_output=True, text=True).stdout.split()
            self.assertEqual(tags, [])
            self.assertEqual(
                subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip(),
                "1",
            )

    def test_strict_gate_blocks_false_success_after_retry(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            root = Path(raw)
            repo = _make_sandbox_repo(root)
            _enqueue(root / "queue", repo, "fix-false-success")
            code = self._run(root, max_fix_attempts=1, retry_fake=_false_success_retry)
            self.assertEqual(code, 1)
            rep = json.loads((root / "runs" / "fix-false-success" / "run_report.json").read_text())
            self.assertEqual(rep["status"], "blocked")
            self.assertFalse(rep["post_retry_effect_gate_passed"])
            self.assertFalse(rep["sandbox_commit_performed"])
            self.assertFalse(rep["sandbox_tag_performed"])
            self.assertIn("fix-false-success.json", list_tasks(root / "queue")["failed"])

    def test_backward_compatible_when_fix_attempts_zero(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            root = Path(raw)
            repo = _make_sandbox_repo(root)
            _enqueue(root / "queue", repo, "no-fix")

            def _loop_success_and_modify(**kwargs):
                # mirror a passed loop AND modify the file so commit/tag has content
                (repo / TARGET).write_text((repo / TARGET).read_text() + "\ndef p643_marker(a, b):\n    return a + b\n")
                return _loop_success()

            retry_spy = mock.MagicMock()
            code = self._run(root, max_fix_attempts=0, retry_fake=retry_spy, loop_fake=_loop_success_and_modify)
            self.assertEqual(code, 0)
            rep = json.loads((root / "runs" / "no-fix" / "run_report.json").read_text())
            self.assertFalse(rep.get("targeted_fix_invoked"))
            self.assertEqual(rep["status"], "success")
            self.assertEqual(rep["stage"], "done")
            self.assertTrue(rep["sandbox_commit_performed"])
            retry_spy.assert_not_called()
            self.assertIn("no-fix.json", list_tasks(root / "queue")["done"])


if __name__ == "__main__":
    unittest.main()
