from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from automation.orchestration.planned_runner.operational_scale_up_acceptance import (
    MAX_SCALE_CYCLES,
    MAX_SCALE_ITEMS,
    MAX_SCALE_TICKS,
    build_prompt669_scaled_operational_goal,
    build_prompt669_scaled_queue,
    run_operational_scale_up_acceptance,
    verify_prompt668_baseline,
)
from automation.orchestration.planned_runner.project_level_completion_gate import PROMPT_EVIDENCE
from automation.orchestration.planned_runner.project_level_completion_gate import REQUIRED_SURFACES


REPO_ROOT = Path(__file__).resolve().parents[1]


class OperationalScaleUpAcceptanceTests(unittest.TestCase):
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
        ]:
            subprocess.run(["git", "tag", tag], cwd=repo, check=True)
        return repo

    def _run(self, repo: Path, goal=None):
        return run_operational_scale_up_acceptance(
            repo_root=repo,
            out_dir=repo / "artifacts/autonomous_runtime",
            run_id="prompt669-test",
            scaled_goal=goal,
        )

    def test_prompt668_baseline_verification(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = verify_prompt668_baseline(repo)
        self.assertTrue(result["prompt668_tag_reachable"])
        self.assertTrue(result["prompt668_report_exists"])
        self.assertTrue(result["prompt668_operational_acceptance_artifact_exists"])
        self.assertTrue(result["project_level_autonomy_complete"])

    def test_scaled_queue_generation_requires_exactly_ten_items(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            queue = build_prompt669_scaled_queue(Path(raw), count=10)
            self.assertEqual(len(queue), MAX_SCALE_ITEMS)
            self.assertEqual([item["tick_index"] for item in queue], list(range(1, 11)))
            with self.assertRaises(ValueError):
                build_prompt669_scaled_queue(Path(raw) / "bad", count=9)

    def test_operational_scale_up_run_succeeds_with_ten_items(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
            base = repo / "artifacts/autonomous_runtime/prompt669_operational_scale"
            for name in [
                "operational_scale_goal.json",
                "task_queue.json",
                "run_state.json",
                "evidence_summary.json",
                "scale_marker.json",
            ]:
                self.assertTrue((base / name).is_file())
            queue = json.loads((base / "task_queue.json").read_text(encoding="utf-8"))
            state = json.loads((base / "run_state.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "success", msg=result["errors"])
        self.assertEqual(result["queue_item_count"], 10)
        self.assertEqual(result["tick_count"], 10)
        self.assertEqual(len(queue["items"]), 10)
        self.assertEqual(len(state["completed_ticks"]), 10)
        self.assertEqual(MAX_SCALE_TICKS, 10)
        self.assertLessEqual(MAX_SCALE_CYCLES, 5)

    def test_scaled_operational_goal_is_required_and_unsafe_goal_rejected(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            goal = build_prompt669_scaled_operational_goal(run_id="prompt669-test")
            goal["goal_text"] = "git push origin main"
            result = self._run(repo, goal=goal)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["stop_reason"], "unsafe_scaled_operational_goal")
        self.assertTrue(result["unsafe_scaled_operational_goal_rejected"])

    def test_missing_approval_blocks_scaled_goal(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            goal = build_prompt669_scaled_operational_goal(run_id="prompt669-test")
            goal["approved_for_execution"] = False
            result = self._run(repo, goal=goal)
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result.get("internal_codex_executor_used", False))

    def test_scaled_operational_evidence_fields_and_safety(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
        for field in [
            "safe_scaled_operational_goal_required",
            "safe_scaled_operational_queue_generated_or_loaded",
            "no_human_intervention_during_run_verified",
            "internal_codex_executor_used",
            "internal_executor_safety_gate_verified",
            "durable_state_persisted",
            "durable_queue_persisted",
            "lock_acquired",
            "duplicate_lock_rejected",
            "per_item_evidence_captured",
            "all_10_items_have_evidence",
            "implementation_artifact_created",
            "validation_or_tests_executed",
            "final_scale_evidence_summary_written",
            "terminal_state_recorded",
            "stop_reason_recorded",
            "operator_stop_verified",
            "failure_threshold_stop_verified",
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
            result = run_operational_scale_up_acceptance(
                repo_root=repo,
                out_dir=repo / "artifacts/autonomous_runtime/cookies",
                run_id="unsafe-path",
            )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["stop_reason"], "unsafe_artifact_path")
        self.assertTrue(result["unsafe_paths_rejected"])

    def test_prompt667_and_prompt668_artifacts_are_not_overwritten(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            before = {
                path: (repo / path).read_bytes()
                for path in [
                    "docs/autonomous_runtime/project_level_autonomy_final_audit.md",
                    "artifacts/autonomous_runtime/prompt668_report.json",
                    "artifacts/autonomous_runtime/prompt668_operational_use/operational_use_report.json",
                    "artifacts/autonomous_runtime/prompt668_operational_use/evidence_summary.json",
                ]
            }
            result = self._run(repo)
            after = {path: (repo / path).read_bytes() for path in before}
        self.assertEqual(before, after)
        self.assertTrue(result["prompt667_final_audit_preserved"])
        self.assertTrue(result["prompt668_operational_artifacts_preserved"])


if __name__ == "__main__":
    unittest.main()
