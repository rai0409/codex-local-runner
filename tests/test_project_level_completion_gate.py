from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from automation.orchestration.planned_runner.project_level_completion_gate import (
    FINAL_E2E_CRITERION,
    PROMPT_EVIDENCE,
    run_project_level_completion_gate,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class ProjectLevelCompletionGateTests(unittest.TestCase):
    def _copy_fixture_repo(self, tmp: Path) -> Path:
        repo = tmp / "repo"
        repo.mkdir()
        (repo / "artifacts" / "autonomous_runtime").mkdir(parents=True)
        for spec in PROMPT_EVIDENCE.values():
            source = REPO_ROOT / spec["report"]
            target = repo / spec["report"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
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
            target = repo / surface
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# surface fixture\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.email=prompt666@example.local",
                "-c",
                "user.name=Prompt666",
                "commit",
                "-q",
                "-m",
                "fixture evidence",
            ],
            cwd=repo,
            check=True,
        )
        for spec in PROMPT_EVIDENCE.values():
            subprocess.run(["git", "tag", spec["tag"]], cwd=repo, check=True)
        return repo

    def _run_gate(self, repo: Path):
        return run_project_level_completion_gate(
            repo_root=repo,
            out_dir=repo / "artifacts" / "autonomous_runtime" / "prompt666_gate",
        )

    def test_completion_gate_loads_prompt660c_through_prompt665_evidence(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_fixture_repo(Path(raw))
            result = self._run_gate(repo)
        self.assertTrue(result["readiness_for_prompt667"], msg=result["pre_final_missing_criteria"])
        self.assertFalse(result["project_level_autonomy_complete"])
        self.assertIn(FINAL_E2E_CRITERION, result["missing_completion_criteria"])
        self.assertEqual(len(result["evidence_files_checked"]), 6)

    def test_missing_report_fails_readiness(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_fixture_repo(Path(raw))
            (repo / PROMPT_EVIDENCE["prompt665"]["report"]).unlink()
            result = self._run_gate(repo)
        self.assertFalse(result["readiness_for_prompt667"])
        self.assertTrue(any("prompt665:report" in item for item in result["missing_completion_criteria"]))

    def test_missing_tag_fails_readiness(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_fixture_repo(Path(raw))
            subprocess.run(
                ["git", "tag", "-d", PROMPT_EVIDENCE["prompt665"]["tag"]],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            )
            result = self._run_gate(repo)
        self.assertFalse(result["readiness_for_prompt667"])
        self.assertTrue(any("tag_missing" in item for item in result["missing_completion_criteria"]))

    def test_missing_safety_field_fails_readiness(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_fixture_repo(Path(raw))
            path = repo / PROMPT_EVIDENCE["prompt665"]["report"]
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["remote_actions_blocked"] = False
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = self._run_gate(repo)
        self.assertFalse(result["readiness_for_prompt667"])
        self.assertFalse(result["safety_invariants_verified"])
        self.assertTrue(any("remote_actions_blocked" in item for item in result["missing_completion_criteria"]))

    def test_missing_unattended_field_fails_readiness(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_fixture_repo(Path(raw))
            path = repo / PROMPT_EVIDENCE["prompt665"]["report"]
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["no_human_intervention_during_run_verified"] = False
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = self._run_gate(repo)
        self.assertFalse(result["readiness_for_prompt667"])
        self.assertFalse(result["unattended_invariants_verified"])

    def test_missing_daemon_field_fails_readiness(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_fixture_repo(Path(raw))
            path = repo / PROMPT_EVIDENCE["prompt663"]["report"]
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["stale_lock_handling_verified"] = False
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = self._run_gate(repo)
        self.assertFalse(result["readiness_for_prompt667"])
        self.assertFalse(result["daemon_invariants_verified"])

    def test_missing_internal_executor_usage_fails_readiness(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_fixture_repo(Path(raw))
            path = repo / PROMPT_EVIDENCE["prompt662"]["report"]
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["internal_codex_executor_used"] = False
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = self._run_gate(repo)
        self.assertFalse(result["readiness_for_prompt667"])
        self.assertFalse(result["internal_executor_invariants_verified"])

    def test_fake_project_level_complete_is_rejected_without_final_e2e(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_fixture_repo(Path(raw))
            path = repo / PROMPT_EVIDENCE["prompt665"]["report"]
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["project_level_autonomy_complete"] = True
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = self._run_gate(repo)
        self.assertFalse(result["readiness_for_prompt667"])
        self.assertTrue(result["fake_completion_rejected"])
        self.assertTrue(any("fake_project_level_autonomy_complete" in item for item in result["missing_completion_criteria"]))

    def test_reports_and_summary_are_written(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_fixture_repo(Path(raw))
            out = repo / "artifacts" / "autonomous_runtime" / "prompt666_gate"
            result = run_project_level_completion_gate(repo_root=repo, out_dir=out)
            self.assertTrue((out / "project_level_completion_gate_report.json").is_file())
            self.assertTrue((out / "project_level_completion_gate_summary.md").is_file())
            self.assertTrue(result["browser_to_codex_invariants_verified"])
            self.assertTrue(result["safety_invariants_verified"])

    def test_final_e2e_report_completes_project_level_gate(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_fixture_repo(Path(raw))
            final_path = repo / "artifacts" / "autonomous_runtime" / "prompt667" / "final.json"
            final_path.parent.mkdir(parents=True, exist_ok=True)
            final_payload = {field: True for field in [
                "final_e2e_acceptance_implemented",
                "safe_project_goal_required",
                "unsafe_project_goal_rejected",
                "safe_task_queue_generated_or_loaded",
                "approval_gate_verified",
                "missing_approval_blocks_execution",
                "no_human_intervention_during_run_verified",
                "lock_acquired",
                "duplicate_lock_rejected",
                "durable_state_persisted",
                "durable_queue_persisted",
                "per_item_or_step_evidence_captured",
                "internal_codex_executor_used",
                "internal_executor_safety_gate_verified",
                "implementation_artifact_created",
                "validation_or_tests_executed",
                "final_evidence_summary_written",
                "terminal_state_recorded",
                "stop_reason_recorded",
                "local_only_evidence_captured",
                "unsafe_paths_rejected",
                "remote_actions_blocked",
                "destructive_actions_blocked",
                "credential_storage_prevented",
                "browser_profile_access_prevented",
                "cookie_access_prevented",
                "env_value_access_prevented",
                "final_project_level_audit_written",
            ]}
            final_payload["queue_item_count"] = 3
            final_payload["project_level_autonomy_complete"] = True
            final_path.write_text(json.dumps(final_payload), encoding="utf-8")
            result = run_project_level_completion_gate(
                repo_root=repo,
                out_dir=repo / "artifacts" / "autonomous_runtime" / "prompt666_gate",
                final_e2e_report_path=final_path,
            )
        self.assertTrue(result["readiness_for_prompt667"])
        self.assertTrue(result["final_e2e_verified"])
        self.assertTrue(result["project_level_autonomy_complete"])
        self.assertEqual(result["missing_completion_criteria"], [])


if __name__ == "__main__":
    unittest.main()
