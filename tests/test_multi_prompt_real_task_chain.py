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
from automation.orchestration.planned_runner.multi_prompt_real_task_chain import (
    BOUNDARY_AFTER,
    BOUNDARY_BEFORE,
    RUN_DIR,
    build_real_task_prompt_queue,
    run_multi_prompt_real_task_chain_acceptance,
    verify_prompt679_baseline,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class MultiPromptRealTaskChainTests(unittest.TestCase):
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
            "artifacts/autonomous_runtime/prompt679_no_confirmation_multi_prompt_queue/no_confirmation_queue_marker.json",
        ]
        for path in required:
            source = REPO_ROOT / path
            target = repo / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(["git", "-c", "user.email=t@example.local", "-c", "user.name=T", "commit", "-q", "-m", "fixture"], cwd=repo, check=True)
        subprocess.run(["git", "tag", "prompt677-increase-multi-prompt-queue-length"], cwd=repo, check=True)
        subprocess.run(["git", "tag", "prompt678-codex-no-confirmation-execution-profile"], cwd=repo, check=True)
        subprocess.run(["git", "tag", "prompt679-wire-no-confirmation-profile-into-multi-prompt-queue"], cwd=repo, check=True)
        return repo

    def _run(self, repo: Path, queue=None):
        return run_multi_prompt_real_task_chain_acceptance(
            repo_root=repo,
            out_dir=repo / "artifacts/autonomous_runtime",
            run_id="prompt680-test",
            prompt_queue=queue,
        )

    def test_prompt679_prompt678_prompt677_baseline_verification(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = verify_prompt679_baseline(repo)
        self.assertTrue(result["prompt677_tag_reachable"])
        self.assertTrue(result["prompt677_report_exists"])
        self.assertTrue(result["prompt678_tag_reachable"])
        self.assertTrue(result["prompt678_report_exists"])
        self.assertTrue(result["prompt679_tag_reachable"])
        self.assertTrue(result["prompt679_report_exists"])
        self.assertTrue(result["prompt679_artifacts_exist"])
        self.assertTrue(result["prompt679_boundary_verified"])

    def test_real_task_prompt_queue_schema_validation(self):
        queue = build_real_task_prompt_queue()
        self.assertTrue(queue["preapproved"])
        self.assertEqual(queue["max_prompt_items"], 7)
        self.assertEqual(queue["max_prompt_ticks"], 7)
        self.assertEqual(len(queue["items"]), 7)
        self.assertEqual({item["execution_profile"] for item in queue["items"]}, {NO_CONFIRMATION_PROFILE_NAME})
        self.assertEqual(queue["items"][2]["item_type"], "small_code_change_readiness")
        self.assertEqual(queue["items"][6]["item_type"], "final_chain_summary")

    def test_missing_approval_unsafe_and_free_text_items_are_rejected(self):
        missing = build_prompt_item(item_id="missing", item_type="documentation_followup", goal="safe local", approved=False, execution_profile=NO_CONFIRMATION_PROFILE_NAME)
        unsafe = build_prompt_item(item_id="unsafe", item_type="documentation_followup", goal="git push and read cookies", execution_profile=NO_CONFIRMATION_PROFILE_NAME)
        free_text = build_prompt_item(item_id="free", item_type="free_text", goal="arbitrary", execution_profile=NO_CONFIRMATION_PROFILE_NAME)
        remote = build_prompt_item(item_id="remote", item_type="documentation_followup", goal="safe local", execution_profile=NO_CONFIRMATION_PROFILE_NAME)
        remote["remote"] = True
        remote["destructive"] = True
        remote["requires_credentials"] = True
        self.assertIn("prompt item missing approval", validate_prompt_item(missing))
        self.assertIn("unsafe prompt item rejected", validate_prompt_item(unsafe))
        self.assertIn("arbitrary free-text prompt rejected", validate_prompt_item(free_text))
        self.assertIn("remote action rejected", validate_prompt_item(remote))
        self.assertIn("destructive action rejected", validate_prompt_item(remote))
        self.assertIn("credential access rejected", validate_prompt_item(remote))

    def test_acceptance_runner_processes_all_seven_real_task_items(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
            run_dir = repo / RUN_DIR
            statuses = json.loads((run_dir / "prompt_item_statuses.json").read_text(encoding="utf-8"))["items"]
            evidence_summary = json.loads((run_dir / "evidence_summary.json").read_text(encoding="utf-8"))
            item_evidence = [json.loads(Path(path).read_text(encoding="utf-8")) for path in evidence_summary["evidence_paths"]]
        self.assertEqual(result["status"], "success", msg=result["errors"])
        self.assertEqual(result["current_capability_boundary_before"], BOUNDARY_BEFORE)
        self.assertEqual(result["current_capability_boundary_after"], BOUNDARY_AFTER)
        self.assertEqual(result["prompt_item_count"], 7)
        self.assertEqual(result["prompt_tick_count"], 7)
        self.assertTrue(result["all_prompt_items_use_no_confirmation_profile"])
        self.assertEqual(len(statuses), 7)
        self.assertEqual(len(item_evidence), 7)
        for evidence in item_evidence:
            self.assertEqual(evidence["selected_execution_profile"], NO_CONFIRMATION_PROFILE_NAME)
            self.assertTrue(evidence["no_confirmation_policy_applied"])
            self.assertTrue(evidence["validation_marker"])
            self.assertEqual(evidence["terminal_state"], "completed")

    def test_workspace_cache_policy_retry_summary_and_prompt681_recommendation(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
            run_dir = repo / RUN_DIR
            policy = json.loads((run_dir / "validation_command_policy.json").read_text(encoding="utf-8"))
            retry = json.loads((run_dir / "retry_skip_stop_summary.json").read_text(encoding="utf-8"))
            evidence = json.loads((run_dir / "evidence_summary.json").read_text(encoding="utf-8"))
        self.assertTrue(result["workspace_local_uv_cache_policy_used"])
        self.assertFalse(result["avoidable_confirmation_prompt_trigger_required"])
        for command in policy["normalized_commands"]:
            if "uv run" in command:
                self.assertTrue(command.startswith("UV_CACHE_DIR=.uv-cache "))
        self.assertTrue(retry["retry_policy_verified"])
        self.assertTrue(retry["skip_policy_verified"])
        self.assertTrue(retry["stop_policy_verified"])
        self.assertTrue(retry["controlled_failure_injection_verified"])
        self.assertIn("Prompt681", evidence["next_prompt_recommendation"])
        self.assertTrue(result["prompt681_recommended_for_real_small_code_change_chain"])

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
                "artifacts/autonomous_runtime/prompt677_report.json",
                "artifacts/autonomous_runtime/prompt678_report.json",
                "artifacts/autonomous_runtime/prompt679_report.json",
            ]
            before = {path: (repo / path).read_bytes() for path in protected}
            result = self._run(repo)
            after = {path: (repo / path).read_bytes() for path in protected}
        self.assertEqual(before, after)
        for prompt in ("prompt667", "prompt668", "prompt669", "prompt670", "prompt671", "prompt672", "prompt673", "prompt674", "prompt676", "prompt677", "prompt678", "prompt679"):
            self.assertTrue(result[f"{prompt}_core_artifacts_preserved"], msg=prompt)
        self.assertEqual(result["prompt675_core_artifacts_preserved"], "not_present")


if __name__ == "__main__":
    unittest.main()
