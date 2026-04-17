from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from automation.control.next_action_controller import ALLOWED_NEXT_ACTIONS
from automation.control.next_action_controller import evaluate_next_action_from_run_dir


class NextActionControllerTests(unittest.TestCase):
    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _cli_path(self) -> Path:
        return self._repo_root() / "scripts" / "evaluate_next_action.py"

    def _base_manifest(self, run_dir: Path) -> dict[str, object]:
        return {
            "job_id": "job-next-action",
            "run_status": "dry_run_completed",
            "artifact_input_dir": str(run_dir / "planning"),
            "started_at": "2026-04-18T00:00:00+00:00",
            "finished_at": "2026-04-18T00:05:00+00:00",
            "dry_run": True,
            "stop_on_failure": True,
            "pr_units": [
                {
                    "pr_id": "pr-01",
                    "compiled_prompt_path": str(run_dir / "pr-01" / "compiled_prompt.md"),
                    "result_path": str(run_dir / "pr-01" / "result.json"),
                    "receipt_path": str(run_dir / "pr-01" / "execution_receipt.json"),
                    "status": "recorded",
                }
            ],
        }

    def _base_receipt(self) -> dict[str, object]:
        return {
            "job_id": "job-next-action",
            "pr_id": "pr-01",
            "status": "recorded",
            "dry_run": True,
            "run_id": "job-next-action:pr-01:dry-run",
            "execution_status": "not_started",
            "compiled_prompt_path": "/tmp/compiled_prompt.md",
            "result_path": "/tmp/result.json",
            "stdout_path": "/tmp/stdout.txt",
            "stderr_path": "/tmp/stderr.txt",
            "tier_category": "runtime_fix_low_risk",
            "depends_on": [],
            "started_at": "2026-04-18T00:00:00+00:00",
            "finished_at": "2026-04-18T00:00:01+00:00",
        }

    def _base_result(self) -> dict[str, object]:
        return {
            "job_id": "job-next-action",
            "pr_id": "pr-01",
            "changed_files": [],
            "execution": {
                "status": "not_started",
                "attempt_count": 0,
                "started_at": "2026-04-18T00:00:00+00:00",
                "finished_at": "2026-04-18T00:00:01+00:00",
                "stdout_path": "/tmp/stdout.txt",
                "stderr_path": "/tmp/stderr.txt",
                "verify": {
                    "status": "not_run",
                    "commands": ["python3 -m unittest -q"],
                    "reason": "validation_not_run_dry_run",
                },
            },
            "additions": 0,
            "deletions": 0,
            "generated_patch_summary": "",
            "failure_type": "missing_signal",
            "failure_message": "dry_run_execution_not_performed",
            "cost": {
                "tokens_input": 0,
                "tokens_output": 0,
            },
        }

    def _base_pr_plan(self) -> dict[str, object]:
        return {
            "plan_id": "plan-1",
            "prs": [
                {
                    "pr_id": "pr-01",
                    "title": "slice",
                    "exact_scope": "exact scope",
                    "touched_files": ["automation/control/next_action_controller.py"],
                    "forbidden_files": ["orchestrator/main.py"],
                    "acceptance_criteria": ["criteria"],
                    "validation_commands": ["python3 -m unittest tests.test_next_action_controller -v"],
                    "rollback_notes": "rollback",
                    "tier_category": "runtime_fix_low_risk",
                    "depends_on": [],
                }
            ],
        }

    def _write_run(self, root: Path, *, receipt: dict | None, result: dict | None, manifest: dict | None = None) -> Path:
        run_dir = root / "run"
        unit_dir = run_dir / "pr-01"
        unit_dir.mkdir(parents=True, exist_ok=True)
        (unit_dir / "compiled_prompt.md").write_text("prompt", encoding="utf-8")

        manifest_payload = manifest or self._base_manifest(run_dir)
        (run_dir / "manifest.json").write_text(
            json.dumps(manifest_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        if receipt is not None:
            (unit_dir / "execution_receipt.json").write_text(
                json.dumps(receipt, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        if result is not None:
            (unit_dir / "result.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return run_dir

    def test_dry_run_completed_recorded_not_started_is_not_false_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            run_dir = self._write_run(root, receipt=self._base_receipt(), result=self._base_result())
            decision = evaluate_next_action_from_run_dir(run_dir, pr_plan=self._base_pr_plan())

        self.assertEqual(decision["next_action"], "signal_recollect")
        self.assertFalse(decision["next_action"] in {"proceed_to_pr", "proceed_to_merge"})

    def test_execution_failure_maps_to_same_prompt_retry_when_scope_valid(self) -> None:
        receipt = self._base_receipt()
        result = self._base_result()
        result["execution"]["status"] = "failed"
        result["failure_type"] = "execution_failure"
        result["failure_message"] = "tool exited with code 2"

        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = self._write_run(Path(tmp_dir), receipt=receipt, result=result)
            decision = evaluate_next_action_from_run_dir(
                run_dir,
                retry_context={"retry_budget_remaining": 2, "prior_retry_class": None},
                pr_plan=self._base_pr_plan(),
            )

        self.assertEqual(decision["next_action"], "same_prompt_retry")

    def test_validation_failure_maps_to_repair_prompt_retry(self) -> None:
        receipt = self._base_receipt()
        result = self._base_result()
        result["execution"]["status"] = "completed"
        result["execution"]["verify"]["status"] = "failed"
        result["execution"]["verify"]["reason"] = "validation_failed"
        result["failure_type"] = "evaluation_failure"
        result["failure_message"] = "tests failed"

        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = self._write_run(Path(tmp_dir), receipt=receipt, result=result)
            decision = evaluate_next_action_from_run_dir(
                run_dir,
                retry_context={"retry_budget_remaining": 2, "prior_retry_class": None},
                pr_plan=self._base_pr_plan(),
            )

        self.assertEqual(decision["next_action"], "repair_prompt_retry")

    def test_missing_artifacts_maps_conservatively(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = self._write_run(Path(tmp_dir), receipt=self._base_receipt(), result=None)
            decision = evaluate_next_action_from_run_dir(
                run_dir,
                retry_context={"missing_signal_count": 0, "retry_budget_remaining": 1},
                pr_plan=self._base_pr_plan(),
            )

        self.assertIn(decision["next_action"], {"signal_recollect", "escalate_to_human"})

    def test_scope_drift_maps_to_prompt_recompile(self) -> None:
        receipt = self._base_receipt()
        result = self._base_result()
        result["execution"]["status"] = "completed"
        result["execution"]["verify"]["status"] = "passed"
        result["changed_files"] = [
            "automation/control/next_action_controller.py",
            "unexpected/file.py",
        ]
        result["failure_type"] = None
        result["failure_message"] = None

        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = self._write_run(Path(tmp_dir), receipt=receipt, result=result)
            decision = evaluate_next_action_from_run_dir(run_dir, pr_plan=self._base_pr_plan())

        self.assertEqual(decision["next_action"], "prompt_recompile")

    def test_category_mismatch_maps_to_roadmap_replan(self) -> None:
        receipt = self._base_receipt()
        receipt["tier_category"] = "runtime_fix_high_risk"
        result = self._base_result()

        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = self._write_run(Path(tmp_dir), receipt=receipt, result=result)
            decision = evaluate_next_action_from_run_dir(run_dir, pr_plan=self._base_pr_plan())

        self.assertEqual(decision["next_action"], "roadmap_replan")

    def test_exhausted_retry_budget_maps_to_escalate(self) -> None:
        receipt = self._base_receipt()
        result = self._base_result()
        result["execution"]["status"] = "failed"
        result["failure_type"] = "execution_failure"

        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = self._write_run(Path(tmp_dir), receipt=receipt, result=result)
            decision = evaluate_next_action_from_run_dir(
                run_dir,
                retry_context={"retry_budget_remaining": 0},
                pr_plan=self._base_pr_plan(),
            )

        self.assertEqual(decision["next_action"], "escalate_to_human")
        self.assertTrue(decision["whether_human_required"])

    def test_exactly_one_next_action_is_returned(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = self._write_run(Path(tmp_dir), receipt=self._base_receipt(), result=self._base_result())
            decision = evaluate_next_action_from_run_dir(run_dir, pr_plan=self._base_pr_plan())

        self.assertEqual(set(decision.keys()), {
            "next_action",
            "reason",
            "retry_budget_remaining",
            "whether_human_required",
            "updated_retry_context",
        })
        self.assertIn(decision["next_action"], ALLOWED_NEXT_ACTIONS)

    def test_deterministic_output_for_identical_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = self._write_run(Path(tmp_dir), receipt=self._base_receipt(), result=self._base_result())
            first = evaluate_next_action_from_run_dir(
                run_dir,
                retry_context={"retry_budget_remaining": 2, "missing_signal_count": 1},
                pr_plan=self._base_pr_plan(),
            )
            second = evaluate_next_action_from_run_dir(
                run_dir,
                retry_context={"retry_budget_remaining": 2, "missing_signal_count": 1},
                pr_plan=self._base_pr_plan(),
            )

        self.assertEqual(first, second)

    def test_invalid_cli_input_handling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing_run_dir = Path(tmp_dir) / "missing"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(self._cli_path()),
                    "--run-dir",
                    str(missing_run_dir),
                    "--json",
                ],
                capture_output=True,
                text=True,
                cwd=self._repo_root(),
            )

        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("run artifact directory does not exist", proc.stderr)


if __name__ == "__main__":
    unittest.main()
