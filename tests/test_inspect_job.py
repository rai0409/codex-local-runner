from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from orchestrator.ledger import record_execution_target
from orchestrator.ledger import record_job_evaluation
from orchestrator.ledger import record_machine_review_payload_path
from orchestrator.ledger import record_merge_execution_outcome
from orchestrator.ledger import record_rollback_execution_outcome
from orchestrator.ledger import record_rollback_traceability_for_candidate


class InspectJobCliTests(unittest.TestCase):
    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _script_path(self) -> Path:
        return self._repo_root() / "scripts" / "inspect_job.py"

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self._script_path()), *args],
            capture_output=True,
            text=True,
            cwd=self._repo_root(),
        )

    def _seed_job(
        self,
        *,
        db_path: Path,
        job_id: str,
        created_at: str | None = "2026-04-12T00:00:00+00:00",
        rubric_path: str | None = None,
        merge_gate_path: str | None = None,
        result_path_override: str | None = None,
    ) -> None:
        request_path = db_path.parent / f"{job_id}_request.json"
        result_path = (
            Path(result_path_override)
            if isinstance(result_path_override, str) and result_path_override.strip()
            else db_path.parent / f"{job_id}_result.json"
        )
        request_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        request_path.write_text("{}", encoding="utf-8")
        result_path.write_text("{}", encoding="utf-8")
        record_job_evaluation(
            db_path=db_path,
            job_id=job_id,
            repo="codex-local-runner",
            task_type="orchestration",
            provider="codex_cli",
            accepted_status="accepted",
            declared_category="docs_only",
            observed_category="docs_only",
            merge_eligible=True,
            merge_gate_passed=True,
            created_at=created_at,
            request_path=str(request_path),
            result_path=str(result_path),
            rubric_path=rubric_path,
            merge_gate_path=merge_gate_path,
        )

    def test_inspect_by_job_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "state" / "jobs.db"
            self._seed_job(db_path=db_path, job_id="job-by-id")

            proc = self._run(["--job-id", "job-by-id", "--db-path", str(db_path)])

        self.assertEqual(proc.returncode, 0)
        self.assertIn("job_id: job-by-id", proc.stdout)
        self.assertIn("accepted_status: accepted", proc.stdout)
        self.assertIn("request_path:", proc.stdout)
        self.assertEqual(proc.stderr, "")

    def test_inspect_latest_job(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "state" / "jobs.db"
            self._seed_job(
                db_path=db_path,
                job_id="job-older",
                created_at="2026-04-11T00:00:00+00:00",
            )
            self._seed_job(
                db_path=db_path,
                job_id="job-latest",
                created_at="2026-04-12T00:00:00+00:00",
            )

            proc = self._run(["--latest", "--db-path", str(db_path)])

        self.assertEqual(proc.returncode, 0)
        self.assertIn("job_id: job-latest", proc.stdout)

    def test_json_output_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "state" / "jobs.db"
            self._seed_job(db_path=db_path, job_id="job-json")

            proc = self._run(["--job-id", "job-json", "--db-path", str(db_path), "--json"])

        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["job_id"], "job-json")
        self.assertIn("paths", payload)
        self.assertIn("fail_reasons", payload)
        self.assertIn("replan_input", payload)
        self.assertIn("rollback_trace", payload)
        self.assertIn("rollback_execution", payload)
        self.assertIn("rubric", payload["paths"])
        self.assertIn("merge_gate", payload["paths"])
        self.assertFalse(payload["rollback_trace"]["recorded"])
        self.assertFalse(payload["rollback_execution"]["recorded"])
        self.assertIn("machine_review", payload)
        self.assertIn("retry_metadata", payload["machine_review"])
        self.assertIn("advisory", payload["machine_review"])
        self.assertIn("execution_bridge", payload["machine_review"])
        self.assertIn("mode_visibility", payload["machine_review"])
        self.assertEqual(payload["machine_review"]["advisory"]["display_recommendation"], None)
        self.assertEqual(payload["machine_review"]["advisory"]["decision_confidence"], None)
        self.assertEqual(payload["machine_review"]["advisory"]["operator_attention_flags"], [])
        self.assertFalse(payload["machine_review"]["advisory"]["execution_allowed"])
        self.assertFalse(
            payload["machine_review"]["execution_bridge"]["eligible_for_bounded_execution"]
        )
        self.assertEqual(payload["machine_review"]["execution_bridge"]["eligibility_basis"], [])
        self.assertEqual(
            payload["machine_review"]["execution_bridge"]["eligibility_blockers"],
            ["explicit_operator_gate_required", "execution_not_implemented"],
        )
        self.assertTrue(
            payload["machine_review"]["execution_bridge"][
                "requires_explicit_operator_decision"
            ]
        )
        self.assertEqual(
            payload["machine_review"]["mode_visibility"]["current_mode"],
            "manual_review_only",
        )
        self.assertIsNone(
            payload["machine_review"]["mode_visibility"]["next_possible_mode"]
        )
        self.assertEqual(
            payload["machine_review"]["mode_visibility"]["mode_basis"],
            ["explicit_operator_decision_required"],
        )
        self.assertEqual(
            payload["machine_review"]["mode_visibility"]["mode_blockers"],
            ["explicit_operator_gate_required", "execution_not_implemented"],
        )
        self.assertIsNone(payload["replan_input"]["failure_type"])
        self.assertEqual(payload["replan_input"]["primary_fail_reasons"], [])

    def test_inspect_surfaces_lifecycle_artifacts_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            run_root = tmp_root / "runs" / "job-lifecycle"
            unit_dir = run_root / "pr-01"
            unit_dir.mkdir(parents=True, exist_ok=True)
            result_path = unit_dir / "result.json"
            result_path.write_text("{}", encoding="utf-8")
            (unit_dir / "checkpoint_decision.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "unit_id": "pr-01",
                        "checkpoint_stage": "post_review",
                        "decision": "global_stop_recommended",
                        "rule_id": "checkpoint_global_stop_recommended",
                        "summary": "checkpoint requested stop",
                        "blocking_reasons": ["global_stop_required"],
                        "required_signals": ["global_stop_required"],
                        "recommended_next_action": "escalate_to_human",
                        "manual_intervention_required": True,
                        "global_stop_recommended": True,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (unit_dir / "commit_decision.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "unit_id": "pr-01",
                        "decision": "blocked",
                        "rule_id": "commit_blocked_review_failed",
                        "summary": "blocked",
                        "blocking_reasons": ["review_failed"],
                        "required_signals": ["review_passed"],
                        "recommended_next_action": "signal_recollect",
                        "readiness_status": "blocked",
                        "readiness_next_action": "resolve_blockers",
                        "automation_eligible": False,
                        "manual_intervention_required": False,
                        "unresolved_blockers": ["review_failed"],
                        "prerequisites_satisfied": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (unit_dir / "merge_decision.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "unit_id": "pr-01",
                        "decision": "manual_required",
                        "rule_id": "merge_manual_review_required",
                        "summary": "manual",
                        "blocking_reasons": ["manual_review_required"],
                        "required_signals": ["manual_review_required"],
                        "recommended_next_action": "escalate_to_human",
                        "readiness_status": "manual_required",
                        "readiness_next_action": "await_manual_review",
                        "automation_eligible": False,
                        "manual_intervention_required": True,
                        "unresolved_blockers": ["manual_review_required"],
                        "prerequisites_satisfied": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (unit_dir / "rollback_decision.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "unit_id": "pr-01",
                        "decision": "required",
                        "rule_id": "rollback_required_by_progression",
                        "summary": "required",
                        "blocking_reasons": [],
                        "required_signals": ["rollback_required"],
                        "recommended_next_action": "rollback_required",
                        "readiness_status": "awaiting_prerequisites",
                        "readiness_next_action": "resolve_blockers",
                        "automation_eligible": False,
                        "manual_intervention_required": True,
                        "unresolved_blockers": ["run_manual_intervention_required"],
                        "prerequisites_satisfied": True,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (unit_dir / "commit_execution.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "unit_id": "pr-01",
                        "execution_type": "git_commit",
                        "status": "failed",
                        "summary": "commit execution failed during git commit",
                        "started_at": "2026-04-18T01:00:00",
                        "finished_at": "2026-04-18T01:00:01",
                        "commit_sha": "",
                        "command_summary": {"git_commit_rc": 1},
                        "failure_reason": "git_commit_failed",
                        "manual_intervention_required": True,
                        "blocking_reasons": ["git_commit_failed"],
                        "attempted": True,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (unit_dir / "push_execution.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "unit_id": "pr-01",
                        "execution_type": "git_push",
                        "status": "succeeded",
                        "summary": "push succeeded",
                        "started_at": "2026-04-18T01:00:02",
                        "finished_at": "2026-04-18T01:00:03",
                        "branch_name": "feature",
                        "remote_name": "origin",
                        "base_branch": "main",
                        "head_branch": "feature",
                        "pr_number": None,
                        "merge_commit_sha": "",
                        "command_summary": {"git_push_rc": 0},
                        "failure_reason": "",
                        "manual_intervention_required": False,
                        "blocking_reasons": [],
                        "attempted": True,
                        "remote_state_status": "non_fast_forward_risk",
                        "remote_state_blocked": True,
                        "remote_state_blocked_reason": "remote_non_fast_forward_risk",
                        "remote_state_missing_or_ambiguous": False,
                        "upstream_tracking_status": "tracked",
                        "remote_divergence_status": "non_fast_forward_risk",
                        "existing_pr_status": "unknown",
                        "pr_creation_state_status": "unknown",
                        "mergeability_status": "unknown",
                        "merge_requirements_status": "unknown",
                        "remote_github_status": "blocked",
                        "remote_github_blocked": True,
                        "remote_github_blocked_reason": "remote_non_fast_forward_risk",
                        "remote_github_blocked_reasons": ["remote_non_fast_forward_risk"],
                        "remote_github_missing_or_ambiguous": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (unit_dir / "pr_execution.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "unit_id": "pr-01",
                        "execution_type": "github_pr_create",
                        "status": "succeeded",
                        "summary": "pr created",
                        "started_at": "2026-04-18T01:00:04",
                        "finished_at": "2026-04-18T01:00:05",
                        "branch_name": "feature",
                        "remote_name": "origin",
                        "base_branch": "main",
                        "head_branch": "feature",
                        "pr_number": 123,
                        "pr_url": "https://example.local/pr/123",
                        "merge_commit_sha": "",
                        "command_summary": {"create_pr_status": "success"},
                        "failure_reason": "",
                        "manual_intervention_required": False,
                        "blocking_reasons": [],
                        "attempted": True,
                        "existing_pr_status": "existing_open",
                        "pr_creation_state_status": "blocked_existing_pr",
                        "remote_state_status": "blocked",
                        "remote_state_blocked": True,
                        "remote_state_blocked_reason": "existing_open_pr_detected",
                        "remote_state_missing_or_ambiguous": False,
                        "remote_github_status": "blocked",
                        "remote_github_blocked": True,
                        "remote_github_blocked_reason": "existing_open_pr_detected",
                        "remote_github_blocked_reasons": ["existing_open_pr_detected"],
                        "remote_github_missing_or_ambiguous": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (unit_dir / "merge_execution.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "unit_id": "pr-01",
                        "execution_type": "github_pr_merge",
                        "status": "failed",
                        "summary": "merge failed",
                        "started_at": "2026-04-18T01:00:06",
                        "finished_at": "2026-04-18T01:00:07",
                        "branch_name": "feature",
                        "remote_name": "origin",
                        "base_branch": "main",
                        "head_branch": "feature",
                        "pr_number": 123,
                        "merge_commit_sha": "",
                        "command_summary": {"merge_status": "api_failure"},
                        "failure_reason": "merge_execution_failed:api_failure",
                        "manual_intervention_required": True,
                        "blocking_reasons": ["merge_execution_failed:api_failure"],
                        "attempted": True,
                        "mergeability_status": "unknown",
                        "merge_requirements_status": "unsatisfied",
                        "required_checks_status": "unsatisfied",
                        "review_state_status": "unsatisfied",
                        "branch_protection_status": "unsatisfied",
                        "remote_state_status": "blocked",
                        "remote_state_blocked": True,
                        "remote_state_blocked_reason": "required_checks_unsatisfied",
                        "remote_state_missing_or_ambiguous": True,
                        "remote_github_status": "blocked",
                        "remote_github_blocked": True,
                        "remote_github_blocked_reason": "required_checks_unsatisfied",
                        "remote_github_blocked_reasons": ["required_checks_unsatisfied"],
                        "remote_github_missing_or_ambiguous": True,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (unit_dir / "rollback_execution.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "unit_id": "pr-01",
                        "execution_type": "rollback_execution",
                        "rollback_mode": "pushed_or_pr_open",
                        "status": "blocked",
                        "summary": "rollback blocked for pushed/pr-open mode",
                        "started_at": "",
                        "finished_at": "2026-04-18T01:00:08",
                        "trigger_reason": "rollback_required",
                        "source_execution_state_summary": {
                            "mode": "pushed_or_pr_open",
                        },
                        "resulting_commit_sha": "",
                        "resulting_pr_state": "manual_followup_required",
                        "resulting_branch_state": {},
                        "command_summary": {},
                        "failure_reason": "rollback_mode_pushed_or_pr_open_requires_manual_path",
                        "manual_intervention_required": True,
                        "replan_required": True,
                        "automatic_continuation_blocked": True,
                        "blocking_reasons": ["rollback_mode_pushed_or_pr_open_requires_manual_path"],
                        "attempted": False,
                        "rollback_aftermath_status": "validation_failed",
                        "rollback_aftermath_blocked": True,
                        "rollback_aftermath_blocked_reason": "rollback_validation_failed",
                        "rollback_aftermath_blocked_reasons": [
                            "rollback_validation_failed",
                            "rollback_remote_followup_required",
                        ],
                        "rollback_aftermath_missing_or_ambiguous": True,
                        "rollback_validation_status": "failed",
                        "rollback_manual_followup_required": True,
                        "rollback_remote_followup_required": True,
                        "rollback_post_validation_status": "failed",
                        "rollback_remote_state_status": "followup_required",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (run_root / "run_state.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "run_id": "job-lifecycle",
                        "state": "paused",
                        "orchestration_state": "global_stop_pending",
                        "summary": "manual gate",
                        "units_total": 1,
                        "units_completed": 0,
                        "units_blocked": 1,
                        "units_failed": 0,
                        "units_pending": 0,
                        "global_stop": True,
                        "global_stop_reason": "manual gate",
                        "continue_allowed": False,
                        "run_paused": True,
                        "manual_intervention_required": True,
                        "rollback_evaluation_pending": False,
                        "global_stop_recommended": True,
                        "next_run_action": "hold_for_global_stop",
                        "loop_state": "manual_intervention_required",
                        "next_safe_action": "require_manual_intervention",
                        "loop_blocked_reason": "global_stop_recommended",
                        "loop_blocked_reasons": ["global_stop_recommended"],
                        "resumable": True,
                        "terminal": False,
                        "loop_manual_intervention_required": True,
                        "loop_replan_required": True,
                        "rollback_completed": False,
                        "delivery_completed": False,
                        "loop_allowed_actions": [
                            "execute_commit",
                            "execute_merge",
                            "execute_pr_creation",
                            "execute_push",
                            "execute_rollback",
                            "pause",
                            "require_manual_intervention",
                            "require_replanning",
                            "stop_terminal_failure",
                            "stop_terminal_success",
                        ],
                        "unit_blocked": True,
                        "latest_unit_id": "pr-01",
                        "allowed_transitions": ["decision_in_progress"],
                        "orchestration_allowed_transitions": ["checkpoint_evaluation_in_progress"],
                        "readiness_summary": {
                            "commit": {
                                "ready": 0,
                                "not_ready": 0,
                                "manual_required": 0,
                                "blocked": 1,
                                "awaiting_prerequisites": 0,
                            },
                            "merge": {
                                "ready": 0,
                                "not_ready": 0,
                                "manual_required": 1,
                                "blocked": 0,
                                "awaiting_prerequisites": 0,
                            },
                            "rollback": {
                                "ready": 0,
                                "not_ready": 0,
                                "manual_required": 0,
                                "blocked": 0,
                                "awaiting_prerequisites": 1,
                            },
                        },
                        "readiness_blocked": True,
                        "readiness_manual_required": True,
                        "readiness_awaiting_prerequisites": True,
                        "commit_execution_summary": {
                            "succeeded": 0,
                            "failed": 1,
                            "blocked": 0,
                        },
                        "commit_execution_executed": False,
                        "commit_execution_pending": False,
                        "commit_execution_failed": True,
                        "commit_execution_manual_intervention_required": True,
                        "push_execution_summary": {"succeeded": 1, "failed": 0, "blocked": 0},
                        "pr_execution_summary": {"succeeded": 1, "failed": 0, "blocked": 0},
                        "merge_execution_summary": {"succeeded": 0, "failed": 1, "blocked": 0},
                        "push_execution_succeeded": True,
                        "pr_execution_succeeded": True,
                        "merge_execution_succeeded": False,
                        "push_execution_pending": False,
                        "pr_execution_pending": False,
                        "merge_execution_pending": False,
                        "push_execution_failed": False,
                        "pr_execution_failed": False,
                        "merge_execution_failed": True,
                        "delivery_execution_manual_intervention_required": True,
                        "rollback_execution_summary": {"succeeded": 0, "failed": 0, "blocked": 1},
                        "rollback_execution_attempted": False,
                        "rollback_execution_succeeded": False,
                        "rollback_execution_pending": True,
                        "rollback_execution_failed": False,
                        "rollback_execution_manual_intervention_required": True,
                        "rollback_replan_required": True,
                        "rollback_automatic_continuation_blocked": True,
                        "rollback_aftermath_summary": {
                            "completed_safe": 0,
                            "completed_manual_followup_required": 0,
                            "blocked": 0,
                            "incomplete": 0,
                            "ambiguous": 0,
                            "validation_failed": 1,
                            "remote_followup_required": 0,
                        },
                        "rollback_aftermath_status": "validation_failed",
                        "rollback_aftermath_blocked": True,
                        "rollback_aftermath_manual_required": True,
                        "rollback_aftermath_missing_or_ambiguous": True,
                        "rollback_aftermath_blocked_reason": "rollback_validation_failed",
                        "rollback_aftermath_blocked_reasons": [
                            "rollback_validation_failed",
                            "rollback_remote_followup_required",
                        ],
                        "rollback_remote_followup_required": True,
                        "rollback_manual_followup_required": True,
                        "rollback_validation_failed": True,
                        "remote_github_summary": {
                            "push": {"blocked": 1, "manual_required": 1, "missing_or_ambiguous": 0},
                            "pr": {"blocked": 1, "manual_required": 1, "missing_or_ambiguous": 0},
                            "merge": {"blocked": 1, "manual_required": 1, "missing_or_ambiguous": 1},
                        },
                        "remote_github_blocked": True,
                        "remote_github_manual_required": True,
                        "remote_github_missing_or_ambiguous": True,
                        "remote_github_blocked_reason": "required_checks_unsatisfied",
                        "remote_github_blocked_reasons": [
                            "remote_non_fast_forward_risk",
                            "existing_open_pr_detected",
                            "required_checks_unsatisfied",
                        ],
                        "policy_status": "manual_only",
                        "policy_blocked": True,
                        "policy_manual_required": True,
                        "policy_replan_required": True,
                        "policy_resume_allowed": False,
                        "policy_terminal": False,
                        "policy_blocked_reason": "rollback_validation_failed",
                        "policy_blocked_reasons": [
                            "rollback_validation_failed",
                            "existing_open_pr_detected",
                        ],
                        "policy_primary_blocker_class": "replan_required",
                        "policy_primary_action": "rollback_required",
                        "policy_allowed_actions": [
                            "inspect",
                            "signal_recollect",
                            "escalate_to_human",
                            "roadmap_replan",
                        ],
                        "policy_disallowed_actions": [
                            "proceed_to_commit",
                            "proceed_to_pr",
                            "proceed_to_merge",
                            "rollback_required",
                        ],
                        "policy_manual_actions": [
                            "inspect",
                            "escalate_to_human",
                            "roadmap_replan",
                        ],
                        "policy_resumable_reason": "terminal_or_replan_or_manual_gate",
                        "objective_contract_present": True,
                        "objective_id": "objective-job-lifecycle",
                        "objective_summary": "Safely complete delivery",
                        "objective_type": "implementation",
                        "requested_outcome": "safe closure with objective evidence",
                        "objective_acceptance_status": "partially_defined",
                        "objective_required_artifacts_status": "defined",
                        "objective_scope_status": "clear",
                        "objective_contract_status": "underspecified",
                        "objective_contract_blocked_reason": "acceptance_partially_defined",
                        "completion_contract_present": True,
                        "completion_status": "replan_before_closure",
                        "done_status": "not_done",
                        "safe_closure_status": "not_safely_closed",
                        "completion_evidence_status": "partial",
                        "completion_blocked_reason": "replan_before_closure",
                        "completion_manual_required": True,
                        "completion_replan_required": True,
                        "completion_lifecycle_alignment_status": "partially_aligned",
                        "approval_transport_present": True,
                        "approval_status": "deferred",
                        "approval_decision": "defer",
                        "approval_scope": "current_completion_state",
                        "approved_action": "hold_for_manual_review",
                        "approval_required": True,
                        "approval_transport_status": "non_actionable",
                        "approval_compatibility_status": "partially_compatible",
                        "approval_blocked_reason": "approval_scope_partial",
                        "reconcile_contract_present": True,
                        "reconcile_status": "blocked",
                        "reconcile_decision": "request_replan",
                        "reconcile_alignment_status": "cross_surface_partial",
                        "reconcile_primary_mismatch": "objective_underspecified",
                        "reconcile_blocked_reason": "objective_underspecified",
                        "reconcile_waiting_on_truth": False,
                        "reconcile_manual_required": True,
                        "reconcile_replan_required": True,
                        "repair_suggestion_contract_present": True,
                        "repair_suggestion_status": "suggested",
                        "repair_suggestion_decision": "request_replan",
                        "repair_suggestion_class": "objective_gap",
                        "repair_suggestion_priority": "high",
                        "repair_suggestion_confidence": "partial",
                        "repair_primary_reason": "objective_underspecified",
                        "repair_manual_required": True,
                        "repair_replan_required": True,
                        "repair_truth_gathering_required": False,
                        "repair_plan_transport_present": True,
                        "repair_plan_status": "available",
                        "repair_plan_decision": "prepare_replan_plan",
                        "repair_plan_class": "replan_plan",
                        "repair_plan_priority": "high",
                        "repair_plan_confidence": "partial",
                        "repair_plan_target_surface": "objective",
                        "repair_plan_candidate_action": "request_replan",
                        "repair_plan_primary_reason": "replan_required",
                        "repair_plan_manual_required": True,
                        "repair_plan_replan_required": True,
                        "repair_plan_truth_gathering_required": False,
                        "repair_approval_binding_present": True,
                        "repair_approval_binding_status": "missing",
                        "repair_approval_binding_decision": "hold_unbound",
                        "repair_approval_binding_scope": "replan_only",
                        "repair_approval_binding_validity": "insufficient_truth",
                        "repair_approval_binding_compatibility_status": "insufficient_truth",
                        "repair_approval_binding_primary_reason": "missing_approval",
                        "repair_approval_binding_manual_required": True,
                        "repair_approval_binding_replan_required": True,
                        "repair_approval_binding_truth_gathering_required": False,
                        "execution_authorization_gate_present": True,
                        "execution_authorization_status": "pending",
                        "execution_authorization_decision": "request_replan",
                        "execution_authorization_scope": "replan_only",
                        "execution_authorization_validity": "insufficient_truth",
                        "execution_authorization_confidence": "partial",
                        "execution_authorization_primary_reason": "missing_binding",
                        "execution_authorization_manual_required": True,
                        "execution_authorization_replan_required": True,
                        "execution_authorization_truth_gathering_required": False,
                        "bounded_execution_bridge_present": True,
                        "bounded_execution_status": "blocked",
                        "bounded_execution_decision": "request_replan",
                        "bounded_execution_scope": "replan_only",
                        "bounded_execution_validity": "insufficient_truth",
                        "bounded_execution_confidence": "conservative_low",
                        "bounded_execution_primary_reason": "authorization_not_eligible",
                        "bounded_execution_manual_required": True,
                        "bounded_execution_replan_required": True,
                        "bounded_execution_truth_gathering_required": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (run_root / "objective_contract.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "run_id": "job-lifecycle",
                        "objective_id": "objective-job-lifecycle",
                        "objective_summary": "Safely complete delivery",
                        "objective_type": "implementation",
                        "requested_outcome": "safe closure with objective evidence",
                        "in_scope": ["scripts/inspect_job.py"],
                        "out_of_scope": ["automation/control/next_action_controller.py"],
                        "acceptance_criteria": [
                            {
                                "criterion_id": "criterion_001",
                                "kind": "acceptance_criterion",
                                "status": "defined",
                                "text": "Objective artifact is visible in inspect output",
                            },
                            {
                                "criterion_id": "criterion_002",
                                "kind": "unknown",
                                "status": "undefined",
                                "text": "",
                            },
                        ],
                        "required_artifacts": ["run_state.json", "next_action.json"],
                        "forbidden_outcomes": ["no-broad-refactor"],
                        "target_repo": "codex-local-runner",
                        "target_branch": "main",
                        "requested_risk_tier": "conservative",
                        "objective_status": "underspecified",
                        "objective_source_status": "structured_partial",
                        "acceptance_status": "partially_defined",
                        "scope_status": "clear",
                        "required_artifacts_status": "defined",
                        "objective_blocked_reason": "acceptance_partially_defined",
                        "objective_blocked_reasons": ["acceptance_partially_defined"],
                        "source_priority_used": "priority_1",
                        "structured_sources_present": ["project_brief.objective"],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (run_root / "completion_contract.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "run_id": "job-lifecycle",
                        "objective_id": "objective-job-lifecycle",
                        "completion_status": "replan_before_closure",
                        "done_status": "not_done",
                        "safe_closure_status": "not_safely_closed",
                        "done_definition_ref": "objective_contract.json#objective_status,acceptance_status",
                        "safe_closure_definition_ref": "run_state.json#lifecycle_closure_status,lifecycle_safely_closed",
                        "required_evidence": [
                            "objective_contract.objective_status",
                            "objective_contract.acceptance_status",
                            "run_state.lifecycle_closure_status",
                        ],
                        "missing_evidence": ["objective_contract.objective_status"],
                        "closure_decision": "replan",
                        "closure_reason": "replan_required_before_closure",
                        "completion_blocked_reason": "replan_before_closure",
                        "completion_blocked_reasons": [
                            "objective_underspecified",
                            "acceptance_partially_defined",
                            "replan_before_closure",
                        ],
                        "completion_manual_required": True,
                        "completion_replan_required": True,
                        "execution_complete_not_accepted": True,
                        "rollback_complete_not_closed": False,
                        "delivery_complete_waiting_external_truth": False,
                        "lifecycle_alignment_status": "partially_aligned",
                        "lifecycle_closure_status": "stopped_replan_required",
                        "completion_evidence_status": "partial",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (run_root / "approval_transport.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "run_id": "job-lifecycle",
                        "objective_id": "objective-job-lifecycle",
                        "completion_status": "replan_before_closure",
                        "approval_status": "deferred",
                        "approval_decision": "defer",
                        "approval_scope": "current_completion_state",
                        "approved_action": "hold_for_manual_review",
                        "approval_reason": "waiting for clarified scope",
                        "approval_notes": "",
                        "approval_requested": True,
                        "approval_required": True,
                        "approval_present": True,
                        "approval_actor": "operator",
                        "approval_recorded_at": "2026-04-19T10:00:00+00:00",
                        "approval_expires_at": "",
                        "approval_compatibility_status": "partially_compatible",
                        "approval_blocked_reason": "approval_scope_partial",
                        "approval_blocked_reasons": ["approval_scope_partial", "approval_non_actionable"],
                        "approval_superseded": False,
                        "approval_stale": False,
                        "approval_transport_status": "non_actionable",
                        "supporting_compact_truth_refs": [
                            "run_state.next_safe_action",
                            "run_state.policy_primary_action",
                            "run_state.lifecycle_closure_status",
                            "run_state.policy_status",
                            "completion_contract.completion_status",
                            "objective_contract.objective_status",
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (run_root / "reconcile_contract.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "run_id": "job-lifecycle",
                        "objective_id": "objective-job-lifecycle",
                        "reconcile_status": "blocked",
                        "reconcile_decision": "request_replan",
                        "reconcile_alignment_status": "cross_surface_partial",
                        "reconcile_primary_mismatch": "objective_underspecified",
                        "reconcile_blocked_reason": "objective_underspecified",
                        "reconcile_blocked_reasons": [
                            "objective_underspecified",
                            "replan_required",
                        ],
                        "reconcile_waiting_on_truth": False,
                        "reconcile_manual_required": True,
                        "reconcile_replan_required": True,
                        "reconcile_completion_status": "replan_before_closure",
                        "reconcile_approval_status": "deferred",
                        "reconcile_lifecycle_status": "stopped_replan_required",
                        "reconcile_objective_status": "underspecified",
                        "reconcile_transport_status": "partial",
                        "supporting_compact_truth_refs": [
                            "run_state.next_safe_action",
                            "run_state.policy_primary_action",
                            "run_state.lifecycle_closure_status",
                            "run_state.policy_status",
                            "completion_contract.completion_status",
                            "approval_transport.approval_status",
                            "approval_transport.approval_transport_status",
                            "objective_contract.objective_status",
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (run_root / "repair_suggestion_contract.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "run_id": "job-lifecycle",
                        "objective_id": "objective-job-lifecycle",
                        "repair_suggestion_status": "suggested",
                        "repair_suggestion_decision": "request_replan",
                        "repair_suggestion_class": "objective_gap",
                        "repair_suggestion_priority": "high",
                        "repair_suggestion_confidence": "partial",
                        "repair_primary_reason": "objective_underspecified",
                        "repair_reason_codes": [
                            "objective_underspecified",
                            "replan_required",
                        ],
                        "repair_manual_required": True,
                        "repair_replan_required": True,
                        "repair_truth_gathering_required": False,
                        "repair_closure_followup_required": False,
                        "repair_execution_recommended": False,
                        "repair_target_surface": "objective",
                        "repair_precondition_status": "not_satisfied",
                        "repair_reconcile_status": "blocked",
                        "repair_completion_status": "replan_before_closure",
                        "repair_approval_status": "deferred",
                        "repair_lifecycle_status": "stopped_replan_required",
                        "supporting_compact_truth_refs": [
                            "run_state.next_safe_action",
                            "run_state.policy_primary_action",
                            "run_state.lifecycle_closure_status",
                            "run_state.policy_status",
                            "completion_contract.completion_status",
                            "reconcile_contract.reconcile_status",
                            "objective_contract.objective_status",
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (run_root / "repair_plan_transport.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "run_id": "job-lifecycle",
                        "objective_id": "objective-job-lifecycle",
                        "repair_plan_status": "available",
                        "repair_plan_decision": "prepare_replan_plan",
                        "repair_plan_class": "replan_plan",
                        "repair_plan_priority": "high",
                        "repair_plan_confidence": "partial",
                        "repair_plan_target_surface": "objective",
                        "repair_plan_candidate_action": "request_replan",
                        "repair_plan_precondition_status": "partially_satisfied",
                        "repair_plan_blocked_reason": "",
                        "repair_plan_blocked_reasons": [],
                        "repair_plan_manual_required": True,
                        "repair_plan_replan_required": True,
                        "repair_plan_truth_gathering_required": False,
                        "repair_plan_closure_followup_required": False,
                        "repair_plan_execution_ready": False,
                        "repair_plan_source_status": "derived_from_repair_suggestion",
                        "repair_plan_reconcile_status": "blocked",
                        "repair_plan_suggestion_status": "suggested",
                        "repair_plan_primary_reason": "replan_required",
                        "repair_plan_reason_codes": [
                            "objective_underspecified",
                            "replan_required",
                        ],
                        "supporting_compact_truth_refs": [
                            "run_state.next_safe_action",
                            "run_state.policy_primary_action",
                            "run_state.lifecycle_closure_status",
                            "run_state.policy_status",
                            "completion_contract.completion_status",
                            "reconcile_contract.reconcile_status",
                            "repair_suggestion_contract.repair_suggestion_status",
                            "objective_contract.objective_status",
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (run_root / "repair_approval_binding.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "run_id": "job-lifecycle",
                        "objective_id": "objective-job-lifecycle",
                        "repair_plan_status": "available",
                        "approval_status": "deferred",
                        "repair_approval_binding_status": "missing",
                        "repair_approval_binding_decision": "hold_unbound",
                        "repair_approval_binding_scope": "replan_only",
                        "repair_approval_binding_validity": "insufficient_truth",
                        "repair_approval_binding_compatibility_status": "insufficient_truth",
                        "repair_approval_binding_primary_reason": "missing_approval",
                        "repair_approval_binding_reason_codes": [
                            "missing_approval",
                            "replan_required",
                        ],
                        "repair_approval_binding_blocked_reason": "missing_approval",
                        "repair_approval_binding_blocked_reasons": [
                            "missing_approval",
                            "replan_required",
                        ],
                        "repair_approval_binding_manual_required": True,
                        "repair_approval_binding_replan_required": True,
                        "repair_approval_binding_truth_gathering_required": False,
                        "repair_approval_binding_execution_authorized": False,
                        "repair_approval_binding_source_status": "derived_from_plan_and_approval",
                        "repair_approval_binding_plan_status": "available",
                        "repair_approval_binding_plan_action": "request_replan",
                        "repair_approval_binding_approval_decision": "defer",
                        "supporting_compact_truth_refs": [
                            "run_state.next_safe_action",
                            "run_state.policy_primary_action",
                            "run_state.lifecycle_closure_status",
                            "run_state.policy_status",
                            "completion_contract.completion_status",
                            "approval_transport.approval_status",
                            "approval_transport.approval_transport_status",
                            "repair_plan_transport.repair_plan_status",
                            "repair_plan_transport.repair_plan_candidate_action",
                            "repair_plan_transport.repair_plan_primary_reason",
                            "repair_suggestion_contract.repair_suggestion_status",
                            "reconcile_contract.reconcile_status",
                            "objective_contract.objective_status",
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (run_root / "execution_authorization_gate.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "run_id": "job-lifecycle",
                        "objective_id": "objective-job-lifecycle",
                        "execution_authorization_status": "pending",
                        "execution_authorization_decision": "request_replan",
                        "execution_authorization_scope": "replan_only",
                        "execution_authorization_validity": "insufficient_truth",
                        "execution_authorization_confidence": "partial",
                        "execution_authorization_primary_reason": "missing_binding",
                        "execution_authorization_reason_codes": [
                            "missing_binding",
                            "replan_required",
                        ],
                        "execution_authorization_blocked_reason": "missing_binding",
                        "execution_authorization_blocked_reasons": [
                            "missing_binding",
                            "replan_required",
                        ],
                        "execution_authorization_manual_required": True,
                        "execution_authorization_replan_required": True,
                        "execution_authorization_truth_gathering_required": False,
                        "execution_authorization_denied": False,
                        "execution_authorization_eligible": False,
                        "execution_authorization_source_status": "derived_from_binding",
                        "execution_authorization_binding_status": "missing",
                        "execution_authorization_plan_status": "available",
                        "execution_authorization_approval_status": "deferred",
                        "supporting_compact_truth_refs": [
                            "run_state.next_safe_action",
                            "run_state.policy_primary_action",
                            "run_state.lifecycle_closure_status",
                            "run_state.policy_status",
                            "completion_contract.completion_status",
                            "approval_transport.approval_status",
                            "approval_transport.approval_transport_status",
                            "repair_plan_transport.repair_plan_status",
                            "repair_plan_transport.repair_plan_candidate_action",
                            "repair_approval_binding.repair_approval_binding_status",
                            "repair_approval_binding.repair_approval_binding_validity",
                            "repair_approval_binding.repair_approval_binding_primary_reason",
                            "repair_suggestion_contract.repair_suggestion_status",
                            "reconcile_contract.reconcile_status",
                            "objective_contract.objective_status",
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (run_root / "bounded_execution_bridge.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "run_id": "job-lifecycle",
                        "objective_id": "objective-job-lifecycle",
                        "bounded_execution_status": "blocked",
                        "bounded_execution_decision": "request_replan",
                        "bounded_execution_scope": "replan_only",
                        "bounded_execution_candidate_action": "attempt_replan_preparation",
                        "bounded_execution_validity": "insufficient_truth",
                        "bounded_execution_confidence": "conservative_low",
                        "bounded_execution_primary_reason": "authorization_not_eligible",
                        "bounded_execution_reason_codes": [
                            "authorization_not_eligible",
                            "replan_required",
                        ],
                        "bounded_execution_blocked_reason": "authorization_not_eligible",
                        "bounded_execution_blocked_reasons": [
                            "authorization_not_eligible",
                            "replan_required",
                        ],
                        "bounded_execution_manual_required": True,
                        "bounded_execution_replan_required": True,
                        "bounded_execution_truth_gathering_required": False,
                        "bounded_execution_ready": False,
                        "bounded_execution_deferred": False,
                        "bounded_execution_denied": False,
                        "bounded_execution_source_status": "derived_from_execution_authorization",
                        "bounded_execution_authorization_status": "pending",
                        "bounded_execution_binding_status": "missing",
                        "bounded_execution_plan_status": "available",
                        "supporting_compact_truth_refs": [
                            "run_state.next_safe_action",
                            "run_state.policy_primary_action",
                            "run_state.lifecycle_closure_status",
                            "run_state.policy_status",
                            "completion_contract.completion_status",
                            "approval_transport.approval_status",
                            "approval_transport.approval_transport_status",
                            "repair_plan_transport.repair_plan_status",
                            "repair_plan_transport.repair_plan_candidate_action",
                            "repair_approval_binding.repair_approval_binding_status",
                            "repair_approval_binding.repair_approval_binding_validity",
                            "execution_authorization_gate.execution_authorization_status",
                            "execution_authorization_gate.execution_authorization_validity",
                            "execution_authorization_gate.execution_authorization_primary_reason",
                            "repair_suggestion_contract.repair_suggestion_status",
                            "reconcile_contract.reconcile_status",
                            "objective_contract.objective_status",
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            self._seed_job(
                db_path=db_path,
                job_id="job-lifecycle",
                result_path_override=str(result_path),
            )

            proc = self._run(["--job-id", "job-lifecycle", "--db-path", str(db_path), "--json"])
            human_proc = self._run(["--job-id", "job-lifecycle", "--db-path", str(db_path)])

        self.assertEqual(proc.returncode, 0)
        self.assertEqual(human_proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertIn("lifecycle_artifacts", payload)
        self.assertEqual(
            payload["lifecycle_artifacts"]["checkpoint_decision"]["decision"],
            "global_stop_recommended",
        )
        self.assertTrue(
            payload["lifecycle_artifacts"]["checkpoint_decision"]["manual_intervention_required"]
        )
        self.assertEqual(payload["lifecycle_artifacts"]["commit_decision"]["decision"], "blocked")
        self.assertEqual(payload["lifecycle_artifacts"]["commit_decision"]["readiness_status"], "blocked")
        self.assertEqual(
            payload["lifecycle_artifacts"]["commit_decision"]["readiness_next_action"],
            "resolve_blockers",
        )
        self.assertFalse(payload["lifecycle_artifacts"]["commit_decision"]["automation_eligible"])
        self.assertEqual(payload["lifecycle_artifacts"]["merge_decision"]["decision"], "manual_required")
        self.assertEqual(
            payload["lifecycle_artifacts"]["merge_decision"]["readiness_status"],
            "manual_required",
        )
        self.assertTrue(
            payload["lifecycle_artifacts"]["merge_decision"]["manual_intervention_required"]
        )
        self.assertEqual(payload["lifecycle_artifacts"]["rollback_decision"]["decision"], "required")
        self.assertEqual(
            payload["lifecycle_artifacts"]["rollback_decision"]["readiness_status"],
            "awaiting_prerequisites",
        )
        self.assertEqual(payload["lifecycle_artifacts"]["commit_execution"]["status"], "failed")
        self.assertIn("execution_authority_status", payload["lifecycle_artifacts"]["commit_execution"])
        self.assertIn("validation_status", payload["lifecycle_artifacts"]["commit_execution"])
        self.assertIn("execution_allowed", payload["lifecycle_artifacts"]["commit_execution"])
        self.assertEqual(
            payload["lifecycle_artifacts"]["commit_execution"]["failure_reason"],
            "git_commit_failed",
        )
        self.assertEqual(payload["lifecycle_artifacts"]["push_execution"]["status"], "succeeded")
        self.assertEqual(
            payload["lifecycle_artifacts"]["push_execution"]["remote_state_status"],
            "non_fast_forward_risk",
        )
        self.assertTrue(payload["lifecycle_artifacts"]["push_execution"]["remote_state_blocked"])
        self.assertTrue(payload["lifecycle_artifacts"]["push_execution"]["remote_github_blocked"])
        self.assertIn("execution_authority_status", payload["lifecycle_artifacts"]["push_execution"])
        self.assertIn("validation_status", payload["lifecycle_artifacts"]["push_execution"])
        self.assertEqual(payload["lifecycle_artifacts"]["pr_execution"]["status"], "succeeded")
        self.assertEqual(
            payload["lifecycle_artifacts"]["pr_execution"]["existing_pr_status"],
            "existing_open",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["pr_execution"]["pr_creation_state_status"],
            "blocked_existing_pr",
        )
        self.assertIn("execution_authority_status", payload["lifecycle_artifacts"]["pr_execution"])
        self.assertIn("validation_status", payload["lifecycle_artifacts"]["pr_execution"])
        self.assertEqual(payload["lifecycle_artifacts"]["pr_execution"]["pr_number"], 123)
        self.assertEqual(payload["lifecycle_artifacts"]["merge_execution"]["status"], "failed")
        self.assertEqual(
            payload["lifecycle_artifacts"]["merge_execution"]["mergeability_status"],
            "unknown",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["merge_execution"]["merge_requirements_status"],
            "unsatisfied",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["merge_execution"]["required_checks_status"],
            "unsatisfied",
        )
        self.assertIn("execution_authority_status", payload["lifecycle_artifacts"]["merge_execution"])
        self.assertIn("validation_status", payload["lifecycle_artifacts"]["merge_execution"])
        self.assertEqual(
            payload["lifecycle_artifacts"]["merge_execution"]["failure_reason"],
            "merge_execution_failed:api_failure",
        )
        self.assertEqual(payload["lifecycle_artifacts"]["rollback_execution"]["status"], "blocked")
        self.assertIn("execution_authority_status", payload["lifecycle_artifacts"]["rollback_execution"])
        self.assertIn("validation_status", payload["lifecycle_artifacts"]["rollback_execution"])
        self.assertEqual(
            payload["lifecycle_artifacts"]["rollback_execution"]["rollback_mode"],
            "pushed_or_pr_open",
        )
        self.assertTrue(
            payload["lifecycle_artifacts"]["rollback_execution"]["manual_intervention_required"]
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["rollback_execution"]["rollback_aftermath_status"],
            "validation_failed",
        )
        self.assertTrue(
            payload["lifecycle_artifacts"]["rollback_execution"]["rollback_aftermath_blocked"]
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["rollback_execution"]["rollback_aftermath_blocked_reason"],
            "rollback_validation_failed",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["rollback_execution"]["rollback_validation_status"],
            "failed",
        )
        self.assertTrue(
            payload["lifecycle_artifacts"]["rollback_execution"]["rollback_manual_followup_required"]
        )
        self.assertTrue(
            payload["lifecycle_artifacts"]["rollback_execution"]["rollback_remote_followup_required"]
        )
        self.assertTrue(
            payload["lifecycle_artifacts"]["commit_execution"]["manual_intervention_required"]
        )
        self.assertEqual(payload["lifecycle_artifacts"]["run_state"]["state"], "paused")
        self.assertEqual(payload["lifecycle_artifacts"]["run_state"]["orchestration_state"], "global_stop_pending")
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["global_stop"])
        self.assertFalse(payload["lifecycle_artifacts"]["run_state"]["continue_allowed"])
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["run_paused"])
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["manual_intervention_required"])
        self.assertFalse(payload["lifecycle_artifacts"]["run_state"]["rollback_evaluation_pending"])
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["global_stop_recommended"])
        self.assertEqual(payload["lifecycle_artifacts"]["run_state"]["next_run_action"], "hold_for_global_stop")
        self.assertEqual(payload["lifecycle_artifacts"]["run_state"]["loop_state"], "manual_intervention_required")
        self.assertEqual(payload["lifecycle_artifacts"]["run_state"]["next_safe_action"], "require_manual_intervention")
        self.assertEqual(payload["lifecycle_artifacts"]["run_state"]["loop_blocked_reason"], "global_stop_recommended")
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["resumable"])
        self.assertFalse(payload["lifecycle_artifacts"]["run_state"]["terminal"])
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["loop_manual_intervention_required"])
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["loop_replan_required"])
        self.assertFalse(payload["lifecycle_artifacts"]["run_state"]["rollback_completed"])
        self.assertFalse(payload["lifecycle_artifacts"]["run_state"]["delivery_completed"])
        self.assertIn("execute_rollback", payload["lifecycle_artifacts"]["run_state"]["loop_allowed_actions"])
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["unit_blocked"])
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["readiness_blocked"])
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["readiness_manual_required"])
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["readiness_awaiting_prerequisites"])
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["commit_execution_failed"])
        self.assertTrue(
            payload["lifecycle_artifacts"]["run_state"]["commit_execution_manual_intervention_required"]
        )
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["push_execution_succeeded"])
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["pr_execution_succeeded"])
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["merge_execution_failed"])
        self.assertTrue(
            payload["lifecycle_artifacts"]["run_state"]["delivery_execution_manual_intervention_required"]
        )
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["rollback_execution_pending"])
        self.assertTrue(
            payload["lifecycle_artifacts"]["run_state"]["rollback_execution_manual_intervention_required"]
        )
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["rollback_replan_required"])
        self.assertTrue(
            payload["lifecycle_artifacts"]["run_state"]["rollback_automatic_continuation_blocked"]
        )
        self.assertIn("authority_validation_blocked", payload["lifecycle_artifacts"]["run_state"])
        self.assertIn("execution_authority_blocked", payload["lifecycle_artifacts"]["run_state"])
        self.assertIn("validation_blocked", payload["lifecycle_artifacts"]["run_state"])
        self.assertIn("authority_validation_manual_required", payload["lifecycle_artifacts"]["run_state"])
        self.assertIn("authority_validation_missing_or_ambiguous", payload["lifecycle_artifacts"]["run_state"])
        self.assertIn("authority_validation_blocked_reason", payload["lifecycle_artifacts"]["run_state"])
        self.assertIn("authority_validation_blocked_reasons", payload["lifecycle_artifacts"]["run_state"])
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["rollback_aftermath_status"],
            "validation_failed",
        )
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["rollback_aftermath_blocked"])
        self.assertTrue(
            payload["lifecycle_artifacts"]["run_state"]["rollback_aftermath_manual_required"]
        )
        self.assertTrue(
            payload["lifecycle_artifacts"]["run_state"]["rollback_aftermath_missing_or_ambiguous"]
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["rollback_aftermath_blocked_reason"],
            "rollback_validation_failed",
        )
        self.assertTrue(
            payload["lifecycle_artifacts"]["run_state"]["rollback_remote_followup_required"]
        )
        self.assertTrue(
            payload["lifecycle_artifacts"]["run_state"]["rollback_manual_followup_required"]
        )
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["rollback_validation_failed"])
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["remote_github_blocked"])
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["remote_github_manual_required"])
        self.assertTrue(
            payload["lifecycle_artifacts"]["run_state"]["remote_github_missing_or_ambiguous"]
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["remote_github_blocked_reason"],
            "required_checks_unsatisfied",
        )
        self.assertIn(
            "existing_open_pr_detected",
            payload["lifecycle_artifacts"]["run_state"]["remote_github_blocked_reasons"],
        )
        self.assertEqual(payload["lifecycle_artifacts"]["run_state"]["policy_status"], "manual_only")
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["policy_blocked"])
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["policy_manual_required"])
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["policy_replan_required"])
        self.assertFalse(payload["lifecycle_artifacts"]["run_state"]["policy_resume_allowed"])
        self.assertFalse(payload["lifecycle_artifacts"]["run_state"]["policy_terminal"])
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["policy_blocked_reason"],
            "rollback_validation_failed",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["policy_primary_blocker_class"],
            "replan_required",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["operator_posture_summary"],
            "execution_blocked_replan_required",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["operator_primary_blocker_class"],
            "replan_required",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["operator_primary_action"],
            "rollback_required",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["operator_action_scope"],
            "run_wide",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["operator_resume_status"],
            "replan_required",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["operator_next_safe_posture"],
            "replan_required_before_execution",
        )
        self.assertIn(
            "roadmap_replan",
            payload["lifecycle_artifacts"]["run_state"]["operator_safe_actions_summary"],
        )
        self.assertIn(
            "proceed_to_pr",
            payload["lifecycle_artifacts"]["run_state"]["operator_unsafe_actions_summary"],
        )
        self.assertIn(
            "needed_now:replan_required_before_execution",
            payload["lifecycle_artifacts"]["run_state"]["operator_guidance_summary"],
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["lifecycle_closure_status"],
            "stopped_replan_required",
        )
        self.assertFalse(payload["lifecycle_artifacts"]["run_state"]["lifecycle_safely_closed"])
        self.assertFalse(payload["lifecycle_artifacts"]["run_state"]["lifecycle_terminal"])
        self.assertFalse(payload["lifecycle_artifacts"]["run_state"]["lifecycle_resumable"])
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["lifecycle_manual_required"])
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["lifecycle_replan_required"])
        self.assertFalse(
            payload["lifecycle_artifacts"]["run_state"]["lifecycle_execution_complete_not_closed"]
        )
        self.assertFalse(
            payload["lifecycle_artifacts"]["run_state"]["lifecycle_rollback_complete_not_closed"]
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["lifecycle_primary_closure_issue"],
            "rollback_validation_failed",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["lifecycle_stop_class"],
            "stopped_replan_required",
        )
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["objective_contract_present"])
        self.assertEqual(payload["lifecycle_artifacts"]["run_state"]["objective_id"], "objective-job-lifecycle")
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["objective_contract_status"],
            "underspecified",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["objective_acceptance_status"],
            "partially_defined",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["objective_scope_status"],
            "clear",
        )
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["completion_contract_present"])
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["completion_status"],
            "replan_before_closure",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["done_status"],
            "not_done",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["safe_closure_status"],
            "not_safely_closed",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["completion_evidence_status"],
            "partial",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["completion_blocked_reason"],
            "replan_before_closure",
        )
        self.assertTrue(
            payload["lifecycle_artifacts"]["run_state"]["completion_manual_required"]
        )
        self.assertTrue(
            payload["lifecycle_artifacts"]["run_state"]["completion_replan_required"]
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["completion_lifecycle_alignment_status"],
            "partially_aligned",
        )
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["approval_transport_present"])
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["approval_status"],
            "deferred",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["approval_decision"],
            "defer",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["approval_scope"],
            "current_completion_state",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["approved_action"],
            "hold_for_manual_review",
        )
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["approval_required"])
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["approval_transport_status"],
            "non_actionable",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["approval_compatibility_status"],
            "partially_compatible",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["approval_blocked_reason"],
            "approval_scope_partial",
        )
        self.assertTrue(payload["lifecycle_artifacts"]["run_state"]["reconcile_contract_present"])
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["reconcile_status"],
            "blocked",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["reconcile_decision"],
            "request_replan",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["reconcile_primary_mismatch"],
            "objective_underspecified",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["reconcile_blocked_reason"],
            "objective_underspecified",
        )
        self.assertFalse(
            payload["lifecycle_artifacts"]["run_state"]["reconcile_waiting_on_truth"]
        )
        self.assertTrue(
            payload["lifecycle_artifacts"]["run_state"]["reconcile_manual_required"]
        )
        self.assertTrue(
            payload["lifecycle_artifacts"]["run_state"]["reconcile_replan_required"]
        )
        self.assertTrue(
            payload["lifecycle_artifacts"]["run_state"]["repair_suggestion_contract_present"]
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["repair_suggestion_status"],
            "suggested",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["repair_suggestion_decision"],
            "request_replan",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["repair_primary_reason"],
            "objective_underspecified",
        )
        self.assertTrue(
            payload["lifecycle_artifacts"]["run_state"]["repair_manual_required"]
        )
        self.assertTrue(
            payload["lifecycle_artifacts"]["run_state"]["repair_replan_required"]
        )
        self.assertFalse(
            payload["lifecycle_artifacts"]["run_state"]["repair_truth_gathering_required"]
        )
        self.assertTrue(
            payload["lifecycle_artifacts"]["run_state"]["repair_plan_transport_present"]
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["repair_plan_status"],
            "available",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["repair_plan_decision"],
            "prepare_replan_plan",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["repair_plan_class"],
            "replan_plan",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["repair_plan_priority"],
            "high",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["repair_plan_candidate_action"],
            "request_replan",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["repair_plan_primary_reason"],
            "replan_required",
        )
        self.assertTrue(
            payload["lifecycle_artifacts"]["run_state"]["repair_plan_manual_required"]
        )
        self.assertTrue(
            payload["lifecycle_artifacts"]["run_state"]["repair_plan_replan_required"]
        )
        self.assertFalse(
            payload["lifecycle_artifacts"]["run_state"]["repair_plan_truth_gathering_required"]
        )
        self.assertTrue(
            payload["lifecycle_artifacts"]["run_state"]["repair_approval_binding_present"]
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["repair_approval_binding_status"],
            "missing",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["repair_approval_binding_decision"],
            "hold_unbound",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["repair_approval_binding_validity"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["repair_approval_binding_compatibility_status"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["repair_approval_binding_primary_reason"],
            "missing_approval",
        )
        self.assertTrue(
            payload["lifecycle_artifacts"]["run_state"]["repair_approval_binding_manual_required"]
        )
        self.assertTrue(
            payload["lifecycle_artifacts"]["run_state"]["repair_approval_binding_replan_required"]
        )
        self.assertTrue(
            payload["lifecycle_artifacts"]["run_state"]["execution_authorization_gate_present"]
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["execution_authorization_status"],
            "pending",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["execution_authorization_decision"],
            "request_replan",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["execution_authorization_validity"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["execution_authorization_confidence"],
            "partial",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["execution_authorization_primary_reason"],
            "missing_binding",
        )
        self.assertTrue(
            payload["lifecycle_artifacts"]["run_state"]["execution_authorization_manual_required"]
        )
        self.assertTrue(
            payload["lifecycle_artifacts"]["run_state"]["execution_authorization_replan_required"]
        )
        self.assertTrue(
            payload["lifecycle_artifacts"]["run_state"]["bounded_execution_bridge_present"]
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["bounded_execution_status"],
            "blocked",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["bounded_execution_decision"],
            "request_replan",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["bounded_execution_validity"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["bounded_execution_primary_reason"],
            "authorization_not_eligible",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["objective_contract"]["objective_status"],
            "underspecified",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["objective_contract"]["objective_source_status"],
            "structured_partial",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["objective_contract"]["acceptance_criteria_total"],
            2,
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["completion_contract"]["completion_status"],
            "replan_before_closure",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["completion_contract"]["done_status"],
            "not_done",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["completion_contract"]["safe_closure_status"],
            "not_safely_closed",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["completion_contract"]["completion_evidence_status"],
            "partial",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["completion_contract"]["required_evidence_total"],
            3,
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["completion_contract"]["missing_evidence_total"],
            1,
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["approval_transport"]["approval_status"],
            "deferred",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["approval_transport"]["approval_decision"],
            "defer",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["approval_transport"]["approval_scope"],
            "current_completion_state",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["approval_transport"]["approval_transport_status"],
            "non_actionable",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["approval_transport"]["approval_compatibility_status"],
            "partially_compatible",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["approval_transport"]["approval_blocked_reason"],
            "approval_scope_partial",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["reconcile_contract"]["reconcile_status"],
            "blocked",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["reconcile_contract"]["reconcile_decision"],
            "request_replan",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["reconcile_contract"]["reconcile_transport_status"],
            "partial",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["repair_suggestion_contract"]["repair_suggestion_status"],
            "suggested",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["repair_suggestion_contract"]["repair_suggestion_decision"],
            "request_replan",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["repair_suggestion_contract"]["repair_suggestion_class"],
            "objective_gap",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["repair_suggestion_contract"]["repair_primary_reason"],
            "objective_underspecified",
        )
        self.assertFalse(
            payload["lifecycle_artifacts"]["repair_suggestion_contract"]["repair_execution_recommended"]
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["repair_plan_transport"]["repair_plan_status"],
            "available",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["repair_plan_transport"]["repair_plan_decision"],
            "prepare_replan_plan",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["repair_plan_transport"]["repair_plan_class"],
            "replan_plan",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["repair_plan_transport"]["repair_plan_primary_reason"],
            "replan_required",
        )
        self.assertFalse(
            payload["lifecycle_artifacts"]["repair_plan_transport"]["repair_plan_execution_ready"]
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["repair_approval_binding"]["repair_approval_binding_status"],
            "missing",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["repair_approval_binding"]["repair_approval_binding_decision"],
            "hold_unbound",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["repair_approval_binding"]["repair_approval_binding_validity"],
            "insufficient_truth",
        )
        self.assertFalse(
            payload["lifecycle_artifacts"]["repair_approval_binding"]["repair_approval_binding_execution_authorized"]
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["execution_authorization_gate"][
                "execution_authorization_status"
            ],
            "pending",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["execution_authorization_gate"][
                "execution_authorization_decision"
            ],
            "request_replan",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["execution_authorization_gate"][
                "execution_authorization_validity"
            ],
            "insufficient_truth",
        )
        self.assertFalse(
            payload["lifecycle_artifacts"]["execution_authorization_gate"][
                "execution_authorization_eligible"
            ]
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["bounded_execution_bridge"][
                "bounded_execution_status"
            ],
            "blocked",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["bounded_execution_bridge"][
                "bounded_execution_decision"
            ],
            "request_replan",
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["bounded_execution_bridge"][
                "bounded_execution_validity"
            ],
            "insufficient_truth",
        )
        self.assertFalse(
            payload["lifecycle_artifacts"]["bounded_execution_bridge"][
                "bounded_execution_ready"
            ]
        )
        self.assertIn(
            "proceed_to_pr",
            payload["lifecycle_artifacts"]["run_state"]["policy_disallowed_actions"],
        )
        self.assertIn(
            "roadmap_replan",
            payload["lifecycle_artifacts"]["run_state"]["policy_manual_actions"],
        )
        self.assertEqual(
            payload["lifecycle_artifacts"]["run_state"]["readiness_summary"]["merge"]["manual_required"],
            1,
        )
        self.assertIsNotNone(payload["lifecycle_artifacts"]["paths"]["checkpoint_decision"])
        self.assertIsNotNone(payload["lifecycle_artifacts"]["paths"]["commit_execution"])
        self.assertIsNotNone(payload["lifecycle_artifacts"]["paths"]["push_execution"])
        self.assertIsNotNone(payload["lifecycle_artifacts"]["paths"]["pr_execution"])
        self.assertIsNotNone(payload["lifecycle_artifacts"]["paths"]["merge_execution"])
        self.assertIsNotNone(payload["lifecycle_artifacts"]["paths"]["rollback_execution"])
        self.assertIsNotNone(payload["lifecycle_artifacts"]["paths"]["objective_contract"])
        self.assertIsNotNone(payload["lifecycle_artifacts"]["paths"]["completion_contract"])
        self.assertIsNotNone(payload["lifecycle_artifacts"]["paths"]["approval_transport"])
        self.assertIsNotNone(payload["lifecycle_artifacts"]["paths"]["reconcile_contract"])
        self.assertIsNotNone(payload["lifecycle_artifacts"]["paths"]["repair_suggestion_contract"])
        self.assertIsNotNone(payload["lifecycle_artifacts"]["paths"]["repair_plan_transport"])
        self.assertIsNotNone(payload["lifecycle_artifacts"]["paths"]["repair_approval_binding"])
        self.assertIsNotNone(payload["lifecycle_artifacts"]["paths"]["execution_authorization_gate"])
        self.assertIsNotNone(payload["lifecycle_artifacts"]["paths"]["bounded_execution_bridge"])
        self.assertIn("lifecycle_operator_posture_summary:", human_proc.stdout)
        self.assertIn("lifecycle_operator_safe_actions_summary:", human_proc.stdout)
        self.assertIn("lifecycle_operator_unsafe_actions_summary:", human_proc.stdout)
        self.assertIn("lifecycle_objective_contract_status:", human_proc.stdout)
        self.assertIn("lifecycle_objective_contract_path:", human_proc.stdout)
        self.assertIn("lifecycle_completion_status:", human_proc.stdout)
        self.assertIn("lifecycle_completion_contract_path:", human_proc.stdout)
        self.assertIn("lifecycle_approval_status:", human_proc.stdout)
        self.assertIn("lifecycle_approval_transport_status:", human_proc.stdout)
        self.assertIn("lifecycle_approval_transport_path:", human_proc.stdout)
        self.assertIn("lifecycle_reconcile_status:", human_proc.stdout)
        self.assertIn("lifecycle_reconcile_contract_path:", human_proc.stdout)
        self.assertIn("lifecycle_repair_suggestion_status:", human_proc.stdout)
        self.assertIn("lifecycle_repair_suggestion_contract_path:", human_proc.stdout)
        self.assertIn("lifecycle_repair_plan_status:", human_proc.stdout)
        self.assertIn("lifecycle_repair_plan_transport_path:", human_proc.stdout)
        self.assertIn("lifecycle_repair_approval_binding_status:", human_proc.stdout)
        self.assertIn("lifecycle_repair_approval_binding_path:", human_proc.stdout)
        self.assertIn("lifecycle_execution_authorization_status:", human_proc.stdout)
        self.assertIn("lifecycle_execution_authorization_gate_path:", human_proc.stdout)
        self.assertIn("lifecycle_bounded_execution_status:", human_proc.stdout)
        self.assertIn("lifecycle_bounded_execution_bridge_path:", human_proc.stdout)
        self.assertIn("lifecycle_closure_status:", human_proc.stdout)
        self.assertIn("lifecycle_execution_complete_not_closed:", human_proc.stdout)
        self.assertIn("lifecycle_rollback_complete_not_closed:", human_proc.stdout)

    def test_inspect_surfaces_retry_reentry_loop_contract_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            run_root = tmp_root / "runs" / "job-retry-loop"
            unit_dir = run_root / "pr-01"
            unit_dir.mkdir(parents=True, exist_ok=True)
            result_path = unit_dir / "result.json"
            result_path.write_text("{}", encoding="utf-8")

            (run_root / "run_state.json").write_text(
                json.dumps(
                    {
                        "run_id": "job-retry-loop",
                        "state": "paused",
                        "loop_state": "manual_intervention_required",
                        "next_safe_action": "pause",
                        "retry_reentry_loop_contract_present": True,
                        "retry_loop_status": "retry_ready",
                        "retry_loop_decision": "same_lane_retry",
                        "retry_loop_validity": "valid",
                        "retry_loop_confidence": "high",
                        "loop_primary_reason": "same_lane_retry_allowed",
                        "attempt_count": 1,
                        "max_attempt_count": 2,
                        "reentry_count": 0,
                        "max_reentry_count": 2,
                        "same_failure_count": 1,
                        "max_same_failure_count": 2,
                        "retry_allowed": True,
                        "reentry_allowed": False,
                        "retry_exhausted": False,
                        "reentry_exhausted": False,
                        "same_failure_exhausted": False,
                        "terminal_stop_required": False,
                        "manual_escalation_required": False,
                        "replan_required": False,
                        "recollect_required": False,
                        "same_lane_retry_allowed": True,
                        "repair_retry_allowed": False,
                        "no_progress_stop_required": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (run_root / "retry_reentry_loop_contract.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "run_id": "job-retry-loop",
                        "objective_id": "objective-retry-loop",
                        "retry_loop_status": "retry_ready",
                        "retry_loop_decision": "same_lane_retry",
                        "retry_loop_validity": "valid",
                        "retry_loop_confidence": "high",
                        "loop_primary_reason": "same_lane_retry_allowed",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            self._seed_job(
                db_path=db_path,
                job_id="job-retry-loop",
                result_path_override=str(result_path),
            )

            proc = self._run(["--job-id", "job-retry-loop", "--db-path", str(db_path), "--json"])
            human_proc = self._run(["--job-id", "job-retry-loop", "--db-path", str(db_path)])

        self.assertEqual(proc.returncode, 0)
        self.assertEqual(human_proc.returncode, 0)
        payload = json.loads(proc.stdout)
        run_state = payload["lifecycle_artifacts"]["run_state"]
        retry_contract = payload["lifecycle_artifacts"]["retry_reentry_loop_contract"]

        self.assertTrue(run_state["retry_reentry_loop_contract_present"])
        self.assertEqual(run_state["retry_loop_status"], "retry_ready")
        self.assertEqual(run_state["retry_loop_decision"], "same_lane_retry")
        self.assertEqual(run_state["loop_primary_reason"], "same_lane_retry_allowed")
        self.assertEqual(retry_contract["retry_loop_status"], "retry_ready")
        self.assertEqual(retry_contract["retry_loop_decision"], "same_lane_retry")
        self.assertEqual(retry_contract["loop_primary_reason"], "same_lane_retry_allowed")
        self.assertIsNotNone(payload["lifecycle_artifacts"]["paths"]["retry_reentry_loop_contract"])

        self.assertIn("lifecycle_retry_loop_status:", human_proc.stdout)
        self.assertIn("lifecycle_retry_loop_status_artifact:", human_proc.stdout)
        self.assertIn("lifecycle_retry_reentry_loop_contract_path:", human_proc.stdout)

    def test_inspect_surfaces_endgame_closure_contract_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            run_root = tmp_root / "runs" / "job-endgame"
            unit_dir = run_root / "pr-01"
            unit_dir.mkdir(parents=True, exist_ok=True)
            result_path = unit_dir / "result.json"
            result_path.write_text("{}", encoding="utf-8")

            (run_root / "run_state.json").write_text(
                json.dumps(
                    {
                        "run_id": "job-endgame",
                        "state": "completed",
                        "loop_state": "terminal_success",
                        "next_safe_action": "stop_terminal_success",
                        "endgame_closure_contract_present": True,
                        "endgame_closure_status": "safely_closed",
                        "endgame_closure_outcome": "terminal_success_closed",
                        "endgame_closure_validity": "valid",
                        "endgame_closure_confidence": "high",
                        "final_closure_class": "safely_closed",
                        "terminal_stop_class": "terminal_success",
                        "closure_resolution_status": "resolved",
                        "endgame_primary_reason": "safely_closed",
                        "safely_closed": True,
                        "completed_but_not_closed": False,
                        "rollback_complete_but_not_closed": False,
                        "manual_closure_only": False,
                        "external_truth_pending": False,
                        "closure_unresolved": False,
                        "terminal_success": True,
                        "terminal_non_success": False,
                        "operator_followup_required": False,
                        "further_retry_allowed": False,
                        "further_reentry_allowed": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (run_root / "endgame_closure_contract.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "run_id": "job-endgame",
                        "objective_id": "objective-endgame",
                        "endgame_closure_status": "safely_closed",
                        "endgame_closure_outcome": "terminal_success_closed",
                        "endgame_closure_validity": "valid",
                        "endgame_closure_confidence": "high",
                        "final_closure_class": "safely_closed",
                        "terminal_stop_class": "terminal_success",
                        "closure_resolution_status": "resolved",
                        "endgame_primary_reason": "safely_closed",
                        "safely_closed": True,
                        "completed_but_not_closed": False,
                        "rollback_complete_but_not_closed": False,
                        "manual_closure_only": False,
                        "external_truth_pending": False,
                        "closure_unresolved": False,
                        "terminal_success": True,
                        "terminal_non_success": False,
                        "operator_followup_required": False,
                        "further_retry_allowed": False,
                        "further_reentry_allowed": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            self._seed_job(
                db_path=db_path,
                job_id="job-endgame",
                result_path_override=str(result_path),
            )

            proc = self._run(["--job-id", "job-endgame", "--db-path", str(db_path), "--json"])
            human_proc = self._run(["--job-id", "job-endgame", "--db-path", str(db_path)])

        self.assertEqual(proc.returncode, 0)
        self.assertEqual(human_proc.returncode, 0)
        payload = json.loads(proc.stdout)
        run_state = payload["lifecycle_artifacts"]["run_state"]
        endgame_contract = payload["lifecycle_artifacts"]["endgame_closure_contract"]

        self.assertTrue(run_state["endgame_closure_contract_present"])
        self.assertEqual(run_state["endgame_closure_status"], "safely_closed")
        self.assertEqual(run_state["final_closure_class"], "safely_closed")
        self.assertEqual(run_state["terminal_stop_class"], "terminal_success")
        self.assertEqual(endgame_contract["endgame_closure_status"], "safely_closed")
        self.assertEqual(endgame_contract["final_closure_class"], "safely_closed")
        self.assertEqual(endgame_contract["endgame_primary_reason"], "safely_closed")
        self.assertIsNotNone(payload["lifecycle_artifacts"]["paths"]["endgame_closure_contract"])

        self.assertIn("lifecycle_endgame_closure_status:", human_proc.stdout)
        self.assertIn("lifecycle_endgame_closure_status_artifact:", human_proc.stdout)
        self.assertIn("lifecycle_endgame_closure_contract_path:", human_proc.stdout)

    def test_inspect_surfaces_loop_hardening_contract_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            run_root = tmp_root / "runs" / "job-loop-hardening"
            unit_dir = run_root / "pr-01"
            unit_dir.mkdir(parents=True, exist_ok=True)
            result_path = unit_dir / "result.json"
            result_path.write_text("{}", encoding="utf-8")

            (run_root / "run_state.json").write_text(
                json.dumps(
                    {
                        "run_id": "job-loop-hardening",
                        "state": "paused",
                        "loop_state": "manual_intervention_required",
                        "next_safe_action": "pause",
                        "loop_hardening_contract_present": True,
                        "loop_hardening_status": "freeze",
                        "loop_hardening_decision": "freeze_retry",
                        "loop_hardening_validity": "partial",
                        "loop_hardening_confidence": "medium",
                        "loop_hardening_primary_reason": "retry_freeze_required",
                        "same_failure_signature": "bucket=execution_failure|verification=completion_gap|execution=tests_failed|closure=not_closable|decision=hold_for_followup",
                        "same_failure_bucket": "execution_failure",
                        "same_failure_persistence": "high",
                        "no_progress_status": "suspected",
                        "oscillation_status": "none",
                        "retry_freeze_status": "required",
                        "same_failure_detected": True,
                        "same_failure_stop_required": False,
                        "no_progress_detected": False,
                        "no_progress_stop_required": False,
                        "oscillation_detected": False,
                        "unstable_loop_detected": False,
                        "retry_freeze_required": True,
                        "cool_down_required": False,
                        "forced_manual_escalation_required": False,
                        "hardening_stop_required": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (run_root / "loop_hardening_contract.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "run_id": "job-loop-hardening",
                        "objective_id": "objective-loop-hardening",
                        "loop_hardening_status": "freeze",
                        "loop_hardening_decision": "freeze_retry",
                        "loop_hardening_validity": "partial",
                        "loop_hardening_confidence": "medium",
                        "loop_hardening_primary_reason": "retry_freeze_required",
                        "same_failure_bucket": "execution_failure",
                        "same_failure_signature": "bucket=execution_failure|verification=completion_gap|execution=tests_failed|closure=not_closable|decision=hold_for_followup",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            self._seed_job(
                db_path=db_path,
                job_id="job-loop-hardening",
                result_path_override=str(result_path),
            )

            proc = self._run(["--job-id", "job-loop-hardening", "--db-path", str(db_path), "--json"])
            human_proc = self._run(["--job-id", "job-loop-hardening", "--db-path", str(db_path)])

        self.assertEqual(proc.returncode, 0)
        self.assertEqual(human_proc.returncode, 0)
        payload = json.loads(proc.stdout)
        run_state = payload["lifecycle_artifacts"]["run_state"]
        loop_hardening_contract = payload["lifecycle_artifacts"]["loop_hardening_contract"]

        self.assertTrue(run_state["loop_hardening_contract_present"])
        self.assertEqual(run_state["loop_hardening_status"], "freeze")
        self.assertEqual(run_state["loop_hardening_decision"], "freeze_retry")
        self.assertEqual(run_state["loop_hardening_primary_reason"], "retry_freeze_required")
        self.assertEqual(loop_hardening_contract["loop_hardening_status"], "freeze")
        self.assertEqual(loop_hardening_contract["loop_hardening_decision"], "freeze_retry")
        self.assertEqual(
            loop_hardening_contract["loop_hardening_primary_reason"],
            "retry_freeze_required",
        )
        self.assertIsNotNone(payload["lifecycle_artifacts"]["paths"]["loop_hardening_contract"])

        self.assertIn("lifecycle_loop_hardening_status:", human_proc.stdout)
        self.assertIn("lifecycle_loop_hardening_status_artifact:", human_proc.stdout)
        self.assertIn("lifecycle_loop_hardening_contract_path:", human_proc.stdout)

    def test_inspect_surfaces_lane_stabilization_contract_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            run_root = tmp_root / "runs" / "job-lane-stabilization"
            unit_dir = run_root / "pr-01"
            unit_dir.mkdir(parents=True, exist_ok=True)
            result_path = unit_dir / "result.json"
            result_path.write_text("{}", encoding="utf-8")

            (run_root / "run_state.json").write_text(
                json.dumps(
                    {
                        "run_id": "job-lane-stabilization",
                        "state": "paused",
                        "loop_state": "manual_intervention_required",
                        "next_safe_action": "proceed_to_pr",
                        "lane_stabilization_contract_present": True,
                        "lane_status": "lane_transition_ready",
                        "lane_decision": "transition_lane",
                        "lane_validity": "partial",
                        "lane_confidence": "medium",
                        "current_lane": "bounded_local_patch",
                        "target_lane": "replan_preparation",
                        "lane_transition_status": "ready",
                        "lane_transition_decision": "transition",
                        "lane_preconditions_status": "satisfied",
                        "lane_retry_policy_class": "replan_only",
                        "lane_verification_policy_class": "manual_review_check",
                        "lane_escalation_policy_class": "manual_replan",
                        "lane_attempt_budget": 0,
                        "lane_reentry_budget": 2,
                        "lane_transition_count": 1,
                        "max_lane_transition_count": 2,
                        "lane_primary_reason": "lane_transition_ready",
                        "lane_valid": False,
                        "lane_mismatch_detected": False,
                        "lane_transition_required": True,
                        "lane_transition_allowed": True,
                        "lane_transition_blocked": False,
                        "lane_stop_required": False,
                        "lane_manual_review_required": False,
                        "lane_replan_required": True,
                        "lane_truth_gathering_required": False,
                        "lane_execution_allowed": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (run_root / "lane_stabilization_contract.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "run_id": "job-lane-stabilization",
                        "objective_id": "objective-lane-stabilization",
                        "lane_status": "lane_transition_ready",
                        "lane_decision": "transition_lane",
                        "lane_validity": "partial",
                        "lane_confidence": "medium",
                        "current_lane": "bounded_local_patch",
                        "target_lane": "replan_preparation",
                        "lane_primary_reason": "lane_transition_ready",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            self._seed_job(
                db_path=db_path,
                job_id="job-lane-stabilization",
                result_path_override=str(result_path),
            )

            proc = self._run(["--job-id", "job-lane-stabilization", "--db-path", str(db_path), "--json"])
            human_proc = self._run(["--job-id", "job-lane-stabilization", "--db-path", str(db_path)])

        self.assertEqual(proc.returncode, 0)
        self.assertEqual(human_proc.returncode, 0)
        payload = json.loads(proc.stdout)
        run_state = payload["lifecycle_artifacts"]["run_state"]
        lane_contract = payload["lifecycle_artifacts"]["lane_stabilization_contract"]

        self.assertTrue(run_state["lane_stabilization_contract_present"])
        self.assertEqual(run_state["lane_status"], "lane_transition_ready")
        self.assertEqual(run_state["lane_decision"], "transition_lane")
        self.assertEqual(run_state["lane_primary_reason"], "lane_transition_ready")
        self.assertEqual(lane_contract["lane_status"], "lane_transition_ready")
        self.assertEqual(lane_contract["lane_decision"], "transition_lane")
        self.assertEqual(lane_contract["lane_primary_reason"], "lane_transition_ready")
        self.assertIsNotNone(payload["lifecycle_artifacts"]["paths"]["lane_stabilization_contract"])

        self.assertIn("lifecycle_lane_status:", human_proc.stdout)
        self.assertIn("lifecycle_lane_status_artifact:", human_proc.stdout)
        self.assertIn("lifecycle_lane_stabilization_contract_path:", human_proc.stdout)

    def test_inspect_surfaces_observability_rollups_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            run_root = tmp_root / "runs" / "job-observability"
            unit_dir = run_root / "pr-01"
            unit_dir.mkdir(parents=True, exist_ok=True)
            result_path = unit_dir / "result.json"
            result_path.write_text("{}", encoding="utf-8")

            (run_root / "run_state.json").write_text(
                json.dumps(
                    {
                        "run_id": "job-observability",
                        "state": "paused",
                        "loop_state": "manual_intervention_required",
                        "next_safe_action": "pause",
                        "observability_rollup_present": True,
                        "failure_bucketing_hardening_present": True,
                        "artifact_retention_present": True,
                        "fleet_safety_control_present": True,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (run_root / "observability_rollup_contract.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "run_id": "job-observability",
                        "objective_id": "objective-observability",
                        "observability_status": "partial",
                        "observability_validity": "partial",
                        "observability_confidence": "medium",
                        "run_terminal_class": "terminal_non_success",
                        "lane": "replan_preparation",
                        "observability_primary_reason": "retry_exhausted_or_no_progress",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (run_root / "failure_bucket_rollup.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "run_id": "job-observability",
                        "objective_id": "objective-observability",
                        "failure_bucket_status": "classified",
                        "failure_bucket_validity": "valid",
                        "failure_bucket_confidence": "high",
                        "primary_failure_bucket": "execution_failure",
                        "failure_bucket_primary_reason": "classified_execution_failure",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (run_root / "fleet_run_rollup.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "run_id": "job-observability",
                        "objective_id": "objective-observability",
                        "fleet_lane": "replan_preparation",
                        "fleet_terminal_class": "terminal_non_success",
                        "fleet_primary_failure_bucket": "execution_failure",
                        "fleet_observability_status": "partial",
                        "fleet_primary_reason": "fleet_retry_or_no_progress_stop",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (run_root / "failure_bucketing_hardening_contract.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "run_id": "job-observability",
                        "objective_id": "objective-observability",
                        "failure_bucketing_status": "classified",
                        "failure_bucketing_validity": "valid",
                        "failure_bucketing_confidence": "high",
                        "primary_failure_bucket": "execution_failure",
                        "bucket_family": "execution",
                        "bucket_severity": "high",
                        "bucket_stability_class": "stable",
                        "bucket_terminality_class": "terminal",
                        "failure_bucketing_primary_reason": "primary_execution_failure",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (run_root / "retention_manifest.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "run_id": "job-observability",
                        "objective_id": "objective-observability",
                        "reference_layout_version": "v1",
                        "reference_order_stable": True,
                        "alias_deduplicated": True,
                        "manifest_compact": True,
                        "retention_manifest_primary_reason": "canonical_reference_layout_ready",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (run_root / "artifact_retention_contract.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "run_id": "job-observability",
                        "objective_id": "objective-observability",
                        "artifact_retention_status": "ready",
                        "artifact_retention_validity": "valid",
                        "artifact_retention_confidence": "high",
                        "retention_policy_class": "retain_with_prunable_markers",
                        "retention_compaction_class": "compact_with_aliases",
                        "retention_primary_reason": "alias_deduplicated",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (run_root / "fleet_safety_control_contract.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "run_id": "job-observability",
                        "objective_id": "objective-observability",
                        "fleet_safety_status": "freeze",
                        "fleet_safety_validity": "valid",
                        "fleet_safety_confidence": "high",
                        "fleet_safety_decision": "freeze_run",
                        "fleet_restart_decision": "restart_blocked",
                        "fleet_safety_scope": "fleet_sensitive",
                        "fleet_safety_primary_reason": "repeat_risk_blocked",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            self._seed_job(
                db_path=db_path,
                job_id="job-observability",
                result_path_override=str(result_path),
            )

            proc = self._run(["--job-id", "job-observability", "--db-path", str(db_path), "--json"])
            human_proc = self._run(["--job-id", "job-observability", "--db-path", str(db_path)])

        self.assertEqual(proc.returncode, 0)
        self.assertEqual(human_proc.returncode, 0)
        payload = json.loads(proc.stdout)
        run_state = payload["lifecycle_artifacts"]["run_state"]
        observability = payload["lifecycle_artifacts"]["observability_rollup_contract"]
        failure_bucket = payload["lifecycle_artifacts"]["failure_bucket_rollup"]
        fleet_rollup = payload["lifecycle_artifacts"]["fleet_run_rollup"]
        hardened_bucket = payload["lifecycle_artifacts"]["failure_bucketing_hardening_contract"]
        retention_manifest = payload["lifecycle_artifacts"]["retention_manifest"]
        artifact_retention = payload["lifecycle_artifacts"]["artifact_retention_contract"]
        fleet_safety = payload["lifecycle_artifacts"]["fleet_safety_control_contract"]

        self.assertTrue(run_state["observability_rollup_present"])
        self.assertTrue(run_state["failure_bucketing_hardening_present"])
        self.assertTrue(run_state["artifact_retention_present"])
        self.assertTrue(run_state["fleet_safety_control_present"])
        self.assertEqual(observability["observability_status"], "partial")
        self.assertEqual(observability["run_terminal_class"], "terminal_non_success")
        self.assertEqual(failure_bucket["primary_failure_bucket"], "execution_failure")
        self.assertEqual(fleet_rollup["fleet_terminal_class"], "terminal_non_success")
        self.assertEqual(hardened_bucket["primary_failure_bucket"], "execution_failure")
        self.assertEqual(hardened_bucket["bucket_family"], "execution")
        self.assertEqual(
            retention_manifest["retention_manifest_primary_reason"],
            "canonical_reference_layout_ready",
        )
        self.assertEqual(artifact_retention["artifact_retention_status"], "ready")
        self.assertEqual(fleet_safety["fleet_safety_status"], "freeze")
        self.assertEqual(fleet_safety["fleet_safety_decision"], "freeze_run")
        self.assertIsNotNone(payload["lifecycle_artifacts"]["paths"]["observability_rollup_contract"])
        self.assertIsNotNone(payload["lifecycle_artifacts"]["paths"]["failure_bucket_rollup"])
        self.assertIsNotNone(payload["lifecycle_artifacts"]["paths"]["fleet_run_rollup"])
        self.assertIsNotNone(
            payload["lifecycle_artifacts"]["paths"]["failure_bucketing_hardening_contract"]
        )
        self.assertIsNotNone(payload["lifecycle_artifacts"]["paths"]["retention_manifest"])
        self.assertIsNotNone(
            payload["lifecycle_artifacts"]["paths"]["artifact_retention_contract"]
        )
        self.assertIsNotNone(
            payload["lifecycle_artifacts"]["paths"]["fleet_safety_control_contract"]
        )

        self.assertIn("lifecycle_observability_rollup_present:", human_proc.stdout)
        self.assertIn("lifecycle_failure_bucketing_hardening_present:", human_proc.stdout)
        self.assertIn("lifecycle_artifact_retention_present:", human_proc.stdout)
        self.assertIn("lifecycle_fleet_safety_control_present:", human_proc.stdout)
        self.assertIn("lifecycle_observability_status_artifact:", human_proc.stdout)
        self.assertIn("lifecycle_primary_failure_bucket_artifact:", human_proc.stdout)
        self.assertIn("lifecycle_fleet_terminal_class_artifact:", human_proc.stdout)
        self.assertIn("lifecycle_hardened_primary_failure_bucket_artifact:", human_proc.stdout)
        self.assertIn("lifecycle_artifact_retention_status_artifact:", human_proc.stdout)
        self.assertIn("lifecycle_fleet_safety_status_artifact:", human_proc.stdout)
        self.assertIn("lifecycle_observability_rollup_contract_path:", human_proc.stdout)
        self.assertIn("lifecycle_failure_bucket_rollup_path:", human_proc.stdout)
        self.assertIn("lifecycle_fleet_run_rollup_path:", human_proc.stdout)
        self.assertIn(
            "lifecycle_failure_bucketing_hardening_contract_path:",
            human_proc.stdout,
        )
        self.assertIn("lifecycle_retention_manifest_path:", human_proc.stdout)
        self.assertIn("lifecycle_artifact_retention_contract_path:", human_proc.stdout)
        self.assertIn("lifecycle_fleet_safety_control_contract_path:", human_proc.stdout)

    def test_missing_job_exits_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "state" / "jobs.db"
            self._seed_job(db_path=db_path, job_id="known-job")

            proc = self._run(["--job-id", "missing-job", "--db-path", str(db_path)])

        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Job not found: missing-job", proc.stderr)

    def test_inspect_distinguishes_action_specific_denial_from_run_wide_posture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            run_root = tmp_root / "runs" / "job-action-scope"
            unit_dir = run_root / "pr-01"
            unit_dir.mkdir(parents=True, exist_ok=True)
            result_path = unit_dir / "result.json"
            result_path.write_text("{}", encoding="utf-8")
            (run_root / "run_state.json").write_text(
                json.dumps(
                    {
                        "state": "paused",
                        "loop_state": "manual_intervention_required",
                        "next_safe_action": "pause",
                        "policy_status": "blocked",
                        "policy_blocked": True,
                        "policy_manual_required": False,
                        "policy_replan_required": False,
                        "policy_resume_allowed": True,
                        "policy_terminal": False,
                        "policy_primary_blocker_class": "remote_github",
                        "policy_primary_action": "proceed_to_pr",
                        "policy_blocked_reason": "existing_open_pr_detected",
                        "policy_blocked_reasons": ["existing_open_pr_detected"],
                        "policy_allowed_actions": ["inspect", "signal_recollect"],
                        "policy_disallowed_actions": ["proceed_to_pr"],
                        "resumable": True,
                        "terminal": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            self._seed_job(
                db_path=db_path,
                job_id="job-action-scope",
                result_path_override=str(result_path),
            )

            proc = self._run(["--job-id", "job-action-scope", "--db-path", str(db_path), "--json"])

        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        run_state = payload["lifecycle_artifacts"]["run_state"]
        self.assertEqual(run_state["operator_posture_summary"], "action_specific_denial_non_terminal")
        self.assertEqual(run_state["operator_action_scope"], "action_specific")
        self.assertEqual(run_state["operator_primary_action"], "proceed_to_pr")
        self.assertEqual(run_state["operator_resume_status"], "resumable")
        self.assertEqual(run_state["lifecycle_closure_status"], "stopped_resumable")
        self.assertFalse(run_state["lifecycle_terminal"])
        self.assertTrue(run_state["lifecycle_resumable"])
        self.assertIn("proceed_to_pr", run_state["operator_unsafe_actions_summary"])

    def test_artifact_derived_fail_reasons_are_surfaced_when_files_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            rubric_path = tmp_root / "rubric.json"
            merge_gate_path = tmp_root / "merge_gate.json"
            rubric_path.write_text(
                json.dumps({"fail_reasons": ["required_tests_not_passed"]}),
                encoding="utf-8",
            )
            merge_gate_path.write_text(
                json.dumps({"fail_reasons": ["category_not_auto_merge_allowed"]}),
                encoding="utf-8",
            )
            self._seed_job(
                db_path=db_path,
                job_id="job-fail-reasons",
                rubric_path=str(rubric_path),
                merge_gate_path=str(merge_gate_path),
            )

            proc = self._run(["--job-id", "job-fail-reasons", "--db-path", str(db_path), "--json"])

        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["fail_reasons"]["rubric"], ["required_tests_not_passed"])
        self.assertEqual(payload["fail_reasons"]["merge_gate"], ["category_not_auto_merge_allowed"])

    def test_replan_input_is_loaded_from_merge_gate_artifact_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            merge_gate_path = tmp_root / "merge_gate.json"
            merge_gate_path.write_text(
                json.dumps(
                    {
                        "fail_reasons": ["required_tests_not_passed"],
                        "replan_input": {
                            "failure_type": "execution_failure",
                            "current_state": "manual_only",
                            "lifecycle_state": "manual_only",
                            "write_authority_state": "disabled",
                            "category": "docs_only",
                            "changed_files": ["docs/reviewer_runbook.md"],
                            "prior_attempt_count": 1,
                            "retry_budget_total": 2,
                            "retry_budget_remaining": 1,
                            "budget_exhausted": False,
                            "primary_fail_reasons": ["required_tests_not_passed"],
                            "retry_recommendation": "retry",
                            "next_action_readiness": "retry_preparable",
                            "retry_recommended": True,
                            "escalation_required": False,
                            "retriable_failure_type": True,
                            "retriable_failure_types": [
                                "execution_failure",
                                "missing_signal",
                            ],
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            self._seed_job(
                db_path=db_path,
                job_id="job-replan",
                merge_gate_path=str(merge_gate_path),
            )

            proc = self._run(["--job-id", "job-replan", "--db-path", str(db_path), "--json"])

        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["replan_input"]["failure_type"], "execution_failure")
        self.assertEqual(payload["replan_input"]["retry_recommendation"], "retry")
        self.assertEqual(payload["replan_input"]["retry_budget_remaining"], 1)

    def test_handles_null_or_missing_artifact_paths_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            missing_merge_gate_path = tmp_root / "does_not_exist_merge_gate.json"
            self._seed_job(
                db_path=db_path,
                job_id="job-missing-artifacts",
                rubric_path=None,
                merge_gate_path=str(missing_merge_gate_path),
            )

            proc = self._run(
                [
                    "--job-id",
                    "job-missing-artifacts",
                    "--db-path",
                    str(db_path),
                    "--json",
                ]
            )

        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertIsNone(payload["paths"]["rubric"])
        self.assertEqual(payload["paths"]["merge_gate"], str(missing_merge_gate_path))
        self.assertEqual(payload["fail_reasons"]["rubric"], [])
        self.assertEqual(payload["fail_reasons"]["merge_gate"], [])

    def test_inspection_does_not_mutate_db_or_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            rubric_path = tmp_root / "rubric.json"
            merge_gate_path = tmp_root / "merge_gate.json"
            rubric_path.write_text(json.dumps({"fail_reasons": ["r1"]}), encoding="utf-8")
            merge_gate_path.write_text(json.dumps({"fail_reasons": ["m1"]}), encoding="utf-8")
            self._seed_job(
                db_path=db_path,
                job_id="job-no-mutate",
                rubric_path=str(rubric_path),
                merge_gate_path=str(merge_gate_path),
            )

            db_before = db_path.read_bytes()
            rubric_before = rubric_path.read_text(encoding="utf-8")
            merge_before = merge_gate_path.read_text(encoding="utf-8")

            proc = self._run(["--job-id", "job-no-mutate", "--db-path", str(db_path), "--json"])

            db_after = db_path.read_bytes()
            rubric_after = rubric_path.read_text(encoding="utf-8")
            merge_after = merge_gate_path.read_text(encoding="utf-8")

        self.assertEqual(proc.returncode, 0)
        self.assertEqual(db_before, db_after)
        self.assertEqual(rubric_before, rubric_after)
        self.assertEqual(merge_before, merge_after)

    def test_usage_error_when_both_job_id_and_latest_are_supplied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "state" / "jobs.db"
            self._seed_job(db_path=db_path, job_id="job-both")
            proc = self._run(
                ["--job-id", "job-both", "--latest", "--db-path", str(db_path)]
            )

        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("not allowed with argument", proc.stderr)

    def test_usage_error_when_neither_job_id_nor_latest_is_supplied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "state" / "jobs.db"
            self._seed_job(db_path=db_path, job_id="job-neither")
            proc = self._run(["--db-path", str(db_path)])

        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("one of the arguments --job-id --latest is required", proc.stderr)

    def test_inspect_surfaces_rollback_traceability_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "state" / "jobs.db"
            self._seed_job(db_path=db_path, job_id="job-rollback-trace")
            candidate_key = record_execution_target(
                db_path=db_path,
                job_id="job-rollback-trace",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                created_at="2026-04-12T00:00:00+00:00",
            )
            record_merge_execution_outcome(
                db_path=db_path,
                job_id="job-rollback-trace",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                execution_status="succeeded",
                executed_at="2026-04-12T00:10:00+00:00",
                pre_merge_sha="b" * 40,
                post_merge_sha="c" * 40,
                merge_result_sha="c" * 40,
                merge_error=None,
            )
            record_rollback_traceability_for_candidate(
                candidate_idempotency_key=candidate_key,
                db_path=db_path,
            )

            proc = self._run(["--job-id", "job-rollback-trace", "--db-path", str(db_path), "--json"])

        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["rollback_trace"]["recorded"])
        self.assertTrue(payload["rollback_trace"]["rollback_eligible"])
        self.assertEqual(payload["rollback_trace"]["pre_merge_sha"], "b" * 40)
        self.assertEqual(payload["rollback_trace"]["post_merge_sha"], "c" * 40)

    def test_inspect_surfaces_rollback_execution_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "state" / "jobs.db"
            self._seed_job(db_path=db_path, job_id="job-rollback-execution")
            candidate_key = record_execution_target(
                db_path=db_path,
                job_id="job-rollback-execution",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                created_at="2026-04-12T00:00:00+00:00",
            )
            record_merge_execution_outcome(
                db_path=db_path,
                job_id="job-rollback-execution",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                execution_status="succeeded",
                executed_at="2026-04-12T00:10:00+00:00",
                pre_merge_sha="b" * 40,
                post_merge_sha="c" * 40,
                merge_result_sha="c" * 40,
                merge_error=None,
            )
            trace = record_rollback_traceability_for_candidate(
                candidate_idempotency_key=candidate_key,
                db_path=db_path,
            )
            record_rollback_execution_outcome(
                rollback_trace_id=str(trace["rollback_trace_id"]),
                execution_status="succeeded",
                attempted_at="2026-04-12T00:20:00+00:00",
                current_head_sha="c" * 40,
                rollback_result_sha="d" * 40,
                rollback_error=None,
                consistency_check_passed=True,
                db_path=db_path,
            )

            proc = self._run(["--job-id", "job-rollback-execution", "--db-path", str(db_path), "--json"])

        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["rollback_execution"]["recorded"])
        self.assertEqual(payload["rollback_execution"]["status"], "succeeded")
        self.assertEqual(payload["rollback_execution"]["rollback_result_sha"], "d" * 40)

    def test_inspect_surfaces_machine_review_recommendation_when_payload_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            job_id = "job-machine-review"
            self._seed_job(db_path=db_path, job_id=job_id)
            machine_payload_path = tmp_root / "artifacts" / f"{job_id}_machine_review_payload.json"
            machine_payload_path.parent.mkdir(parents=True, exist_ok=True)
            machine_payload_path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "job_id": job_id,
                        "recommended_action": "retry",
                        "policy_version": "deterministic_review_policy.v1",
                        "policy_reasons": ["rollback_execution_failed_retry_candidate"],
                        "requires_human_review": True,
                        "retry_metadata": {
                            "retry_recommended": True,
                            "retry_basis": ["rollback_execution_failed_retry_candidate"],
                            "retry_blockers": [],
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            record_machine_review_payload_path(
                db_path=db_path,
                job_id=job_id,
                machine_review_payload_path=str(machine_payload_path),
            )

            proc = self._run(["--job-id", job_id, "--db-path", str(db_path), "--json"])

        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["machine_review"]["recommended_action"], "retry")
        self.assertEqual(
            payload["machine_review"]["policy_version"],
            "deterministic_review_policy.v1",
        )
        self.assertEqual(
            payload["machine_review"]["policy_reasons"],
            ["rollback_execution_failed_retry_candidate"],
        )
        self.assertTrue(payload["machine_review"]["requires_human_review"])
        self.assertEqual(
            payload["machine_review"]["retry_metadata"]["retry_recommended"],
            True,
        )
        self.assertEqual(
            payload["machine_review"]["retry_metadata"]["retry_basis"],
            ["rollback_execution_failed_retry_candidate"],
        )
        self.assertEqual(
            payload["machine_review"]["retry_metadata"]["retry_blockers"],
            [],
        )
        self.assertEqual(
            payload["machine_review"]["advisory"]["display_recommendation"],
            "retry",
        )
        self.assertEqual(
            payload["machine_review"]["advisory"]["decision_confidence"],
            "low",
        )
        self.assertIn(
            "rollback_execution_failed_retry_candidate",
            payload["machine_review"]["advisory"]["operator_attention_flags"],
        )
        self.assertFalse(payload["machine_review"]["advisory"]["execution_allowed"])
        self.assertFalse(
            payload["machine_review"]["execution_bridge"]["eligible_for_bounded_execution"]
        )
        self.assertEqual(payload["machine_review"]["execution_bridge"]["eligibility_basis"], [])
        self.assertEqual(
            payload["machine_review"]["execution_bridge"]["eligibility_blockers"],
            [
                "rollback_execution_failed_retry_candidate",
                "explicit_operator_gate_required",
                "execution_not_implemented",
            ],
        )
        self.assertTrue(
            payload["machine_review"]["execution_bridge"][
                "requires_explicit_operator_decision"
            ]
        )
        self.assertEqual(
            payload["machine_review"]["mode_visibility"]["current_mode"],
            "manual_review_only",
        )
        self.assertIsNone(
            payload["machine_review"]["mode_visibility"]["next_possible_mode"]
        )
        self.assertEqual(
            payload["machine_review"]["mode_visibility"]["mode_basis"],
            [
                "ledger_backed_machine_review_visible",
                "explicit_operator_decision_required",
            ],
        )
        self.assertEqual(
            payload["machine_review"]["mode_visibility"]["mode_blockers"],
            [
                "rollback_execution_failed_retry_candidate",
                "explicit_operator_gate_required",
                "execution_not_implemented",
            ],
        )

    def test_inspect_handles_older_machine_review_payload_without_retry_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            job_id = "job-machine-review-old-payload"
            self._seed_job(db_path=db_path, job_id=job_id)
            machine_payload_path = tmp_root / "artifacts" / f"{job_id}_machine_review_payload.json"
            machine_payload_path.parent.mkdir(parents=True, exist_ok=True)
            machine_payload_path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "job_id": job_id,
                        "recommended_action": "keep",
                        "policy_version": "deterministic_review_policy.v1",
                        "policy_reasons": ["validation_passed_and_merge_policy_green"],
                        "requires_human_review": True,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            record_machine_review_payload_path(
                db_path=db_path,
                job_id=job_id,
                machine_review_payload_path=str(machine_payload_path),
            )

            proc = self._run(["--job-id", job_id, "--db-path", str(db_path), "--json"])

        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(
            payload["machine_review"]["retry_metadata"]["retry_recommended"],
            None,
        )
        self.assertEqual(payload["machine_review"]["retry_metadata"]["retry_basis"], [])
        self.assertEqual(
            payload["machine_review"]["retry_metadata"]["retry_blockers"],
            [],
        )
        self.assertEqual(
            payload["machine_review"]["advisory"]["display_recommendation"],
            "keep",
        )
        self.assertEqual(
            payload["machine_review"]["advisory"]["decision_confidence"],
            "low",
        )
        self.assertIn(
            "validation_passed_and_merge_policy_green",
            payload["machine_review"]["advisory"]["operator_attention_flags"],
        )
        self.assertFalse(payload["machine_review"]["advisory"]["execution_allowed"])
        self.assertFalse(
            payload["machine_review"]["execution_bridge"]["eligible_for_bounded_execution"]
        )
        self.assertEqual(payload["machine_review"]["execution_bridge"]["eligibility_basis"], [])
        self.assertEqual(
            payload["machine_review"]["execution_bridge"]["eligibility_blockers"],
            [
                "validation_passed_and_merge_policy_green",
                "explicit_operator_gate_required",
                "execution_not_implemented",
            ],
        )
        self.assertTrue(
            payload["machine_review"]["execution_bridge"][
                "requires_explicit_operator_decision"
            ]
        )
        self.assertEqual(
            payload["machine_review"]["mode_visibility"]["current_mode"],
            "manual_review_only",
        )
        self.assertIsNone(
            payload["machine_review"]["mode_visibility"]["next_possible_mode"]
        )
        self.assertEqual(
            payload["machine_review"]["mode_visibility"]["mode_basis"],
            [
                "ledger_backed_machine_review_visible",
                "explicit_operator_decision_required",
            ],
        )
        self.assertEqual(
            payload["machine_review"]["mode_visibility"]["mode_blockers"],
            [
                "validation_passed_and_merge_policy_green",
                "explicit_operator_gate_required",
                "execution_not_implemented",
            ],
        )

    def test_inspect_surfaces_recovery_policy_shape_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            job_id = "job-recovery-policy-shape"
            self._seed_job(db_path=db_path, job_id=job_id)
            machine_payload_path = tmp_root / "artifacts" / f"{job_id}_machine_review_payload.json"
            machine_payload_path.parent.mkdir(parents=True, exist_ok=True)
            machine_payload_path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.1",
                        "job_id": job_id,
                        "policy_version": "deterministic_review_policy.v2",
                        "score_total": 8.4,
                        "dimension_scores": {
                            "correctness": 3.1,
                            "scope_control": 1.8,
                            "safety": 2.0,
                            "repo_alignment": 1.5,
                        },
                        "failure_codes": ["insufficient_tests"],
                        "recovery_decision": "revise_current_state",
                        "decision_basis": ["required_tests_not_passed"],
                        "requires_human_review": True,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            record_machine_review_payload_path(
                db_path=db_path,
                job_id=job_id,
                machine_review_payload_path=str(machine_payload_path),
            )

            proc = self._run(["--job-id", job_id, "--db-path", str(db_path), "--json"])

        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["machine_review"]["recovery_decision"], "revise_current_state")
        self.assertEqual(payload["machine_review"]["recommended_action"], "revise_current_state")
        self.assertEqual(payload["machine_review"]["score_total"], 8.4)
        self.assertEqual(
            payload["machine_review"]["dimension_scores"]["scope_control"],
            1.8,
        )
        self.assertEqual(payload["machine_review"]["failure_codes"], ["insufficient_tests"])
        self.assertEqual(payload["machine_review"]["decision_basis"], ["required_tests_not_passed"])
        self.assertEqual(
            payload["machine_review"]["advisory"]["display_recommendation"],
            "revise_current_state",
        )

    def test_inspect_handles_machine_review_payload_without_advisory_or_execution_bridge_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            job_id = "job-machine-review-no-advisory-bridge"
            self._seed_job(db_path=db_path, job_id=job_id)
            machine_payload_path = tmp_root / "artifacts" / f"{job_id}_machine_review_payload.json"
            machine_payload_path.parent.mkdir(parents=True, exist_ok=True)
            machine_payload_path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "job_id": job_id,
                        "recommended_action": "escalate",
                        "policy_version": "deterministic_review_policy.v1",
                        "policy_reasons": ["validation_status_missing"],
                        "requires_human_review": True,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            record_machine_review_payload_path(
                db_path=db_path,
                job_id=job_id,
                machine_review_payload_path=str(machine_payload_path),
            )

            proc = self._run(["--job-id", job_id, "--db-path", str(db_path), "--json"])

        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(
            payload["machine_review"]["mode_visibility"]["current_mode"],
            "manual_review_only",
        )
        self.assertIsNone(
            payload["machine_review"]["mode_visibility"]["next_possible_mode"]
        )
        self.assertEqual(
            payload["machine_review"]["mode_visibility"]["mode_basis"],
            [
                "ledger_backed_machine_review_visible",
                "explicit_operator_decision_required",
            ],
        )
        self.assertEqual(
            payload["machine_review"]["mode_visibility"]["mode_blockers"],
            [
                "validation_status_missing",
                "explicit_operator_gate_required",
                "execution_not_implemented",
            ],
        )

    def test_inspect_keeps_machine_review_unrecorded_without_ledger_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            job_id = "job-machine-review-unrecorded"
            self._seed_job(db_path=db_path, job_id=job_id)
            loose_payload_path = tmp_root / "state" / f"{job_id}_machine_review_payload.json"
            loose_payload_path.write_text(
                json.dumps(
                    {
                        "job_id": job_id,
                        "recommended_action": "keep",
                        "policy_version": "deterministic_review_policy.v1",
                        "policy_reasons": ["validation_passed_and_merge_policy_green"],
                        "requires_human_review": True,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            proc = self._run(["--job-id", job_id, "--db-path", str(db_path), "--json"])

        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertIsNone(payload["paths"]["machine_review_payload"])
        self.assertFalse(payload["machine_review"]["recorded"])
        self.assertIsNone(payload["machine_review"]["recommended_action"])
        self.assertIsNone(payload["machine_review"]["policy_version"])
        self.assertEqual(payload["machine_review"]["policy_reasons"], [])
        self.assertIsNone(payload["machine_review"]["requires_human_review"])
        self.assertEqual(
            payload["machine_review"]["retry_metadata"],
            {
                "retry_recommended": None,
                "retry_basis": [],
                "retry_blockers": [],
            },
        )
        self.assertEqual(
            payload["machine_review"]["advisory"],
            {
                "display_recommendation": None,
                "decision_confidence": None,
                "operator_attention_flags": [],
                "execution_allowed": False,
            },
        )
        self.assertEqual(
            payload["machine_review"]["execution_bridge"],
            {
                "eligible_for_bounded_execution": False,
                "eligibility_basis": [],
                "eligibility_blockers": [
                    "explicit_operator_gate_required",
                    "execution_not_implemented",
                ],
                "requires_explicit_operator_decision": True,
            },
        )
        self.assertEqual(
            payload["machine_review"]["mode_visibility"],
            {
                "current_mode": "manual_review_only",
                "next_possible_mode": None,
                "mode_basis": ["explicit_operator_decision_required"],
                "mode_blockers": [
                    "explicit_operator_gate_required",
                    "execution_not_implemented",
                ],
            },
        )


if __name__ == "__main__":
    unittest.main()
