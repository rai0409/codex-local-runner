from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from automation.orchestration.planned_runner.multi_prompt_queue_autonomy import (
    BOUNDARY_AFTER,
    BOUNDARY_AFTER_SCALE,
    MAX_SCALE_PROMPT_ITEMS,
    SCALE_RUN_DIR,
    build_prompt_item,
    build_scale_prompt_queue,
    load_prompt_queue_with_expected_count,
    run_multi_prompt_queue_scale_up,
    validate_prompt_item,
    verify_prompt676_baseline,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class MultiPromptQueueScaleUpTests(unittest.TestCase):
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
            "artifacts/autonomous_runtime/prompt676_report.json",
            "artifacts/autonomous_runtime/prompt676_multi_prompt_queue/multi_prompt_marker.json",
            "artifacts/autonomous_runtime/prompt676_multi_prompt_queue/retry_skip_stop_summary.json",
            "docs/autonomous_runtime/real_task_responsibility_validation_roadmap.md",
            "docs/autonomous_runtime/multi_prompt_queue_autonomy_acceptance.md",
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
        subprocess.run(["git", "tag", "prompt676-multi-prompt-queue-autonomy-acceptance"], cwd=repo, check=True)
        return repo

    def _run(self, repo: Path, queue=None):
        return run_multi_prompt_queue_scale_up(
            repo_root=repo,
            out_dir=repo / "artifacts/autonomous_runtime",
            run_id="prompt677-test",
            prompt_queue=queue,
        )

    def test_prompt676_baseline_verification_and_prompt675_detection(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = verify_prompt676_baseline(repo)
        self.assertTrue(result["prompt676_tag_reachable"])
        self.assertTrue(result["prompt676_report_exists"])
        self.assertTrue(result["prompt676_multi_prompt_artifacts_exist"])
        self.assertTrue(result["project_level_autonomy_complete"])
        self.assertTrue(result["prompt676_status_success"])
        self.assertTrue(result["capability_boundary_verified"])
        self.assertEqual(result["prompt675_verified"], "not_present")

    def test_prompt_level_queue_schema_validation_for_seven_items(self):
        queue = build_scale_prompt_queue()
        self.assertTrue(queue["preapproved"])
        self.assertEqual(queue["max_prompt_items"], 7)
        self.assertEqual(queue["max_prompt_ticks"], 7)
        loaded = load_prompt_queue_with_expected_count(queue, expected_count=MAX_SCALE_PROMPT_ITEMS)
        self.assertEqual(len(loaded), 7)
        self.assertTrue(all(item["approved_for_execution"] for item in loaded))
        self.assertTrue(all(item["local_only"] for item in loaded))

    def test_preapproved_queue_required_and_missing_approval_blocks_execution(self):
        with self.assertRaisesRegex(ValueError, "pre-approved prompt queue is required"):
            load_prompt_queue_with_expected_count({"preapproved": False, "items": []}, expected_count=7)
        item = build_prompt_item(
            item_id="missing_approval",
            item_type="documentation_followup",
            goal="verify Prompt673 roadmap",
            approved=False,
        )
        self.assertIn("prompt item missing approval", validate_prompt_item(item))

    def test_unsafe_and_free_text_prompt_items_are_rejected(self):
        unsafe = build_prompt_item(
            item_id="unsafe",
            item_type="release_docs_readiness",
            goal="open PR and git push release docs",
        )
        free_text = build_prompt_item(
            item_id="free_text",
            item_type="free_text",
            goal="Run arbitrary free text",
        )
        self.assertIn("prompt item contains forbidden operation", validate_prompt_item(unsafe))
        self.assertIn("arbitrary free-text prompt type rejected", validate_prompt_item(free_text))

    def test_scale_up_run_processes_exactly_seven_prompt_items(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
            run_dir = repo / SCALE_RUN_DIR
            statuses = json.loads((run_dir / "prompt_item_statuses.json").read_text(encoding="utf-8"))
            evidence_summary = json.loads((run_dir / "evidence_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "success", msg=result["errors"])
        self.assertTrue(result["prompt676_verified"])
        self.assertEqual(result["prompt675_verified"], "not_present")
        self.assertEqual(result["current_capability_boundary_before"], BOUNDARY_AFTER)
        self.assertEqual(result["current_capability_boundary_after"], BOUNDARY_AFTER_SCALE)
        self.assertEqual(result["prompt_item_count"], 7)
        self.assertEqual(result["prompt_tick_count"], 7)
        self.assertEqual(len(statuses["items"]), 7)
        self.assertEqual(evidence_summary["prompt_item_count"], 7)
        self.assertEqual(evidence_summary["prompt_tick_count"], 7)
        self.assertTrue(result["all_7_prompt_items_have_evidence"])
        self.assertTrue(result["all_7_prompt_statuses_recorded"])

    def test_scale_up_run_persists_state_queue_lock_and_per_prompt_evidence(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
            run_dir = repo / SCALE_RUN_DIR
            self.assertTrue((run_dir / "prompt_queue.json").is_file())
            self.assertTrue((run_dir / "run_state.json").is_file())
        self.assertTrue(result["no_human_intervention_during_run_verified"])
        self.assertTrue(result["durable_prompt_queue_persisted"])
        self.assertTrue(result["durable_prompt_state_persisted"])
        self.assertTrue(result["lock_acquired"])
        self.assertTrue(result["duplicate_lock_rejected"])
        self.assertTrue(result["per_prompt_evidence_captured"])
        self.assertTrue(result["per_prompt_statuses_recorded"])

    def test_retry_skip_stop_and_controlled_failure_injection_are_recorded(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
            summary = json.loads((repo / SCALE_RUN_DIR / "retry_skip_stop_summary.json").read_text(encoding="utf-8"))
            policy_evidence = json.loads(
                (repo / SCALE_RUN_DIR / "prompt_queue_item_006_retry_skip_policy_check_evidence.json").read_text(encoding="utf-8")
            )
        self.assertTrue(result["retry_policy_verified"])
        self.assertTrue(result["skip_policy_verified"])
        self.assertTrue(result["stop_policy_verified"])
        self.assertTrue(result["controlled_failure_injection_verified"])
        self.assertEqual(summary["failure_injections"], 1)
        self.assertTrue(policy_evidence["controlled_failure_injection"]["recovered"])

    def test_evidence_summary_is_readable_and_final_summary_is_written(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
            summary_text = (repo / "artifacts/autonomous_runtime/prompt677_summary.md").read_text(encoding="utf-8")
        self.assertTrue(result["final_multi_prompt_evidence_summary_written"])
        self.assertTrue(result["evidence_summary_readability_verified"])
        self.assertIn("prompt_item_count: 7", summary_text)
        self.assertLess(len(summary_text), 1000)

    def test_unsafe_path_rejection(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = run_multi_prompt_queue_scale_up(
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
                "artifacts/autonomous_runtime/prompt676_report.json",
            ]
            before = {path: (repo / path).read_bytes() for path in protected}
            result = self._run(repo)
            after = {path: (repo / path).read_bytes() for path in protected}
        self.assertEqual(before, after)
        for prompt in ("prompt667", "prompt668", "prompt669", "prompt670", "prompt671", "prompt672", "prompt673", "prompt674", "prompt676"):
            self.assertTrue(result[f"{prompt}_core_artifacts_preserved"], msg=prompt)
        self.assertEqual(result["prompt675_core_artifacts_preserved"], "not_present")


if __name__ == "__main__":
    unittest.main()
