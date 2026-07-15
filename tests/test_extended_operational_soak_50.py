from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from automation.orchestration.planned_runner.extended_operational_soak_50 import (
    DEFAULT_EXTENDED_ITEMS,
    MAX_EXTENDED_CYCLES,
    MAX_EXTENDED_ITEMS,
    MAX_EXTENDED_TICKS,
    MIN_EXTENDED_ITEMS,
    build_prompt671_extended_goal,
    build_prompt671_extended_queue,
    run_extended_operational_soak_50,
    verify_prompt670_baseline,
)
from automation.orchestration.planned_runner.project_level_completion_gate import (
    PROMPT_EVIDENCE,
    REQUIRED_SURFACES,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class ExtendedOperationalSoak50Tests(unittest.TestCase):
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
            "artifacts/autonomous_runtime/prompt670_report.json",
            "artifacts/autonomous_runtime/prompt670_operational_soak/operational_soak_goal.json",
            "artifacts/autonomous_runtime/prompt670_operational_soak/evidence_summary.json",
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
            "prompt670-operational-soak-and-recovery-testing",
        ]:
            subprocess.run(["git", "tag", tag], cwd=repo, check=True)
        return repo

    def _run(self, repo: Path, goal=None):
        return run_extended_operational_soak_50(
            repo_root=repo,
            out_dir=repo / "artifacts/autonomous_runtime",
            run_id="prompt671-test",
            extended_goal=goal,
        )

    def test_prompt670_baseline_verification(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = verify_prompt670_baseline(repo)
        self.assertTrue(result["prompt670_tag_reachable"])
        self.assertTrue(result["prompt670_report_exists"])
        self.assertTrue(result["prompt670_soak_artifact_exists"])
        self.assertTrue(result["project_level_autonomy_complete"])

    def test_extended_queue_generation_between_45_and_50(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            queue = build_prompt671_extended_queue(Path(raw), count=DEFAULT_EXTENDED_ITEMS)
            self.assertEqual(len(queue), 50)
            self.assertEqual(queue[11]["policy"], "retry_once")
            self.assertEqual(queue[36]["policy"], "retry_once")
            self.assertEqual(queue[24]["policy"], "skip")
            with self.assertRaises(ValueError):
                build_prompt671_extended_queue(Path(raw) / "bad", count=44)
            with self.assertRaises(ValueError):
                build_prompt671_extended_queue(Path(raw) / "bad2", count=51)

    def test_extended_soak_run_succeeds(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
        self.assertEqual(result["status"], "success", msg=result["errors"])
        self.assertGreaterEqual(result["queue_item_count"], MIN_EXTENDED_ITEMS)
        self.assertLessEqual(result["queue_item_count"], MAX_EXTENDED_ITEMS)
        self.assertGreaterEqual(result["tick_count"], MIN_EXTENDED_ITEMS)
        self.assertLessEqual(result["tick_count"], MAX_EXTENDED_TICKS)
        self.assertLessEqual(MAX_EXTENDED_CYCLES, 10)

    def test_safe_goal_required_and_unsafe_goal_rejected(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            goal = build_prompt671_extended_goal(run_id="prompt671-test")
            goal["goal_text"] = "git push origin main"
            result = self._run(repo, goal=goal)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["stop_reason"], "unsafe_extended_soak_goal")

    def test_extended_soak_evidence_fields_and_safety(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
        for field in [
            "no_human_intervention_during_run_verified",
            "internal_codex_executor_used",
            "internal_executor_safety_gate_verified",
            "durable_state_persisted",
            "durable_queue_persisted",
            "lock_acquired",
            "duplicate_lock_rejected",
            "stale_lock_handling_verified",
            "resume_after_interruption_verified",
            "operator_stop_verified",
            "retry_policy_verified",
            "skip_or_stop_policy_verified",
            "failure_threshold_stop_verified",
            "state_queue_consistency_verified",
            "per_item_evidence_captured",
            "all_processed_items_have_evidence",
            "final_readable_soak_evidence_summary_written",
            "evidence_summary_readability_verified",
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
        self.assertGreaterEqual(result["controlled_interruption_count"], 2)
        self.assertGreaterEqual(result["retryable_failure_injection_count"], 2)

    def test_unsafe_path_rejection(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = run_extended_operational_soak_50(
                repo_root=repo,
                out_dir=repo / "artifacts/autonomous_runtime/cookies",
                run_id="unsafe-path",
            )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["stop_reason"], "unsafe_artifact_path")
        self.assertTrue(result["unsafe_paths_rejected"])

    def test_prior_artifacts_are_not_overwritten(self):
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
                "artifacts/autonomous_runtime/prompt670_report.json",
                "artifacts/autonomous_runtime/prompt670_operational_soak/operational_soak_goal.json",
                "artifacts/autonomous_runtime/prompt670_operational_soak/evidence_summary.json",
            ]
            before = {path: (repo / path).read_bytes() for path in protected}
            result = self._run(repo)
            after = {path: (repo / path).read_bytes() for path in protected}
        self.assertEqual(before, after)
        self.assertTrue(result["prompt667_final_audit_preserved"])
        self.assertTrue(result["prompt668_operational_artifacts_preserved"])
        self.assertTrue(result["prompt669_scale_up_artifacts_preserved"])
        self.assertTrue(result["prompt670_soak_artifacts_preserved"])


if __name__ == "__main__":
    unittest.main()
