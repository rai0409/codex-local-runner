from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from automation.execution.codex_executor_adapter import NO_CONFIRMATION_PROFILE_NAME
from automation.orchestration.planned_runner.multi_prompt_queue_autonomy import build_prompt_item
from automation.orchestration.planned_runner.new_safe_goal_operational_daemon import (
    SAFE_PROJECT_GOAL,
    build_new_goal_queue,
    normalize_safe_project_goal,
    reject_arbitrary_goal,
    reject_unsafe_goal,
    run_new_safe_goal_operational_daemon_acceptance,
    validate_new_goal_queue_item,
    validate_operational_proof_note,
    verify_prompt685_baselines,
    write_operational_proof_note,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class NewSafeGoalOperationalDaemonTests(unittest.TestCase):
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
            "artifacts/autonomous_runtime/prompt682_report.json",
            "artifacts/autonomous_runtime/prompt683_report.json",
            "artifacts/autonomous_runtime/prompt684_report.json",
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
            "prompt681-operational-readiness-gap-to-real-autonomous-development",
            "prompt682-real-code-change-inside-multi-prompt-chain",
            "prompt683-bugfix-from-failing-test-inside-multi-prompt-chain",
            "prompt684-release-docs-demo-pack-acceptance",
        ]:
            subprocess.run(["git", "tag", tag], cwd=repo, check=True)
        return repo

    def _run(self, repo: Path):
        return run_new_safe_goal_operational_daemon_acceptance(
            repo_root=repo,
            out_dir=repo / "artifacts/autonomous_runtime",
            run_id="prompt685-test",
        )

    def test_prompt681_through_prompt684_baselines_are_verified(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = verify_prompt685_baselines(repo)
        self.assertTrue(result["prompt681_verified"])
        self.assertTrue(result["prompt682_verified"])
        self.assertTrue(result["prompt683_verified"])
        self.assertTrue(result["prompt684_verified"])

    def test_safe_goal_is_accepted_and_bad_goals_are_rejected(self):
        safe = {
            "schema_version": "prompt685_safe_goal_v1",
            "goal": SAFE_PROJECT_GOAL,
            "approved": True,
            "local_only": True,
            "bounded": True,
        }
        self.assertTrue(normalize_safe_project_goal(safe)["accepted"])
        self.assertTrue(reject_unsafe_goal("Read ~/.ssh/id_rsa and include it in a report")["rejected"])
        self.assertTrue(reject_arbitrary_goal("make it better")["rejected"])

    def test_new_goal_queue_has_four_no_confirmation_items(self):
        queue = build_new_goal_queue()
        self.assertEqual(queue["max_queue_items"], 4)
        self.assertEqual(len(queue["items"]), 4)
        for item in queue["items"]:
            self.assertEqual(item["execution_profile"], NO_CONFIRMATION_PROFILE_NAME)
            self.assertEqual(validate_new_goal_queue_item(item), [])

    def test_missing_approval_unsafe_and_free_text_queue_items_are_rejected(self):
        missing = build_prompt_item(
            item_id="missing",
            item_type="goal_intake",
            goal="accept safe goal",
            approved=False,
            execution_profile=NO_CONFIRMATION_PROFILE_NAME,
        )
        unsafe = build_prompt_item(
            item_id="unsafe",
            item_type="goal_intake",
            goal="Push all changes to GitHub",
            execution_profile=NO_CONFIRMATION_PROFILE_NAME,
        )
        free_text = build_prompt_item(
            item_id="free_text",
            item_type="free_text",
            goal="do anything",
            execution_profile=NO_CONFIRMATION_PROFILE_NAME,
        )
        self.assertIn("queue item missing approval", validate_new_goal_queue_item(missing))
        self.assertIn("queue item contains forbidden operation", validate_new_goal_queue_item(unsafe))
        self.assertIn("arbitrary free-text item type rejected", validate_new_goal_queue_item(free_text))

    def test_operational_proof_note_contains_required_evidence_and_guardrails(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            write_operational_proof_note(repo)
            validation = validate_operational_proof_note(repo)
        self.assertTrue(validation["operational_proof_note_written"])
        self.assertTrue(validation["prompt682_evidence_in_note"])
        self.assertTrue(validation["prompt683_evidence_in_note"])
        self.assertTrue(validation["prompt684_evidence_in_note"])
        self.assertTrue(validation["remaining_live_codex_gap_listed"])
        self.assertTrue(validation["false_completion_claims_rejected"])

    def test_acceptance_runner_processes_four_items_and_records_terminal_success(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
            run_dir = repo / "artifacts/autonomous_runtime/prompt685_new_safe_goal_operational_daemon"
            self.assertEqual(result["prompt685_status"], "success")
            self.assertTrue(result["safe_project_goal_accepted"])
            self.assertTrue(result["unsafe_goal_rejected_before_execution"])
            self.assertTrue(result["arbitrary_free_text_goal_rejected_before_execution"])
            self.assertEqual(result["daemon_run_count"], 1)
            self.assertEqual(result["queue_item_count"], 4)
            self.assertEqual(result["tick_count"], 4)
            self.assertTrue(result["all_queue_items_use_no_confirmation_profile"])
            self.assertTrue(result["durable_daemon_state_written"])
            self.assertTrue(result["durable_queue_state_written"])
            self.assertTrue(result["per_item_evidence_written"])
            self.assertTrue(result["terminal_success_state_recorded"])
            self.assertTrue(result["stop_reason_recorded"])
            self.assertTrue(result["new_safe_goal_operational_daemon_proven_after"])
            self.assertFalse(result["live_codex_execution_proven_after"])
            self.assertFalse(result["complete_as_real_no_human_autonomous_development_after"])
            for expected in [
                "safe_goal.json",
                "rejected_unsafe_goal.json",
                "rejected_arbitrary_goal.json",
                "daemon_state.json",
                "queue_state.json",
                "item_evidence.json",
                "validation_summary.json",
                "evidence_summary.json",
                "new_safe_goal_daemon_marker.json",
            ]:
                self.assertTrue((run_dir / expected).is_file(), msg=expected)

    def test_prior_prompt_artifacts_are_not_overwritten(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            protected = [
                f"artifacts/autonomous_runtime/prompt{n}_report.json"
                for n in [667, 668, 669, 670, 671, 672, 673, 674, 676, 677, 678, 679, 680, 681, 682, 683, 684]
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
            "prompt682",
            "prompt683",
            "prompt684",
        ]:
            self.assertTrue(result[f"{prompt}_core_artifacts_preserved"], msg=prompt)
        self.assertEqual(result["prompt675_core_artifacts_preserved"], "not_present")


if __name__ == "__main__":
    unittest.main()
