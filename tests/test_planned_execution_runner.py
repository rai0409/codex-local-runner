from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from automation.execution.codex_executor_adapter import CodexExecutorAdapter
from automation.orchestration.planned_execution_runner import DryRunCodexExecutionTransport
from automation.orchestration.planned_execution_runner import PlannedExecutionRunner


class _RecordingDryRunTransport(DryRunCodexExecutionTransport):
    def __init__(self, *, status_by_pr_id: dict[str, str] | None = None) -> None:
        super().__init__(status_by_pr_id=status_by_pr_id)
        self.launch_order: list[str] = []

    def launch_job(self, **kwargs):  # type: ignore[override]
        self.launch_order.append(str(kwargs.get("pr_id", "")))
        return super().launch_job(**kwargs)


class PlannedExecutionRunnerTests(unittest.TestCase):
    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _script_path(self) -> Path:
        return self._repo_root() / "scripts" / "run_planned_execution.py"

    def _write_planning_artifacts(self, root: Path) -> Path:
        artifacts_dir = root / "planning_artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        project_brief = {
            "project_id": "project-planned-exec",
            "objective": "Run deterministic planned dry-run execution",
            "success_definition": "Each PR slice gets prompt, result, and receipt",
            "constraints": ["additive only"],
            "non_goals": ["no scheduler"],
            "allowed_risk_level": "conservative",
            "target_repo": "codex-local-runner",
            "target_branch": "main",
            "requested_by": "operator",
            "created_at": "2026-04-18T00:00:00+00:00",
        }
        repo_facts = {
            "repo": "codex-local-runner",
            "default_branch": "main",
            "relevant_paths": ["automation/planning", "automation/execution", "automation/orchestration"],
            "entrypoints": ["scripts/run_planned_execution.py"],
            "tests_available": ["tests/test_planned_execution_runner.py"],
            "build_commands": ["python3 -m unittest discover -s tests"],
            "lint_commands": [],
            "current_branch_rules": ["require_ci_green=true"],
            "sensitive_paths": ["orchestrator/**"],
            "source_of_truth_commit": "abc123",
        }
        roadmap = {
            "roadmap_id": "project-planned-exec-roadmap-v1",
            "milestones": [
                {
                    "milestone_id": "m-01",
                    "title": "ordered slices",
                    "tier_category": "runtime_fix_low_risk",
                    "pr_ids": [
                        "project-planned-exec-pr-01",
                        "project-planned-exec-pr-02",
                        "project-planned-exec-pr-03",
                    ],
                }
            ],
            "dependency_edges": [
                {"from": "project-planned-exec-pr-01", "to": "project-planned-exec-pr-02"},
                {"from": "project-planned-exec-pr-02", "to": "project-planned-exec-pr-03"},
            ],
            "blocked_by": [],
            "estimated_risk": "medium",
        }
        pr_plan = {
            "plan_id": "project-planned-exec-plan-v1",
            "prs": [
                {
                    "pr_id": "project-planned-exec-pr-01",
                    "title": "[planning] first slice",
                    "exact_scope": "Create first scoped unit",
                    "touched_files": ["automation/planning/prompt_compiler.py"],
                    "forbidden_files": ["orchestrator/main.py"],
                    "acceptance_criteria": ["first unit compiled"],
                    "validation_commands": ["python3 -m unittest tests.test_prompt_compiler -v"],
                    "rollback_notes": "revert slice 1",
                    "tier_category": "runtime_fix_low_risk",
                    "depends_on": [],
                },
                {
                    "pr_id": "project-planned-exec-pr-02",
                    "title": "[execution] second slice",
                    "exact_scope": "Create second scoped unit",
                    "touched_files": ["automation/execution/codex_executor_adapter.py"],
                    "forbidden_files": ["orchestrator/merge_executor.py"],
                    "acceptance_criteria": ["second unit compiled"],
                    "validation_commands": ["python3 -m unittest tests.test_codex_executor_adapter -v"],
                    "rollback_notes": "revert slice 2",
                    "tier_category": "runtime_fix_high_risk",
                    "depends_on": ["project-planned-exec-pr-01"],
                },
                {
                    "pr_id": "project-planned-exec-pr-03",
                    "title": "[orchestration] third slice",
                    "exact_scope": "Create third scoped unit",
                    "touched_files": ["automation/orchestration/planned_execution_runner.py"],
                    "forbidden_files": ["orchestrator/rollback_executor.py"],
                    "acceptance_criteria": ["third unit compiled"],
                    "validation_commands": ["python3 -m unittest tests.test_planned_execution_runner -v"],
                    "rollback_notes": "revert slice 3",
                    "tier_category": "runtime_fix_high_risk",
                    "depends_on": ["project-planned-exec-pr-02"],
                },
            ],
            "canonical_surface_notes": ["inspect_job remains authority"],
            "compatibility_notes": ["legacy replan_input.* preserved"],
            "planning_warnings": [],
        }

        write_map = {
            "project_brief.json": project_brief,
            "repo_facts.json": repo_facts,
            "roadmap.json": roadmap,
            "pr_plan.json": pr_plan,
        }
        for filename, payload in write_map.items():
            (artifacts_dir / filename).write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return artifacts_dir

    def test_deterministic_processing_order_for_multiple_pr_slices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"

            transport = _RecordingDryRunTransport()
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest_a = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
            )
            order_a = list(transport.launch_order)

            transport_b = _RecordingDryRunTransport()
            runner_b = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport_b))
            manifest_b = runner_b.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
            )
            order_b = list(transport_b.launch_order)

        self.assertEqual(
            order_a,
            [
                "project-planned-exec-pr-01",
                "project-planned-exec-pr-02",
                "project-planned-exec-pr-03",
            ],
        )
        self.assertEqual(order_a, order_b)
        self.assertEqual(
            [entry["pr_id"] for entry in manifest_a["pr_units"]],
            [entry["pr_id"] for entry in manifest_b["pr_units"]],
        )

    def test_pr_id_mapping_and_artifact_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"

            transport = _RecordingDryRunTransport()
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
            )

            run_root = out_dir / manifest["job_id"]
            self.assertTrue((run_root / "manifest.json").exists())

            for entry in manifest["pr_units"]:
                pr_id = entry["pr_id"]
                unit_dir = run_root / pr_id
                self.assertTrue(unit_dir.exists())
                self.assertTrue((unit_dir / "compiled_prompt.md").exists())
                self.assertTrue((unit_dir / "result.json").exists())
                self.assertTrue((unit_dir / "execution_receipt.json").exists())

                result_payload = json.loads((unit_dir / "result.json").read_text(encoding="utf-8"))
                receipt_payload = json.loads((unit_dir / "execution_receipt.json").read_text(encoding="utf-8"))
                prompt_text = (unit_dir / "compiled_prompt.md").read_text(encoding="utf-8")

                self.assertEqual(result_payload["pr_id"], pr_id)
                self.assertEqual(receipt_payload["pr_id"], pr_id)
                self.assertIn(f"Execute exactly one PR slice: {pr_id}", prompt_text)

    def test_manifest_generation_and_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=_RecordingDryRunTransport()))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
            )

        self.assertIn("job_id", manifest)
        self.assertIn("run_status", manifest)
        self.assertIn("artifact_input_dir", manifest)
        self.assertIn("started_at", manifest)
        self.assertIn("finished_at", manifest)
        self.assertIn("pr_units", manifest)
        self.assertEqual(manifest["run_status"], "dry_run_completed")
        self.assertGreaterEqual(len(manifest["pr_units"]), 1)

    def test_stop_on_failure_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"

            transport = _RecordingDryRunTransport(
                status_by_pr_id={"project-planned-exec-pr-02": "failed"}
            )
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
            )

        self.assertEqual(manifest["run_status"], "failed")
        self.assertEqual(
            [entry["pr_id"] for entry in manifest["pr_units"]],
            [
                "project-planned-exec-pr-01",
                "project-planned-exec-pr-02",
            ],
        )

    def test_dry_run_transport_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"

            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=_RecordingDryRunTransport()))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
            )
            first = manifest["pr_units"][0]
            result_payload = json.loads(Path(first["result_path"]).read_text(encoding="utf-8"))

        self.assertEqual(result_payload["execution"]["status"], "not_started")
        self.assertEqual(result_payload["execution"]["verify"]["status"], "not_run")
        self.assertEqual(result_payload["failure_type"], "missing_signal")

    def test_invalid_cli_input_handling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = root / "missing_artifacts"
            out_dir = root / "out"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(self._script_path()),
                    "--artifacts-dir",
                    str(artifacts_dir),
                    "--out-dir",
                    str(out_dir),
                    "--json",
                ],
                capture_output=True,
                text=True,
                cwd=self._repo_root(),
            )

        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("artifacts directory does not exist", proc.stderr)

    def test_manifest_paths_and_status_fields_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=_RecordingDryRunTransport()))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
            )

            for entry in manifest["pr_units"]:
                self.assertIn("compiled_prompt_path", entry)
                self.assertIn("result_path", entry)
                self.assertIn("receipt_path", entry)
                self.assertIn("status", entry)
                self.assertTrue(Path(entry["compiled_prompt_path"]).exists())
                self.assertTrue(Path(entry["result_path"]).exists())
                self.assertTrue(Path(entry["receipt_path"]).exists())

    def test_result_shape_compatibility_with_current_expectations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=_RecordingDryRunTransport()))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
            )
            first = manifest["pr_units"][0]
            payload = json.loads(Path(first["result_path"]).read_text(encoding="utf-8"))

        self.assertIn("job_id", payload)
        self.assertIn("pr_id", payload)
        self.assertIn("changed_files", payload)
        self.assertIn("execution", payload)
        self.assertIn("additions", payload)
        self.assertIn("deletions", payload)
        self.assertIn("generated_patch_summary", payload)
        self.assertIn("failure_type", payload)
        self.assertIn("failure_message", payload)
        self.assertIn("cost", payload)
        self.assertIn("verify", payload["execution"])


if __name__ == "__main__":
    unittest.main()
