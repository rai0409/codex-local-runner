from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from automation.execution.codex_executor_adapter import NO_CONFIRMATION_PROFILE_NAME
from automation.orchestration.planned_runner.multi_prompt_queue_autonomy import build_prompt_item
from automation.orchestration.planned_runner.release_docs_demo_pack import (
    REQUIRED_DOCS,
    build_release_docs_prompt_queue,
    run_release_docs_demo_pack_acceptance,
    validate_release_docs,
    validate_release_docs_prompt_item,
    verify_prompt684_baselines,
    write_release_docs,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class ReleaseDocsDemoPackTests(unittest.TestCase):
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
        ]:
            subprocess.run(["git", "tag", tag], cwd=repo, check=True)
        return repo

    def _run(self, repo: Path):
        return run_release_docs_demo_pack_acceptance(
            repo_root=repo,
            out_dir=repo / "artifacts/autonomous_runtime",
            run_id="prompt684-test",
        )

    def test_prompt681_prompt682_and_prompt683_baselines_are_verified(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = verify_prompt684_baselines(repo)
        self.assertTrue(result["prompt681_verified"])
        self.assertTrue(result["prompt682_verified"])
        self.assertTrue(result["prompt683_verified"])

    def test_release_docs_prompt_queue_has_five_no_confirmation_items(self):
        queue = build_release_docs_prompt_queue()
        self.assertEqual(queue["max_prompt_items"], 5)
        self.assertEqual(len(queue["items"]), 5)
        for item in queue["items"]:
            self.assertEqual(item["execution_profile"], NO_CONFIRMATION_PROFILE_NAME)
            self.assertEqual(validate_release_docs_prompt_item(item), [])

    def test_missing_approval_unsafe_and_free_text_items_are_rejected(self):
        missing = build_prompt_item(
            item_id="missing",
            item_type="release_docs_generate",
            goal="generate local docs",
            approved=False,
            execution_profile=NO_CONFIRMATION_PROFILE_NAME,
        )
        unsafe = build_prompt_item(
            item_id="unsafe",
            item_type="release_docs_generate",
            goal="publish docs and git push",
            execution_profile=NO_CONFIRMATION_PROFILE_NAME,
        )
        free_text = build_prompt_item(
            item_id="free_text",
            item_type="free_text",
            goal="write anything",
            execution_profile=NO_CONFIRMATION_PROFILE_NAME,
        )
        self.assertIn("prompt item missing approval", validate_release_docs_prompt_item(missing))
        self.assertIn("prompt item contains forbidden operation", validate_release_docs_prompt_item(unsafe))
        self.assertIn("arbitrary free-text prompt type rejected", validate_release_docs_prompt_item(free_text))

    def test_write_and_validate_release_docs(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            written = write_release_docs(repo)
            validation = validate_release_docs(repo)
            combined = "\n".join((repo / path).read_text(encoding="utf-8") for path in REQUIRED_DOCS)
        self.assertEqual(len(written), len(REQUIRED_DOCS))
        self.assertTrue(validation["release_docs_files_created"])
        self.assertTrue(validation["required_sections_validated"])
        self.assertTrue(validation["evidence_references_validated"])
        self.assertTrue(validation["prompt677_evidence_referenced"])
        self.assertTrue(validation["prompt679_evidence_referenced"])
        self.assertTrue(validation["prompt680_evidence_referenced"])
        self.assertTrue(validation["prompt682_evidence_referenced"])
        self.assertTrue(validation["prompt683_evidence_referenced"])
        self.assertTrue(validation["false_completion_claims_rejected"])
        self.assertTrue(validation["remaining_false_items_listed"])
        self.assertIn("complete_as_real_no_human_autonomous_development=false", combined)
        self.assertIn("live_codex_execution_proven_after=false", combined)
        self.assertIn("new_safe_goal_operational_daemon_proven_after=false", combined)

    def test_false_completion_claim_is_rejected(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            write_release_docs(repo)
            target = repo / REQUIRED_DOCS[0]
            target.write_text(target.read_text(encoding="utf-8") + "\nThis is fully complete.\n", encoding="utf-8")
            validation = validate_release_docs(repo)
        self.assertFalse(validation["false_completion_claims_rejected"])
        self.assertFalse(validation["docs_validation_passed"])

    def test_acceptance_runner_processes_five_items_and_proves_release_docs(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
            run_dir = repo / "artifacts/autonomous_runtime/prompt684_release_docs_demo_pack"
            evidence = json.loads((run_dir / "evidence_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(result["prompt684_status"], "success")
        self.assertEqual(result["prompt_item_count"], 5)
        self.assertEqual(result["prompt_tick_count"], 5)
        self.assertTrue(result["all_prompt_items_use_no_confirmation_profile"])
        self.assertTrue(result["workspace_local_uv_cache_policy_used"])
        self.assertTrue(result["release_docs_files_created"])
        self.assertTrue(result["release_docs_demo_pack_proven_after"])
        self.assertTrue(result["real_code_change_proven_after"])
        self.assertTrue(result["bugfix_from_failing_test_proven_after"])
        self.assertFalse(result["live_codex_execution_proven_after"])
        self.assertFalse(result["new_safe_goal_operational_daemon_proven_after"])
        self.assertFalse(result["complete_as_real_no_human_autonomous_development_after"])
        self.assertEqual(len(evidence["evidence_paths"]), 5)

    def test_prior_prompt_artifacts_are_not_overwritten(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            protected = [
                f"artifacts/autonomous_runtime/prompt{n}_report.json"
                for n in [667, 668, 669, 670, 671, 672, 673, 674, 676, 677, 678, 679, 680, 681, 682, 683]
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
        ]:
            self.assertTrue(result[f"{prompt}_core_artifacts_preserved"], msg=prompt)
        self.assertEqual(result["prompt675_core_artifacts_preserved"], "not_present")


if __name__ == "__main__":
    unittest.main()
