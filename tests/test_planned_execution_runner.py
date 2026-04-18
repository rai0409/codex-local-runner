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


class _RecordingLiveTransport:
    def __init__(
        self,
        *,
        status_by_pr_id: dict[str, str] | None = None,
        verify_status_by_pr_id: dict[str, str] | None = None,
    ) -> None:
        self.status_by_pr_id = dict(status_by_pr_id or {})
        self.verify_status_by_pr_id = dict(verify_status_by_pr_id or {})
        self.launch_order: list[str] = []
        self.runs: dict[str, dict[str, object]] = {}

    def launch_job(self, **kwargs):  # type: ignore[override]
        pr_id = str(kwargs.get("pr_id", "")).strip()
        job_id = str(kwargs.get("job_id", "")).strip()
        run_id = f"{job_id}:{pr_id}:live"
        self.launch_order.append(pr_id)

        status = self.status_by_pr_id.get(pr_id, "completed")
        if status not in {"completed", "failed", "timed_out", "not_started", "running"}:
            status = "failed"
        verify_status = self.verify_status_by_pr_id.get(pr_id, "passed")
        if verify_status not in {"passed", "failed", "not_run"}:
            verify_status = "not_run"

        verify_reason = (
            "validation_passed"
            if verify_status == "passed"
            else "validation_failed" if verify_status == "failed" else "validation_not_run"
        )
        failure_type = None
        failure_message = None
        if status == "failed":
            failure_type = "execution_failure"
            failure_message = "mocked execution failure"
        elif status == "timed_out":
            failure_type = "transport_timeout"
            failure_message = "mocked timeout"
        elif status == "not_started":
            failure_type = "transport_submission_failure"
            failure_message = "mocked submission failure"
        elif verify_status == "failed":
            failure_type = "evaluation_failure"
            failure_message = "mocked verify failure"
        elif verify_status == "not_run":
            failure_type = "missing_signal"
            failure_message = "mocked verify missing"

        run_payload = {
            "run_id": run_id,
            "status": status,
            "attempt_count": 1,
            "started_at": "2026-04-18T00:00:00",
            "finished_at": "2026-04-18T00:00:01",
            "stdout_path": f"/tmp/{pr_id}_stdout.txt",
            "stderr_path": f"/tmp/{pr_id}_stderr.txt",
            "verify": {
                "status": verify_status,
                "commands": ["python3 -m unittest tests.test_planned_execution_runner -v"],
                "reason": verify_reason,
            },
            "changed_files": [],
            "additions": 1,
            "deletions": 0,
            "generated_patch_summary": "mocked live execution",
            "failure_type": failure_type,
            "failure_message": failure_message,
            "cost": {"tokens_input": 100, "tokens_output": 50},
            "artifacts": [],
        }
        self.runs[run_id] = run_payload
        return {"run_id": run_id, "status": status, "dry_run": False}

    def poll_status(self, **kwargs):  # type: ignore[override]
        run_id = str(kwargs.get("run_id", ""))
        payload = dict(self.runs[run_id])
        payload["dry_run"] = False
        return payload

    def collect_artifacts(self, **kwargs):  # type: ignore[override]
        run_id = str(kwargs.get("run_id", ""))
        payload = self.runs[run_id]
        return {
            "run_id": run_id,
            "stdout_path": str(payload["stdout_path"]),
            "stderr_path": str(payload["stderr_path"]),
            "artifacts": [],
            "dry_run": False,
        }


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
                retry_context={
                    "prior_attempt_count": 0,
                    "prior_retry_class": None,
                    "missing_signal_count": 0,
                    "retry_budget_remaining": 1,
                },
            )
            order_a = list(transport.launch_order)

            transport_b = _RecordingDryRunTransport()
            runner_b = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport_b))
            manifest_b = runner_b.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
                retry_context={
                    "prior_attempt_count": 0,
                    "prior_retry_class": None,
                    "missing_signal_count": 0,
                    "retry_budget_remaining": 1,
                },
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
            self.assertTrue((run_root / "next_action.json").exists())
            self.assertTrue((run_root / "action_handoff.json").exists())

            for entry in manifest["pr_units"]:
                pr_id = entry["pr_id"]
                unit_dir = run_root / pr_id
                self.assertTrue(unit_dir.exists())
                self.assertTrue((unit_dir / "compiled_prompt.md").exists())
                self.assertTrue((unit_dir / "bounded_step_contract.json").exists())
                self.assertTrue((unit_dir / "pr_implementation_prompt_contract.json").exists())
                self.assertTrue((unit_dir / "unit_progression.json").exists())
                self.assertTrue((unit_dir / "result.json").exists())
                self.assertTrue((unit_dir / "execution_receipt.json").exists())

                result_payload = json.loads((unit_dir / "result.json").read_text(encoding="utf-8"))
                receipt_payload = json.loads((unit_dir / "execution_receipt.json").read_text(encoding="utf-8"))
                prompt_text = (unit_dir / "compiled_prompt.md").read_text(encoding="utf-8")
                bounded_step_contract = json.loads(
                    (unit_dir / "bounded_step_contract.json").read_text(encoding="utf-8")
                )
                prompt_contract = json.loads(
                    (unit_dir / "pr_implementation_prompt_contract.json").read_text(encoding="utf-8")
                )
                unit_progression_payload = json.loads(
                    (unit_dir / "unit_progression.json").read_text(encoding="utf-8")
                )

                self.assertEqual(result_payload["pr_id"], pr_id)
                self.assertEqual(receipt_payload["pr_id"], pr_id)
                self.assertIn(f"Execute exactly one PR slice: {pr_id}", prompt_text)
                self.assertEqual(bounded_step_contract["step_id"], pr_id)
                self.assertEqual(prompt_contract["source_step_id"], pr_id)
                self.assertEqual(unit_progression_payload["pr_id"], pr_id)
                self.assertIn("contract_handoff", unit_progression_payload)
                self.assertEqual(
                    prompt_contract["progression_metadata"]["planned_step_id"],
                    pr_id,
                )

            decision_payload = json.loads((run_root / "next_action.json").read_text(encoding="utf-8"))
            handoff_payload = json.loads((run_root / "action_handoff.json").read_text(encoding="utf-8"))
            self.assertEqual(decision_payload["job_id"], manifest["job_id"])
            self.assertIn("next_action", decision_payload)
            self.assertIn("reason", decision_payload)
            self.assertIn("updated_retry_context", decision_payload)
            self.assertIn("progression_outcome", decision_payload)
            self.assertIn("progression_rule_id", decision_payload)
            self.assertEqual(handoff_payload["job_id"], manifest["job_id"])
            self.assertIn("action_consumable", handoff_payload)
            self.assertIn("handoff_created_at", handoff_payload)

    def test_launch_metadata_uses_structured_contract_surfaces(self) -> None:
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

            first = manifest["pr_units"][0]
            unit_dir = Path(first["compiled_prompt_path"]).parent
            bounded = json.loads((unit_dir / "bounded_step_contract.json").read_text(encoding="utf-8"))
            prompt_contract = json.loads(
                (unit_dir / "pr_implementation_prompt_contract.json").read_text(encoding="utf-8")
            )
            run_ids = sorted(transport._runs.keys())  # type: ignore[attr-defined]
            first_run = transport._runs[run_ids[0]]  # type: ignore[attr-defined]
            metadata = first_run["metadata"]

        self.assertEqual(metadata["planned_step_id"], bounded["step_id"])
        self.assertEqual(metadata["source_step_id"], prompt_contract["source_step_id"])
        self.assertEqual(
            metadata["strict_scope_files"],
            bounded["progression_metadata"]["strict_scope_files"],
        )
        self.assertEqual(
            metadata["validation_commands"],
            bounded["validation_expectations"],
        )

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
        self.assertIn("decision_summary", manifest)
        self.assertIn("progression_summary", manifest)
        self.assertIn("manifest_path", manifest)
        self.assertIn("next_action_path", manifest)
        self.assertIn("action_handoff_path", manifest)
        self.assertIn("retry_context_store_path", manifest)
        self.assertIn("handoff_summary", manifest)
        self.assertEqual(
            manifest["decision_summary"]["next_action"],
            "signal_recollect",
        )
        self.assertEqual(
            manifest["handoff_summary"]["next_action"],
            "signal_recollect",
        )
        self.assertEqual(manifest["progression_summary"]["final_unit_state"], "reviewed")

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

            decision_payload = json.loads(
                Path(manifest["next_action_path"]).read_text(encoding="utf-8")
            )

        self.assertEqual(manifest["run_status"], "failed")
        self.assertEqual(
            [entry["pr_id"] for entry in manifest["pr_units"]],
            [
                "project-planned-exec-pr-01",
                "project-planned-exec-pr-02",
            ],
        )
        self.assertIn(decision_payload["next_action"], {"same_prompt_retry", "escalate_to_human"})

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
            decision_payload = json.loads(
                Path(manifest["next_action_path"]).read_text(encoding="utf-8")
            )
            handoff_payload = json.loads(
                Path(manifest["action_handoff_path"]).read_text(encoding="utf-8")
            )

        self.assertEqual(result_payload["execution"]["status"], "not_started")
        self.assertEqual(result_payload["execution"]["verify"]["status"], "not_run")
        self.assertEqual(result_payload["failure_type"], "missing_signal")
        self.assertEqual(decision_payload["next_action"], "signal_recollect")
        self.assertEqual(handoff_payload["next_action"], "signal_recollect")
        self.assertFalse(decision_payload["next_action"] in {"proceed_to_pr", "proceed_to_merge"})

    def test_live_transport_path_integrates_with_controller(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"

            transport = _RecordingLiveTransport()
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=False,
                stop_on_failure=True,
            )

            decision_payload = json.loads(
                Path(manifest["next_action_path"]).read_text(encoding="utf-8")
            )
            first = manifest["pr_units"][0]
            result_payload = json.loads(Path(first["result_path"]).read_text(encoding="utf-8"))
            handoff_payload = json.loads(
                Path(manifest["action_handoff_path"]).read_text(encoding="utf-8")
            )

        self.assertEqual(manifest["run_status"], "completed")
        self.assertEqual(result_payload["execution"]["status"], "completed")
        self.assertEqual(result_payload["execution"]["verify"]["status"], "passed")
        self.assertEqual(decision_payload["next_action"], "proceed_to_pr")
        self.assertEqual(handoff_payload["next_action"], "proceed_to_pr")
        self.assertTrue(handoff_payload["action_consumable"])
        self.assertFalse(decision_payload["whether_human_required"])
        self.assertEqual(manifest["progression_summary"]["final_unit_state"], "advanced")

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

    def test_invalid_live_transport_gate_fails_non_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "out"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(self._script_path()),
                    "--artifacts-dir",
                    str(artifacts_dir),
                    "--out-dir",
                    str(out_dir),
                    "--transport-mode",
                    "live",
                    "--repo-path",
                    str(self._repo_root()),
                    "--json",
                ],
                capture_output=True,
                text=True,
                cwd=self._repo_root(),
            )

        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("--enable-live-transport", proc.stderr)

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
                self.assertIn("bounded_step_contract_path", entry)
                self.assertIn("pr_implementation_prompt_contract_path", entry)
                self.assertIn("result_path", entry)
                self.assertIn("receipt_path", entry)
                self.assertIn("unit_progression_path", entry)
                self.assertIn("unit_progression_state", entry)
                self.assertIn("status", entry)
                self.assertTrue(Path(entry["compiled_prompt_path"]).exists())
                self.assertTrue(Path(entry["bounded_step_contract_path"]).exists())
                self.assertTrue(Path(entry["pr_implementation_prompt_contract_path"]).exists())
                self.assertTrue(Path(entry["result_path"]).exists())
                self.assertTrue(Path(entry["receipt_path"]).exists())
                self.assertTrue(Path(entry["unit_progression_path"]).exists())
            self.assertTrue(Path(manifest["action_handoff_path"]).exists())

    def test_unit_progression_checkpoint_surface_is_explicit_and_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"

            transport = _RecordingLiveTransport()
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=False,
                stop_on_failure=True,
            )
            first = manifest["pr_units"][0]
            progression = json.loads(Path(first["unit_progression_path"]).read_text(encoding="utf-8"))
            checkpoints = progression["checkpoints"]
            states = [entry["state"] for entry in checkpoints]

        self.assertEqual(progression["schema_version"], "v1")
        self.assertEqual(states[:4], ["planned", "prompt_ready", "execution_ready", "execution_completed"])
        self.assertIn("reviewed", states)
        self.assertEqual(progression["current_state"], "advanced")

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

    def test_one_run_one_decision_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"

            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=_RecordingDryRunTransport()))
            manifest_a = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
                retry_context={
                    "prior_attempt_count": 0,
                    "prior_retry_class": None,
                    "missing_signal_count": 0,
                    "retry_budget_remaining": 1,
                },
            )
            decision_a = json.loads(Path(manifest_a["next_action_path"]).read_text(encoding="utf-8"))
            handoff_a = json.loads(Path(manifest_a["action_handoff_path"]).read_text(encoding="utf-8"))

            runner_b = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=_RecordingDryRunTransport()))
            manifest_b = runner_b.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
                retry_context={
                    "prior_attempt_count": 0,
                    "prior_retry_class": None,
                    "missing_signal_count": 0,
                    "retry_budget_remaining": 1,
                },
            )
            decision_b = json.loads(Path(manifest_b["next_action_path"]).read_text(encoding="utf-8"))
            handoff_b = json.loads(Path(manifest_b["action_handoff_path"]).read_text(encoding="utf-8"))

        self.assertEqual(decision_a["next_action"], decision_b["next_action"])
        self.assertEqual(decision_a["reason"], decision_b["reason"])
        self.assertEqual(decision_a["updated_retry_context"], decision_b["updated_retry_context"])
        self.assertEqual(handoff_a["next_action"], handoff_b["next_action"])
        self.assertEqual(handoff_a["updated_retry_context"], handoff_b["updated_retry_context"])
        self.assertEqual(handoff_a["action_consumable"], handoff_b["action_consumable"])

    def test_retry_context_continuity_across_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"

            failing_transport_a = _RecordingDryRunTransport(
                status_by_pr_id={"project-planned-exec-pr-01": "failed"}
            )
            runner_a = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=failing_transport_a))
            manifest_a = runner_a.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
            )
            handoff_a = json.loads(Path(manifest_a["action_handoff_path"]).read_text(encoding="utf-8"))

            failing_transport_b = _RecordingDryRunTransport(
                status_by_pr_id={"project-planned-exec-pr-01": "failed"}
            )
            runner_b = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=failing_transport_b))
            manifest_b = runner_b.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
            )
            handoff_b = json.loads(Path(manifest_b["action_handoff_path"]).read_text(encoding="utf-8"))
            run_root = out_dir / manifest_b["job_id"]
            handoff_files = sorted(run_root.glob("action_handoff*.json"))

        self.assertEqual(handoff_a["next_action"], "same_prompt_retry")
        self.assertEqual(handoff_b["next_action"], "escalate_to_human")
        self.assertEqual(len(handoff_files), 1)


if __name__ == "__main__":
    unittest.main()
