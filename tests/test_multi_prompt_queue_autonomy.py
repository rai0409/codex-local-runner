from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from automation.orchestration.planned_runner.multi_prompt_queue_autonomy import (
    BOUNDARY_BEFORE_PROMPT674,
    RUN_DIR,
    build_default_prompt_queue,
    build_prompt_item,
    load_prompt_queue,
    run_multi_prompt_queue_autonomy,
    validate_prompt_item,
    verify_current_baseline,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class MultiPromptQueueAutonomyTests(unittest.TestCase):
    def _copy_repo(self, tmp: Path) -> Path:
        repo = tmp / "repo"
        repo.mkdir()
        required = [
            "artifacts/autonomous_runtime/prompt667_report.json",
            "artifacts/autonomous_runtime/prompt668_report.json",
            "artifacts/autonomous_runtime/prompt669_report.json",
            "artifacts/autonomous_runtime/prompt670_report.json",
            "artifacts/autonomous_runtime/prompt671_report.json",
            "artifacts/autonomous_runtime/prompt672_report.json",
            "artifacts/autonomous_runtime/prompt672_responsibility_matrix.json",
            "artifacts/autonomous_runtime/prompt673_report.json",
            "artifacts/autonomous_runtime/prompt674_report.json",
            "docs/autonomous_runtime/responsibility_scope_matrix.md",
            "docs/autonomous_runtime/real_task_responsibility_validation_roadmap.md",
            "docs/autonomous_runtime/real_task_test_addition_acceptance.md",
            "tests/test_real_task_test_addition_acceptance.py",
        ]
        for path in required:
            source = REPO_ROOT / path
            target = repo / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@example.local", "-c", "user.name=T", "commit", "-q", "-m", "fixture"],
            cwd=repo,
            check=True,
        )
        for tag in [
            "prompt674-real-task-test-addition-acceptance",
        ]:
            subprocess.run(["git", "tag", tag], cwd=repo, check=True)
        return repo

    def _run(self, repo: Path, queue=None):
        return run_multi_prompt_queue_autonomy(
            repo_root=repo,
            out_dir=repo / "artifacts/autonomous_runtime",
            run_id="prompt676-test",
            prompt_queue=queue,
        )

    def test_baseline_verification(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = verify_current_baseline(repo)
        self.assertTrue(result["prompt674_tag_reachable"])
        self.assertTrue(result["prompt674_report_exists"])
        self.assertTrue(result["project_level_autonomy_complete"])
        self.assertTrue(result["prompt674_status_success"])
        self.assertTrue(result["capability_boundary_verified"])
        self.assertEqual(result["prompt675_verified"], "not_present")

    def test_prompt_level_queue_schema_validation(self):
        queue = build_default_prompt_queue()
        self.assertEqual(len(queue["items"]), 3)
        loaded = load_prompt_queue(queue)
        self.assertEqual(len(loaded), 3)
        self.assertTrue(all(item["approved_for_execution"] for item in loaded))
        self.assertTrue(all(item["local_only"] for item in loaded))

    def test_preapproved_queue_required_and_missing_approval_blocks(self):
        item = build_prompt_item(
            item_id="missing_approval",
            item_type="documentation_followup",
            goal="verify Prompt673 roadmap",
            approved=False,
        )
        errors = validate_prompt_item(item)
        self.assertIn("prompt item missing approval", errors)

    def test_unsafe_and_arbitrary_free_text_prompt_items_are_rejected(self):
        unsafe = build_prompt_item(
            item_id="unsafe",
            item_type="documentation_followup",
            goal="git push origin main",
        )
        arbitrary = build_prompt_item(
            item_id="arbitrary",
            item_type="free_text",
            goal="Do anything you want",
        )
        self.assertIn("prompt item contains forbidden operation", validate_prompt_item(unsafe))
        self.assertIn("arbitrary free-text prompt type rejected", validate_prompt_item(arbitrary))

    def test_multi_prompt_run_processes_exactly_three_items_and_records_evidence(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
            run_dir = repo / RUN_DIR
            statuses = json.loads((run_dir / "prompt_item_statuses.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "success", msg=result["errors"])
        self.assertEqual(result["current_capability_boundary_before"], BOUNDARY_BEFORE_PROMPT674)
        self.assertEqual(result["prompt_item_count"], 3)
        self.assertEqual(result["prompt_tick_count"], 3)
        self.assertTrue(result["no_human_intervention_during_run_verified"])
        self.assertTrue(result["durable_prompt_queue_persisted"])
        self.assertTrue(result["durable_prompt_state_persisted"])
        self.assertTrue(result["lock_acquired"])
        self.assertTrue(result["duplicate_lock_rejected"])
        self.assertTrue(result["per_prompt_evidence_captured"])
        self.assertTrue(result["per_prompt_statuses_recorded"])
        self.assertEqual(len(statuses["items"]), 3)

    def test_retry_skip_stop_policy_and_summary_are_written(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
            summary = json.loads((repo / RUN_DIR / "retry_skip_stop_summary.json").read_text(encoding="utf-8"))
        self.assertTrue(result["retry_policy_verified"])
        self.assertTrue(result["skip_policy_verified"])
        self.assertTrue(result["stop_policy_verified"])
        self.assertTrue(result["final_multi_prompt_evidence_summary_written"])
        self.assertEqual(summary["max_retries_per_prompt"], 1)

    def test_unsafe_path_rejection(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = run_multi_prompt_queue_autonomy(
                repo_root=repo,
                out_dir=repo / "artifacts/autonomous_runtime/cookies",
                run_id="unsafe-path",
            )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["stop_reason"], "unsafe_artifact_path")
        self.assertTrue(result["unsafe_paths_rejected"])

    def test_prior_core_artifacts_are_not_overwritten(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            protected = [
                "artifacts/autonomous_runtime/prompt667_report.json",
                "artifacts/autonomous_runtime/prompt668_report.json",
                "artifacts/autonomous_runtime/prompt669_report.json",
                "artifacts/autonomous_runtime/prompt670_report.json",
                "artifacts/autonomous_runtime/prompt671_report.json",
                "artifacts/autonomous_runtime/prompt672_report.json",
                "artifacts/autonomous_runtime/prompt673_report.json",
                "artifacts/autonomous_runtime/prompt674_report.json",
            ]
            before = {path: (repo / path).read_bytes() for path in protected}
            result = self._run(repo)
            after = {path: (repo / path).read_bytes() for path in protected}
        self.assertEqual(before, after)
        for prompt in ("prompt667", "prompt668", "prompt669", "prompt670", "prompt671", "prompt672", "prompt673", "prompt674"):
            self.assertTrue(result[f"{prompt}_core_artifacts_preserved"], msg=prompt)
        self.assertEqual(result["prompt675_core_artifacts_preserved"], "not_present")


if __name__ == "__main__":
    unittest.main()
