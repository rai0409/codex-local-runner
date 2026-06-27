from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from automation.orchestration.planned_runner.operational_soak_recovery_acceptance import (
    DEFAULT_SOAK_ITEMS,
    MAX_RETRY_ATTEMPTS_PER_ITEM,
    MAX_SOAK_CYCLES,
    MAX_SOAK_ITEMS,
    MAX_SOAK_TICKS,
    MIN_SOAK_ITEMS,
    build_prompt670_soak_goal,
    build_prompt670_soak_queue,
    run_operational_soak_recovery_acceptance,
    verify_prompt669_baseline,
)
from automation.orchestration.planned_runner.project_level_completion_gate import (
    PROMPT_EVIDENCE,
    REQUIRED_SURFACES,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class OperationalSoakRecoveryAcceptanceTests(unittest.TestCase):
    def _copy_repo(self, tmp: Path) -> Path:
        repo = tmp / "repo"
        repo.mkdir()
        for spec in PROMPT_EVIDENCE.values():
            source = REPO_ROOT / spec["report"]
            target = repo / spec["report"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        for extra in [
            "artifacts/autonomous_runtime/prompt667_report.json",
            "artifacts/autonomous_runtime/prompt667_final_project_run/final_project_run_report.json",
            "artifacts/autonomous_runtime/prompt668_report.json",
            "artifacts/autonomous_runtime/prompt668_operational_use/operational_use_report.json",
            "artifacts/autonomous_runtime/prompt668_operational_use/evidence_summary.json",
            "artifacts/autonomous_runtime/prompt669_report.json",
            "artifacts/autonomous_runtime/prompt669_operational_scale/operational_scale_goal.json",
            "artifacts/autonomous_runtime/prompt669_operational_scale/evidence_summary.json",
            "docs/autonomous_runtime/project_level_autonomy_final_audit.md",
            *REQUIRED_SURFACES,
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
        for spec in PROMPT_EVIDENCE.values():
            subprocess.run(["git", "tag", spec["tag"]], cwd=repo, check=True)
        for tag in [
            "prompt667-end-to-end-unattended-project-run-acceptance",
            "prompt668-operational-use-acceptance",
            "prompt669-increase-operational-run-scale",
        ]:
            subprocess.run(["git", "tag", tag], cwd=repo, check=True)
        return repo

    def _run(self, repo: Path, goal=None):
        return run_operational_soak_recovery_acceptance(
            repo_root=repo,
            out_dir=repo / "artifacts/autonomous_runtime",
            run_id="prompt670-test",
            soak_goal=goal,
        )

    def test_prompt669_baseline_verification(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = verify_prompt669_baseline(repo)
        self.assertTrue(result["prompt669_tag_reachable"])
        self.assertTrue(result["prompt669_report_exists"])
        self.assertTrue(result["prompt669_operational_scale_artifact_exists"])
        self.assertTrue(result["project_level_autonomy_complete"])
        self.assertTrue(result["operational_scale_up_implemented"])

    def test_soak_queue_generation_between_20_and_30(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            queue = build_prompt670_soak_queue(Path(raw), count=DEFAULT_SOAK_ITEMS)
            self.assertGreaterEqual(len(queue), MIN_SOAK_ITEMS)
            self.assertLessEqual(len(queue), MAX_SOAK_ITEMS)
            self.assertEqual(queue[7]["policy"], "retry_once")
            self.assertEqual(queue[9]["policy"], "skip")
            with self.assertRaises(ValueError):
                build_prompt670_soak_queue(Path(raw) / "bad", count=19)
            with self.assertRaises(ValueError):
                build_prompt670_soak_queue(Path(raw) / "bad2", count=31)

    def test_operational_soak_run_succeeds_with_recovery_evidence(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
            base = repo / "artifacts/autonomous_runtime/prompt670_operational_soak"
            for name in [
                "operational_soak_goal.json",
                "task_queue.json",
                "run_state.json",
                "evidence_summary.json",
                "recovery_summary.json",
                "failure_policy_summary.json",
                "soak_marker.json",
            ]:
                self.assertTrue((base / name).is_file(), msg=name)
            queue = json.loads((base / "task_queue.json").read_text(encoding="utf-8"))
            state = json.loads((base / "run_state.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "success", msg=result["errors"])
        self.assertGreaterEqual(result["queue_item_count"], 20)
        self.assertLessEqual(result["queue_item_count"], 30)
        self.assertGreaterEqual(result["tick_count"], 20)
        self.assertLessEqual(result["tick_count"], 30)
        self.assertEqual(len(queue["items"]), DEFAULT_SOAK_ITEMS)
        self.assertEqual(len(state["completed_ticks"]), DEFAULT_SOAK_ITEMS)
        self.assertLessEqual(MAX_SOAK_TICKS, 30)
        self.assertLessEqual(MAX_SOAK_CYCLES, 8)
        self.assertLessEqual(MAX_RETRY_ATTEMPTS_PER_ITEM, 2)

    def test_safe_goal_required_and_unsafe_goal_rejected(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            goal = build_prompt670_soak_goal(run_id="prompt670-test")
            goal["goal_text"] = "git push origin main"
            result = self._run(repo, goal=goal)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["stop_reason"], "unsafe_soak_operational_goal")
        self.assertTrue(result["unsafe_soak_operational_goal_rejected"])

    def test_missing_approval_blocks_soak_goal(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            goal = build_prompt670_soak_goal(run_id="prompt670-test")
            goal["approved_for_execution"] = False
            result = self._run(repo, goal=goal)
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result.get("internal_codex_executor_used", False))

    def test_soak_recovery_evidence_fields_and_safety(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
        for field in [
            "safe_soak_operational_goal_required",
            "safe_soak_operational_queue_generated_or_loaded",
            "no_human_intervention_during_run_verified",
            "internal_codex_executor_used",
            "internal_executor_safety_gate_verified",
            "durable_state_persisted",
            "durable_queue_persisted",
            "lock_acquired",
            "duplicate_lock_rejected",
            "stale_lock_handling_verified",
            "controlled_interruption_verified",
            "resume_after_interruption_verified",
            "operator_stop_verified",
            "retryable_failure_injection_verified",
            "retry_policy_verified",
            "skip_or_stop_policy_verified",
            "failure_threshold_stop_verified",
            "state_queue_consistency_verified",
            "per_item_evidence_captured",
            "all_processed_items_have_evidence",
            "final_readable_soak_evidence_summary_written",
            "terminal_state_recorded",
            "stop_reason_recorded",
            "operational_gate_or_completion_gate_verified",
            "local_only_evidence_captured",
            "unsafe_paths_rejected",
            "remote_actions_blocked",
            "destructive_actions_blocked",
            "credential_storage_prevented",
            "browser_profile_access_prevented",
            "cookie_access_prevented",
            "env_value_access_prevented",
        ]:
            self.assertTrue(result[field], msg=field)

    def test_unsafe_path_rejection(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = run_operational_soak_recovery_acceptance(
                repo_root=repo,
                out_dir=repo / "artifacts/autonomous_runtime/cookies",
                run_id="unsafe-path",
            )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["stop_reason"], "unsafe_artifact_path")
        self.assertTrue(result["unsafe_paths_rejected"])

    def test_prompt667_prompt668_and_prompt669_artifacts_are_not_overwritten(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            protected = [
                "docs/autonomous_runtime/project_level_autonomy_final_audit.md",
                "artifacts/autonomous_runtime/prompt668_report.json",
                "artifacts/autonomous_runtime/prompt668_operational_use/operational_use_report.json",
                "artifacts/autonomous_runtime/prompt668_operational_use/evidence_summary.json",
                "artifacts/autonomous_runtime/prompt669_report.json",
                "artifacts/autonomous_runtime/prompt669_operational_scale/operational_scale_goal.json",
                "artifacts/autonomous_runtime/prompt669_operational_scale/evidence_summary.json",
            ]
            before = {path: (repo / path).read_bytes() for path in protected}
            result = self._run(repo)
            after = {path: (repo / path).read_bytes() for path in protected}
        self.assertEqual(before, after)
        self.assertTrue(result["prompt667_final_audit_preserved"])
        self.assertTrue(result["prompt668_operational_artifacts_preserved"])
        self.assertTrue(result["prompt669_scale_up_artifacts_preserved"])


if __name__ == "__main__":
    unittest.main()
