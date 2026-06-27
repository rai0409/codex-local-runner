from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from automation.orchestration.planned_runner.end_to_end_unattended_project_run import (
    build_prompt667_project_goal,
    run_end_to_end_unattended_project_run,
)
from automation.orchestration.planned_runner.project_level_completion_gate import PROMPT_EVIDENCE


REPO_ROOT = Path(__file__).resolve().parents[1]


class EndToEndUnattendedProjectRunTests(unittest.TestCase):
    def _copy_repo(self, tmp: Path) -> Path:
        repo = tmp / "repo"
        repo.mkdir()
        for spec in PROMPT_EVIDENCE.values():
            target = repo / spec["report"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / spec["report"], target)
        for surface in [
            "automation/execution/codex_executor_adapter.py",
            "automation/orchestration/planned_runner/runtime_internal_execution_adapter.py",
            "automation/orchestration/planned_runner/bounded_unattended_acceptance.py",
            "automation/orchestration/planned_runner/long_running_daemon_acceptance.py",
            "automation/orchestration/planned_runner/daemon.py",
            "automation/orchestration/planned_runner/daemon_queue.py",
            "automation/orchestration/planned_runner/daemon_state.py",
            "automation/orchestration/planned_runner/daemon_lock.py",
            "scripts/run_task_queue_daemon.py",
        ]:
            path = repo / surface
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# fixture\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@example.local", "-c", "user.name=T", "commit", "-q", "-m", "fixture"],
            cwd=repo,
            check=True,
        )
        for spec in PROMPT_EVIDENCE.values():
            subprocess.run(["git", "tag", spec["tag"]], cwd=repo, check=True)
        return repo

    def _run(self, repo: Path, goal=None):
        return run_end_to_end_unattended_project_run(
            repo_root=repo,
            out_dir=repo / "artifacts" / "autonomous_runtime" / "prompt667_final_project_run",
            run_id="prompt667-test",
            project_goal=goal,
        )

    def test_final_e2e_run_completes_project_level_autonomy(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
            required = [
                "project_goal.json",
                "task_queue.json",
                "run_state.json",
                "evidence_summary.json",
                "final_marker.json",
            ]
            for name in required:
                self.assertTrue((repo / "artifacts" / "autonomous_runtime" / "prompt667_final_project_run" / name).is_file())
            self.assertTrue((repo / "docs" / "autonomous_runtime" / "end_to_end_unattended_project_run_acceptance.md").is_file())
            self.assertTrue((repo / "docs" / "autonomous_runtime" / "project_level_autonomy_final_audit.md").is_file())
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["project_level_autonomy_complete"])
        self.assertEqual(result["queue_item_count"], 3)
        self.assertTrue(result["completion_gate_executed_after_final_e2e"])

    def test_safe_project_goal_is_required_and_unsafe_goal_rejected(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            goal = build_prompt667_project_goal(run_id="prompt667-test")
            goal["goal_text"] = "git push origin main"
            result = self._run(repo, goal=goal)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["stop_reason"], "unsafe_project_goal")
        self.assertTrue(result["unsafe_project_goal_rejected"])
        self.assertFalse(result["project_level_autonomy_complete"])

    def test_missing_approval_blocks_execution(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            goal = build_prompt667_project_goal(run_id="prompt667-test")
            goal["approved_for_execution"] = False
            result = self._run(repo, goal=goal)
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["project_level_autonomy_complete"])


if __name__ == "__main__":
    unittest.main()
