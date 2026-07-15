from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from automation.execution.codex_executor_adapter import (
    NO_CONFIRMATION_PROFILE_NAME,
    normalize_validation_command_for_workspace_cache,
    validate_workspace_local_uv_cache_policy,
)
from automation.orchestration.planned_runner.no_confirmation_multi_prompt_queue import (
    BOUNDARY_AFTER,
    BOUNDARY_BEFORE,
    RUN_DIR,
    build_no_confirmation_prompt_queue,
    build_validation_command_policy,
    run_no_confirmation_multi_prompt_queue_acceptance,
    verify_prompt678_baseline,
)
from automation.orchestration.planned_runner.multi_prompt_queue_autonomy import (
    build_prompt_item,
    validate_prompt_item,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class NoConfirmationMultiPromptQueueTests(unittest.TestCase):
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
        subprocess.run(["git", "tag", "prompt677-increase-multi-prompt-queue-length"], cwd=repo, check=True)
        subprocess.run(["git", "tag", "prompt678-codex-no-confirmation-execution-profile"], cwd=repo, check=True)
        return repo

    def _run(self, repo: Path, queue=None):
        return run_no_confirmation_multi_prompt_queue_acceptance(
            repo_root=repo,
            out_dir=repo / "artifacts/autonomous_runtime",
            run_id="prompt679-test",
            prompt_queue=queue,
        )

    def test_prompt678_and_prompt677_baseline_verification(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = verify_prompt678_baseline(repo)
        self.assertTrue(result["prompt677_tag_reachable"])
        self.assertTrue(result["prompt677_report_exists"])
        self.assertTrue(result["prompt677_status_success"])
        self.assertTrue(result["prompt678_tag_reachable"])
        self.assertTrue(result["prompt678_report_exists"])
        self.assertTrue(result["prompt678_status_success"])
        self.assertTrue(result["prompt678_boundary_verified"])

    def test_safe_preapproved_items_select_no_confirmation_profile(self):
        queue = build_no_confirmation_prompt_queue()
        self.assertEqual(len(queue["items"]), 3)
        for item in queue["items"]:
            self.assertEqual(item["execution_profile"], NO_CONFIRMATION_PROFILE_NAME)
            self.assertEqual(validate_prompt_item(item), [])

    def test_no_confirmation_profile_rejected_without_approval(self):
        item = build_prompt_item(
            item_id="missing_approval",
            item_type="documentation_followup",
            goal="safe local check",
            approved=False,
            execution_profile=NO_CONFIRMATION_PROFILE_NAME,
        )
        errors = validate_prompt_item(item)
        self.assertIn("prompt item missing approval", errors)
        self.assertIn("preapproval required", errors)

    def test_no_confirmation_profile_rejects_unsafe_and_free_text_items(self):
        unsafe = build_prompt_item(
            item_id="unsafe",
            item_type="documentation_followup",
            goal="git push and read private session",
            execution_profile=NO_CONFIRMATION_PROFILE_NAME,
        )
        free_text = build_prompt_item(
            item_id="free_text",
            item_type="free_text",
            goal="arbitrary request",
            execution_profile=NO_CONFIRMATION_PROFILE_NAME,
        )
        self.assertIn("unsafe prompt item rejected", validate_prompt_item(unsafe))
        self.assertIn("arbitrary free-text prompt rejected", validate_prompt_item(free_text))

    def test_no_confirmation_profile_rejects_remote_destructive_secret_items(self):
        item = build_prompt_item(
            item_id="remote",
            item_type="documentation_followup",
            goal="safe local check",
            execution_profile=NO_CONFIRMATION_PROFILE_NAME,
        )
        item["remote"] = True
        item["destructive"] = True
        item["requires_credentials"] = True
        errors = validate_prompt_item(item)
        self.assertIn("remote action rejected", errors)
        self.assertIn("destructive action rejected", errors)
        self.assertIn("credential access rejected", errors)

    def test_validation_command_policy_rewrites_workspace_local_uv_cache(self):
        command = "PYTHONPATH=. uv run pytest tests/test_no_confirmation_multi_prompt_queue.py -q"
        rewritten = normalize_validation_command_for_workspace_cache(command)
        self.assertTrue(rewritten.startswith("UV_CACHE_DIR=.uv-cache "))
        self.assertEqual(validate_workspace_local_uv_cache_policy(rewritten), [])
        external = "UV_CACHE_DIR=/tmp/external PYTHONPATH=. uv run pytest tests/test_no_confirmation_multi_prompt_queue.py -q"
        self.assertIn("workspace-external uv cache rejected", validate_workspace_local_uv_cache_policy(external))
        self.assertTrue(normalize_validation_command_for_workspace_cache(external).startswith("UV_CACHE_DIR=.uv-cache "))

    def test_acceptance_runner_records_profile_selection_and_command_previews(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
            run_dir = repo / RUN_DIR
            profile_summary = json.loads((run_dir / "profile_selection_summary.json").read_text(encoding="utf-8"))
            evidence_summary = json.loads((run_dir / "evidence_summary.json").read_text(encoding="utf-8"))
            item_evidence = [json.loads(Path(path).read_text(encoding="utf-8")) for path in evidence_summary["evidence_paths"]]
        self.assertEqual(result["status"], "success", msg=result["errors"])
        self.assertEqual(result["current_capability_boundary_before"], BOUNDARY_BEFORE)
        self.assertEqual(result["current_capability_boundary_after"], BOUNDARY_AFTER)
        self.assertEqual(result["prompt_item_count"], 3)
        self.assertEqual(result["prompt_tick_count"], 3)
        self.assertTrue(result["all_prompt_items_use_no_confirmation_profile"])
        self.assertTrue(result["dry_run_command_construction_attached_to_evidence"])
        self.assertTrue(profile_summary["all_prompt_items_use_no_confirmation_profile"])
        self.assertEqual(len(evidence_summary["evidence_paths"]), 3)
        for evidence in item_evidence:
            self.assertEqual(evidence["selected_execution_profile"], NO_CONFIRMATION_PROFILE_NAME)
            self.assertEqual(evidence["non_interactive_command_preview"][:2], ["codex", "exec"])

    def test_acceptance_runner_records_workspace_local_cache_policy_and_confirmation_avoidance(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
            policy = json.loads((repo / RUN_DIR / "validation_command_policy.json").read_text(encoding="utf-8"))
        self.assertTrue(result["workspace_local_uv_cache_policy_implemented"])
        self.assertTrue(result["validation_commands_use_workspace_local_uv_cache"])
        self.assertTrue(result["avoidable_workspace_external_cache_confirmation_eliminated"])
        self.assertTrue(result["final_confirmation_avoidance_summary_written"])
        for command in policy["normalized_commands"]:
            if "uv run" in command:
                self.assertTrue(command.startswith("UV_CACHE_DIR=.uv-cache "))

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
            ]
            before = {path: (repo / path).read_bytes() for path in protected}
            result = self._run(repo)
            after = {path: (repo / path).read_bytes() for path in protected}
        self.assertEqual(before, after)
        for prompt in ("prompt667", "prompt668", "prompt669", "prompt670", "prompt671", "prompt672", "prompt673", "prompt674", "prompt676", "prompt677", "prompt678"):
            self.assertTrue(result[f"{prompt}_core_artifacts_preserved"], msg=prompt)
        self.assertEqual(result["prompt675_core_artifacts_preserved"], "not_present")


if __name__ == "__main__":
    unittest.main()
