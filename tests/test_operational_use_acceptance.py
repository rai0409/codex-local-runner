from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from automation.orchestration.planned_runner.operational_use_acceptance import (
    build_prompt668_operational_goal,
    run_operational_use_acceptance,
    verify_prompt667_baseline,
)
from automation.orchestration.planned_runner.project_level_completion_gate import PROMPT_EVIDENCE


REPO_ROOT = Path(__file__).resolve().parents[1]


class OperationalUseAcceptanceTests(unittest.TestCase):
    def _copy_repo(self, tmp: Path) -> Path:
        repo = tmp / "repo"
        repo.mkdir()
        for spec in PROMPT_EVIDENCE.values():
            target = repo / spec["report"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / spec["report"], target)
        for extra in [
            "artifacts/autonomous_runtime/prompt667_report.json",
            "artifacts/autonomous_runtime/prompt667_final_project_run/final_project_run_report.json",
            "docs/autonomous_runtime/project_level_autonomy_final_audit.md",
        ]:
            source = REPO_ROOT / extra
            target = repo / extra
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@example.local", "-c", "user.name=T", "commit", "-q", "-m", "fixture"],
            cwd=repo,
            check=True,
        )
        return repo

    def _run(self, repo: Path, goal=None):
        return run_operational_use_acceptance(
            repo_root=repo,
            out_dir=repo / "artifacts/autonomous_runtime/prompt668_operational_use",
            run_id="prompt668-test",
            operational_goal=goal,
        )

    def test_prompt667_baseline_verification(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = verify_prompt667_baseline(repo)
        self.assertTrue(result["prompt667_report_exists"])
        self.assertTrue(result["prompt667_final_audit_exists"])
        self.assertTrue(result["project_level_autonomy_complete"])

    def test_operational_use_run_succeeds(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
            base = repo / "artifacts/autonomous_runtime/prompt668_operational_use"
            for name in [
                "operational_goal.json",
                "task_queue.json",
                "run_state.json",
                "evidence_summary.json",
                "operational_marker.json",
            ]:
                self.assertTrue((base / name).is_file())
            self.assertTrue((repo / "docs/autonomous_runtime/operational_use_acceptance.md").is_file())
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["queue_item_count"], 3)
        self.assertTrue(result["no_human_intervention_during_run_verified"])
        self.assertTrue(result["internal_executor_safety_gate_verified"])

    def test_unsafe_operational_goal_is_rejected(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            goal = build_prompt668_operational_goal(run_id="prompt668-test")
            goal["goal_text"] = "git push origin main"
            result = self._run(repo, goal=goal)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["stop_reason"], "unsafe_operational_goal")
        self.assertTrue(result["unsafe_operational_goal_rejected"])

    def test_missing_approval_blocks_goal(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            goal = build_prompt668_operational_goal(run_id="prompt668-test")
            goal["approved_for_execution"] = False
            result = self._run(repo, goal=goal)
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result.get("internal_codex_executor_used", False))

    def test_unsafe_path_rejection(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = run_operational_use_acceptance(
                repo_root=repo,
                out_dir=repo / "artifacts/autonomous_runtime/cookies/prompt668",
                run_id="unsafe-path",
            )
        self.assertEqual(result["status"], "blocked")
        self.assertTrue(result["unsafe_paths_rejected"])

    def test_operational_evidence_fields(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
        self.assertTrue(result["durable_state_persisted"])
        self.assertTrue(result["durable_queue_persisted"])
        self.assertTrue(result["lock_acquired"])
        self.assertTrue(result["duplicate_lock_rejected"])
        self.assertTrue(result["per_item_evidence_captured"])
        self.assertTrue(result["implementation_artifact_created"])
        self.assertTrue(result["validation_or_tests_executed"])
        self.assertTrue(result["final_operational_evidence_summary_written"])
        self.assertTrue(result["terminal_state_recorded"])
        self.assertTrue(result["stop_reason_recorded"])
        self.assertTrue(result["remote_actions_blocked"])
        self.assertTrue(result["destructive_actions_blocked"])
        self.assertTrue(result["credential_storage_prevented"])
        self.assertTrue(result["cookie_access_prevented"])
        self.assertTrue(result["browser_profile_access_prevented"])
        self.assertTrue(result["env_value_access_prevented"])


if __name__ == "__main__":
    unittest.main()
