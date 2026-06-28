from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from automation.orchestration.planned_runner.operational_readiness_gap import (
    BOUNDARY_BEFORE,
    MATRIX_PATH,
    RUN_DIR,
    build_readiness_matrix,
    run_operational_readiness_gap_acceptance,
    verify_baselines,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class OperationalReadinessGapTests(unittest.TestCase):
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
        ]
        for path in required:
            source = REPO_ROOT / path
            target = repo / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(["git", "-c", "user.email=t@example.local", "-c", "user.name=T", "commit", "-q", "-m", "fixture"], cwd=repo, check=True)
        for tag in [
            "prompt677-increase-multi-prompt-queue-length",
            "prompt678-codex-no-confirmation-execution-profile",
            "prompt679-wire-no-confirmation-profile-into-multi-prompt-queue",
            "prompt680-multi-prompt-real-task-chain-acceptance",
        ]:
            subprocess.run(["git", "tag", tag], cwd=repo, check=True)
        return repo

    def _run(self, repo: Path):
        return run_operational_readiness_gap_acceptance(
            repo_root=repo,
            out_dir=repo / "artifacts/autonomous_runtime",
            run_id="prompt681-test",
        )

    def test_baselines_and_prompt675_detection(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = verify_baselines(repo)
        self.assertTrue(result["prompt680_verified"])
        self.assertTrue(result["prompt679_verified"])
        self.assertTrue(result["prompt678_verified"])
        self.assertTrue(result["prompt677_verified"])
        self.assertEqual(result["prompt675_verified"], "not_present")

    def test_matrix_is_complete_false_for_unproven_real_operation_gaps(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            matrix = build_readiness_matrix(repo)
        self.assertFalse(matrix["complete_as_real_no_human_autonomous_development"])
        by_id = {item["id"]: item for item in matrix["criteria"]}
        self.assertEqual(by_id[4]["status"], "unproven")
        self.assertEqual(by_id[6]["status"], "unproven")
        self.assertEqual(by_id[16]["status"], "unproven")
        self.assertEqual(by_id[17]["status"], "unproven")
        self.assertGreaterEqual(len(matrix["blocking_gaps"]), 5)

    def test_matrix_contains_required_fields_for_each_criterion(self):
        matrix = build_readiness_matrix(REPO_ROOT)
        required = {"id", "name", "status", "evidence_prompt", "evidence_commit", "evidence_tag", "evidence_field", "missing_proof", "required_prompt", "pass_criteria", "safety_notes"}
        self.assertEqual(matrix["total_criteria_count"], len(matrix["criteria"]))
        self.assertGreaterEqual(matrix["total_criteria_count"], 16)
        for criterion in matrix["criteria"]:
            self.assertTrue(required.issubset(criterion), msg=criterion)
            self.assertIn(criterion["status"], {"proven", "partially_proven", "unproven", "out_of_scope_for_safety"})

    def test_next_prompt_sequence_starts_with_real_code_change(self):
        matrix = build_readiness_matrix(REPO_ROOT)
        self.assertEqual(matrix["next_prompt_sequence"][0]["prompt_id"], "Prompt682")
        self.assertIn("real_code_change", matrix["next_prompt_sequence"][0]["title"])
        self.assertEqual(matrix["next_recommended_action"], "continue_to_real_code_change_inside_multi_prompt_chain_acceptance")

    def test_acceptance_writes_reports_and_avoids_abstract_language(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
            doc = (repo / "docs/autonomous_runtime/operational_readiness_gap_to_real_autonomous_development.md").read_text(encoding="utf-8")
            matrix = json.loads((repo / MATRIX_PATH).read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["current_capability_boundary_before"], BOUNDARY_BEFORE)
        self.assertFalse(result["complete_as_real_no_human_autonomous_development"])
        self.assertTrue(result["readiness_matrix_written"])
        self.assertTrue(result["human_readable_report_written"])
        self.assertTrue(result["workspace_local_uv_cache_policy_used"])
        self.assertNotIn("moving in the right direction", doc.lower())
        self.assertNotIn("progress", doc.lower())
        self.assertFalse(matrix["complete_as_real_no_human_autonomous_development"])

    def test_prior_core_artifacts_are_not_overwritten(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            protected = [f"artifacts/autonomous_runtime/prompt{n}_report.json" for n in [667, 668, 669, 670, 671, 672, 673, 674, 676, 677, 678, 679, 680]]
            before = {path: (repo / path).read_bytes() for path in protected}
            result = self._run(repo)
            after = {path: (repo / path).read_bytes() for path in protected}
        self.assertEqual(before, after)
        for prompt in ("prompt667", "prompt668", "prompt669", "prompt670", "prompt671", "prompt672", "prompt673", "prompt674", "prompt676", "prompt677", "prompt678", "prompt679", "prompt680"):
            self.assertTrue(result[f"{prompt}_core_artifacts_preserved"], msg=prompt)
        self.assertEqual(result["prompt675_core_artifacts_preserved"], "not_present")


if __name__ == "__main__":
    unittest.main()
