from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from automation.execution.codex_executor_adapter import NO_CONFIRMATION_PROFILE_NAME
from automation.orchestration.planned_runner.multi_prompt_queue_autonomy import (
    build_prompt_item,
    validate_prompt_item,
)
from automation.orchestration.planned_runner.operational_readiness_gap import (
    build_readiness_matrix,
    extract_blocking_gap_ids,
)
from automation.orchestration.planned_runner.real_code_change_chain import (
    CODE_ARTIFACT_PATH,
    RUNNER_ARTIFACT_PATH,
    TEST_ARTIFACT_PATH,
    build_real_code_prompt_queue,
    run_real_code_change_inside_multi_prompt_chain_acceptance,
    verify_prompt681_baseline,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class RealCodeChangeInsideMultiPromptChainTests(unittest.TestCase):
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
            "artifacts/autonomous_runtime/prompt673_report.json",
            "artifacts/autonomous_runtime/prompt674_report.json",
            "artifacts/autonomous_runtime/prompt676_report.json",
            "artifacts/autonomous_runtime/prompt677_report.json",
            "artifacts/autonomous_runtime/prompt678_report.json",
            "artifacts/autonomous_runtime/prompt679_report.json",
            "artifacts/autonomous_runtime/prompt680_report.json",
            "artifacts/autonomous_runtime/prompt681_report.json",
            "artifacts/autonomous_runtime/prompt681_operational_readiness_matrix.json",
            "artifacts/autonomous_runtime/prompt680_multi_prompt_real_task_chain/real_task_chain_marker.json",
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
            "prompt680-multi-prompt-real-task-chain-acceptance",
            "prompt681-operational-readiness-gap-to-real-autonomous-development",
        ]:
            subprocess.run(["git", "tag", tag], cwd=repo, check=True)
        for path in [CODE_ARTIFACT_PATH, RUNNER_ARTIFACT_PATH, TEST_ARTIFACT_PATH]:
            source = REPO_ROOT / path
            target = repo / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        return repo

    def _run(self, repo: Path):
        return run_real_code_change_inside_multi_prompt_chain_acceptance(
            repo_root=repo,
            out_dir=repo / "artifacts/autonomous_runtime",
            run_id="prompt682-test",
        )

    def test_prompt681_and_prompt680_baselines_are_verified(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = verify_prompt681_baseline(repo)
        self.assertTrue(result["prompt681_tag_reachable"])
        self.assertTrue(result["prompt680_tag_reachable"])
        self.assertTrue(result["prompt681_real_code_change_false"])
        self.assertTrue(result["matrix_complete_false"])

    def test_extract_blocking_gap_ids_returns_deterministic_ids(self):
        matrix = {
            "criteria": [
                {"id": "6", "status": "unproven", "missing_proof": "missing"},
                {"id": 4, "status": "partially_proven", "missing_proof": "missing"},
                {"id": 4, "status": "partially_proven", "missing_proof": "duplicate"},
                {"id": 9, "status": "proven", "missing_proof": ""},
                {"id": "bad", "status": "unproven", "missing_proof": "missing"},
                {"id": True, "status": "unproven", "missing_proof": "missing"},
                {"id": 7, "status": "unproven", "missing_proof": ""},
            ]
        }
        self.assertEqual(extract_blocking_gap_ids(matrix), [4, 6])
        self.assertEqual(extract_blocking_gap_ids(build_readiness_matrix(REPO_ROOT)), [4, 5, 6, 14, 16, 17])

    def test_real_code_prompt_queue_has_five_approved_no_confirmation_items(self):
        queue = build_real_code_prompt_queue()
        self.assertEqual(queue["max_prompt_items"], 5)
        self.assertEqual(len(queue["items"]), 5)
        for item in queue["items"]:
            self.assertTrue(item["approved_for_execution"])
            self.assertEqual(item["execution_profile"], NO_CONFIRMATION_PROFILE_NAME)
            self.assertEqual(validate_prompt_item(item), [])

    def test_missing_approval_unsafe_and_free_text_items_are_rejected(self):
        missing_approval = build_prompt_item(
            item_id="missing_approval",
            item_type="small_code_change",
            goal="apply safe local change",
            approved=False,
            execution_profile=NO_CONFIRMATION_PROFILE_NAME,
        )
        unsafe = build_prompt_item(
            item_id="unsafe",
            item_type="small_code_change",
            goal="git push changes",
            execution_profile=NO_CONFIRMATION_PROFILE_NAME,
        )
        free_text = build_prompt_item(
            item_id="free_text",
            item_type="free_text",
            goal="do whatever seems useful",
            execution_profile=NO_CONFIRMATION_PROFILE_NAME,
        )
        self.assertIn("prompt item missing approval", validate_prompt_item(missing_approval))
        self.assertIn("prompt item contains forbidden operation", validate_prompt_item(unsafe))
        self.assertIn("arbitrary free-text prompt type rejected", validate_prompt_item(free_text))

    def test_acceptance_runner_processes_five_items_and_records_real_code_change(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
            run_dir = repo / "artifacts/autonomous_runtime/prompt682_real_code_change_chain"
            evidence = json.loads((run_dir / "evidence_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(result["prompt682_status"], "success")
        self.assertEqual(result["prompt_item_count"], 5)
        self.assertEqual(result["prompt_tick_count"], 5)
        self.assertTrue(result["all_prompt_items_use_no_confirmation_profile"])
        self.assertTrue(result["workspace_local_uv_cache_policy_used"])
        self.assertTrue(result["actual_code_artifact_changed"])
        self.assertTrue(result["test_artifact_created_or_updated"])
        self.assertTrue(result["real_code_change_inside_multi_prompt_chain_proven"])
        self.assertFalse(result["bugfix_from_failing_test_proven_after"])
        self.assertFalse(result["live_codex_execution_proven_after"])
        self.assertFalse(result["release_docs_demo_pack_proven_after"])
        self.assertFalse(result["new_safe_goal_operational_daemon_proven_after"])
        self.assertEqual(len(evidence["evidence_paths"]), 5)

    def test_prior_prompt_artifacts_are_not_overwritten(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            protected = [
                f"artifacts/autonomous_runtime/prompt{n}_report.json"
                for n in [667, 668, 669, 670, 671, 672, 673, 674, 676, 677, 678, 679, 680, 681]
            ]
            before = {path: (repo / path).read_bytes() for path in protected}
            result = self._run(repo)
            after = {path: (repo / path).read_bytes() for path in protected}
        self.assertEqual(before, after)
        for prompt in [
            "prompt667",
            "prompt668",
            "prompt669",
            "prompt670",
            "prompt671",
            "prompt672",
            "prompt673",
            "prompt674",
            "prompt676",
            "prompt677",
            "prompt678",
            "prompt679",
            "prompt680",
            "prompt681",
        ]:
            self.assertTrue(result[f"{prompt}_core_artifacts_preserved"], msg=prompt)
        self.assertEqual(result["prompt675_core_artifacts_preserved"], "not_present")


if __name__ == "__main__":
    unittest.main()
