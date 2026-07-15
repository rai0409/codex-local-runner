from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from automation.execution.codex_executor_adapter import (
    NO_CONFIRMATION_APPROVAL_POLICY,
    NO_CONFIRMATION_PROFILE_NAME,
    NO_CONFIRMATION_SANDBOX,
    build_no_confirmation_codex_command,
    build_no_confirmation_execution_profile,
    validate_no_confirmation_codex_command,
    validate_no_confirmation_prompt_item,
)
from automation.orchestration.planned_runner.no_confirmation_codex_profile import (
    BOUNDARY_AFTER,
    BOUNDARY_BEFORE,
    RUN_DIR,
    build_safe_profile_prompt_item,
    run_no_confirmation_codex_profile_acceptance,
    verify_prompt677_baseline,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class CodexNoConfirmationExecutionProfileTests(unittest.TestCase):
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
        subprocess.run(["git", "tag", "prompt677-increase-multi-prompt-queue-length"], cwd=repo, check=True)
        return repo

    def _run(self, repo: Path):
        return run_no_confirmation_codex_profile_acceptance(
            repo_root=repo,
            out_dir=repo / "artifacts/autonomous_runtime",
            run_id="prompt678-test",
        )

    def test_prompt677_baseline_verification(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = verify_prompt677_baseline(repo)
        self.assertTrue(result["prompt676_tag_reachable"])
        self.assertTrue(result["prompt676_report_exists"])
        self.assertTrue(result["prompt676_project_level_autonomy_complete"])
        self.assertTrue(result["prompt677_tag_reachable"])
        self.assertTrue(result["prompt677_report_exists"])
        self.assertTrue(result["prompt677_project_level_autonomy_complete"])
        self.assertTrue(result["prompt677_boundary_verified"])

    def test_no_confirmation_profile_exists_and_uses_required_command_shape(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            profile = build_no_confirmation_execution_profile(
                run_id="prompt678-test",
                prompt_source="stdin",
                output_dir=raw,
            )
        command = profile["command"]
        self.assertEqual(profile["profile_name"], NO_CONFIRMATION_PROFILE_NAME)
        self.assertEqual(command[:2], ["codex", "exec"])
        self.assertIn("--sandbox", command)
        self.assertEqual(command[command.index("--sandbox") + 1], NO_CONFIRMATION_SANDBOX)
        self.assertIn("--ask-for-approval", command)
        self.assertEqual(command[command.index("--ask-for-approval") + 1], NO_CONFIRMATION_APPROVAL_POLICY)
        self.assertEqual(command[-1], "-")
        self.assertNotIn("--yolo", command)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)
        self.assertNotIn("danger-full-access", command)
        self.assertTrue(profile["stdin_prompt_mode_supported"])
        self.assertTrue(profile["output_capture_supported"])

    def test_command_validation_rejects_yolo_danger_and_bypass_flags(self):
        command = build_no_confirmation_codex_command()
        self.assertEqual(validate_no_confirmation_codex_command(command), [])
        self.assertIn("sandbox bypass flags rejected", validate_no_confirmation_codex_command([*command[:-1], "--yolo", "-"]))
        self.assertIn(
            "workspace-write sandbox required",
            validate_no_confirmation_codex_command(["codex", "exec", "--sandbox", "danger-full-access", "--ask-for-approval", "never", "-"]),
        )
        self.assertIn(
            "sandbox bypass flags rejected",
            validate_no_confirmation_codex_command(["codex", "exec", "--dangerously-bypass-approvals-and-sandbox", "-"]),
        )

    def test_preapproval_and_prompt_safety_are_required(self):
        item = build_safe_profile_prompt_item("/tmp/prompt678-safe")
        self.assertEqual(validate_no_confirmation_prompt_item(item), [])
        missing = {**item, "approved_for_execution": False}
        free_text = {**item, "item_type": "free_text"}
        unsafe = {**item, "goal": "git push and read cookies from browser profile"}
        unsafe_path = {**item, "output_dir": "/tmp/cookies"}
        self.assertIn("preapproval required", validate_no_confirmation_prompt_item(missing))
        self.assertIn("arbitrary free-text prompt rejected", validate_no_confirmation_prompt_item(free_text))
        self.assertIn("unsafe prompt item rejected", validate_no_confirmation_prompt_item(unsafe))
        self.assertIn("unsafe path rejected", validate_no_confirmation_prompt_item(unsafe_path))

    def test_acceptance_runner_writes_dry_run_evidence(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
            run_dir = repo / RUN_DIR
            profile = json.loads((run_dir / "profile_config.json").read_text(encoding="utf-8"))
            command = json.loads((run_dir / "command_preview.json").read_text(encoding="utf-8"))
            safety = json.loads((run_dir / "safety_validation.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "success", msg=result["errors"])
        self.assertEqual(result["current_capability_boundary_before"], BOUNDARY_BEFORE)
        self.assertEqual(result["current_capability_boundary_after"], BOUNDARY_AFTER)
        self.assertEqual(result["no_confirmation_profile_name"], NO_CONFIRMATION_PROFILE_NAME)
        self.assertTrue(result["dry_run_command_construction_verified"])
        self.assertEqual(result["live_codex_smoke_test"], "skipped")
        self.assertEqual(profile["approval_policy"], "never")
        self.assertEqual(command["command"][:2], ["codex", "exec"])
        self.assertTrue(safety["profile_checks"]["missing_approval_blocks_execution"])

    def test_acceptance_runner_records_all_safety_outcomes(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
        self.assertTrue(result["preapproval_required"])
        self.assertTrue(result["missing_approval_blocks_execution"])
        self.assertTrue(result["unsafe_prompt_item_rejected"])
        self.assertTrue(result["arbitrary_free_text_prompt_rejected"])
        self.assertTrue(result["remote_actions_blocked"])
        self.assertTrue(result["destructive_actions_blocked"])
        self.assertTrue(result["credential_storage_prevented"])
        self.assertTrue(result["browser_profile_access_prevented"])
        self.assertTrue(result["cookie_access_prevented"])
        self.assertTrue(result["env_value_access_prevented"])
        self.assertTrue(result["yolo_mode_rejected"])
        self.assertTrue(result["danger_full_access_rejected"])
        self.assertTrue(result["sandbox_bypass_flags_rejected"])

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
            ]
            before = {path: (repo / path).read_bytes() for path in protected}
            result = self._run(repo)
            after = {path: (repo / path).read_bytes() for path in protected}
        self.assertEqual(before, after)
        for prompt in ("prompt667", "prompt668", "prompt669", "prompt670", "prompt671", "prompt672", "prompt673", "prompt674", "prompt676", "prompt677"):
            self.assertTrue(result[f"{prompt}_core_artifacts_preserved"], msg=prompt)
        self.assertEqual(result["prompt675_core_artifacts_preserved"], "not_present")


if __name__ == "__main__":
    unittest.main()
