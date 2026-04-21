from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from orchestrator.ledger import get_rollback_execution_by_job_id
from orchestrator.ledger import record_execution_target
from orchestrator.ledger import record_job_evaluation
from orchestrator.ledger import record_merge_execution_outcome
from orchestrator.ledger import record_rollback_execution_outcome
from orchestrator.ledger import record_rollback_traceability_for_candidate


class BuildOperatorSummaryCliTests(unittest.TestCase):
    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _script_path(self) -> Path:
        return self._repo_root() / "scripts" / "build_operator_summary.py"

    def _inspect_script_path(self) -> Path:
        return self._repo_root() / "scripts" / "inspect_job.py"

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self._script_path()), *args],
            capture_output=True,
            text=True,
            cwd=self._repo_root(),
        )

    def _run_inspect(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self._inspect_script_path()), *args],
            capture_output=True,
            text=True,
            cwd=self._repo_root(),
        )

    def _seed_job(
        self,
        *,
        db_path: Path,
        job_id: str,
        created_at: str,
        verify_status: str | None,
        verify_reason: str | None,
        merge_gate_payload: dict[str, object] | None = None,
        result_path_override: str | None = None,
    ) -> tuple[Path, Path]:
        request_path = db_path.parent / f"{job_id}_request.json"
        result_path = (
            Path(result_path_override)
            if isinstance(result_path_override, str) and result_path_override.strip()
            else db_path.parent / f"{job_id}_result.json"
        )
        merge_gate_path = db_path.parent / f"{job_id}_merge_gate.json"
        request_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        request_path.write_text(
            json.dumps({"job_id": job_id}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        execution = {}
        if verify_status is not None:
            execution = {"verify": {"status": verify_status, "reason": verify_reason}}
        result_path.write_text(
            json.dumps({"job_id": job_id, "execution": execution}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if merge_gate_payload is not None:
            merge_gate_path.write_text(
                json.dumps(merge_gate_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
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
            rubric_path=None,
            merge_gate_path=str(merge_gate_path) if merge_gate_payload is not None else None,
            classification_path=None,
        )
        return request_path, result_path

    def _seed_candidate_with_merge_execution(
        self,
        *,
        db_path: Path,
        job_id: str,
        execution_status: str,
        pre_merge_sha: str,
        post_merge_sha: str,
    ) -> str:
        candidate_key = record_execution_target(
            db_path=db_path,
            job_id=job_id,
            repo="codex-local-runner",
            target_ref="refs/heads/main",
            source_sha="a" * 40,
            base_sha="b" * 40,
            created_at="2026-04-13T00:00:00+00:00",
        )
        record_merge_execution_outcome(
            db_path=db_path,
            job_id=job_id,
            repo="codex-local-runner",
            target_ref="refs/heads/main",
            source_sha="a" * 40,
            base_sha="b" * 40,
            execution_status=execution_status,
            executed_at="2026-04-13T00:10:00+00:00",
            pre_merge_sha=pre_merge_sha,
            post_merge_sha=post_merge_sha,
            merge_result_sha=post_merge_sha,
            merge_error=None,
        )
        return candidate_key

    def _build_and_read_machine_payload(
        self,
        *,
        db_path: Path,
        job_id: str,
        out_dir: Path,
    ) -> dict[str, object]:
        proc = self._run(
            [
                "--job-id",
                job_id,
                "--db-path",
                str(db_path),
                "--out-dir",
                str(out_dir),
            ]
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload_path = out_dir / f"{job_id}_machine_review_payload.json"
        self.assertTrue(payload_path.exists())
        return json.loads(payload_path.read_text(encoding="utf-8"))

    def test_builds_json_and_html_summary_for_job_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            self._seed_job(
                db_path=db_path,
                job_id="job-summary-1",
                created_at="2026-04-13T00:00:00+00:00",
                verify_status="passed",
                verify_reason="all_commands_passed",
            )
            out_dir = tmp_root / "out"

            proc = self._run(
                ["--job-id", "job-summary-1", "--db-path", str(db_path), "--out-dir", str(out_dir)]
            )

            json_path = out_dir / "job-summary-1_operator_summary.json"
            html_path = out_dir / "job-summary-1_operator_summary.html"
            machine_path = out_dir / "job-summary-1_machine_review_payload.json"
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            self.assertTrue(json_path.exists())
            self.assertTrue(html_path.exists())
            self.assertTrue(machine_path.exists())
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            machine_payload = json.loads(machine_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["job_id"], "job-summary-1")
            self.assertEqual(payload["repo"], "codex-local-runner")
            self.assertEqual(payload["accepted_status"], "accepted")
            self.assertEqual(payload["validation"]["verify_status"], "passed")
            self.assertIsNone(payload["lifecycle_state"])
            self.assertEqual(payload["write_authority"]["state"], None)
            self.assertEqual(payload["write_authority"]["allowed_categories"], [])
            self.assertEqual(payload["failure_type"], None)
            self.assertEqual(payload["retry_recommended"], None)
            self.assertEqual(payload["retry_recommendation"], None)
            self.assertEqual(payload["retry_budget_remaining"], None)
            self.assertEqual(payload["escalation_required"], None)
            self.assertEqual(payload["next_action_readiness"], None)
            self.assertEqual(payload["primary_fail_reasons"], [])
            self.assertEqual(payload["merge"]["merge_eligible"], True)
            self.assertEqual(payload["merge"]["merge_gate_passed"], True)
            self.assertIn("request", payload["paths"])
            self.assertIn("result", payload["paths"])
            self.assertEqual(machine_payload["schema_version"], "1.1")
            self.assertEqual(
                machine_payload["action_vocabulary"],
                ["keep", "revise_current_state", "reset_and_retry", "escalate"],
            )

            self.assertEqual(machine_payload["job_id"], "job-summary-1")
            self.assertEqual(machine_payload["repo"], "codex-local-runner")
            self.assertEqual(machine_payload["accepted_status"], "accepted")
            self.assertEqual(machine_payload["merge_eligible"], True)
            self.assertEqual(machine_payload["rollback_eligible"], None)
            self.assertEqual(machine_payload["requires_human_review"], True)
            self.assertEqual(machine_payload["recommended_action"], "escalate")
            self.assertEqual(
                machine_payload["policy_version"],
                "deterministic_review_policy.v2",
            )
            self.assertEqual(
                machine_payload["policy_reasons"],
                ["contract_drift", "insufficient_tests"],
            )
            self.assertIsNone(
                machine_payload["retry_metadata"]["retry_recommended"],
            )
            self.assertEqual(
                machine_payload["retry_metadata"]["retry_basis"],
                [],
            )
            self.assertEqual(
                machine_payload["retry_metadata"]["retry_blockers"],
                [
                    "execution_status_missing",
                    "validation_passed",
                    "required_tests_not_declared",
                    "forbidden_path_signal_missing",
                    "diff_size_signal_missing",
                    "changed_files_missing_or_empty",
                    "runtime_semantics_signal_missing",
                    "contract_shape_signal_missing",
                    "reviewer_fields_signal_missing",
                    "prompt_contract_signal_missing",
                    "blocking_failure_code:contract_drift",
                ],
            )
            self.assertEqual(machine_payload["lifecycle_state"], None)
            self.assertEqual(machine_payload["write_authority"]["state"], None)
            self.assertEqual(machine_payload["write_authority"]["allowed_categories"], [])
            self.assertEqual(machine_payload["failure_type"], None)
            self.assertEqual(machine_payload["retry_recommended"], None)
            self.assertEqual(machine_payload["retry_recommendation"], None)
            self.assertEqual(machine_payload["retry_budget_remaining"], None)
            self.assertEqual(machine_payload["escalation_required"], None)
            self.assertEqual(machine_payload["next_action_readiness"], None)
            self.assertEqual(machine_payload["primary_fail_reasons"], [])
            self.assertIn("operator_summary_json", machine_payload["artifact_references"])
            self.assertIn("operator_summary_html", machine_payload["artifact_references"])
            self.assertIn("machine_review_payload", machine_payload["artifact_references"])

            html = html_path.read_text(encoding="utf-8")
            self.assertIn('<meta name="viewport" content="width=device-width, initial-scale=1">', html)
            self.assertIn("Operator Summary", html)

    def test_summary_surfaces_lifecycle_artifacts_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            run_root = tmp_root / "runs" / "job-summary-lifecycle"
            unit_dir = run_root / "pr-01"
            unit_dir.mkdir(parents=True, exist_ok=True)
            result_path = unit_dir / "result.json"
            result_path.write_text(
                json.dumps({"job_id": "job-summary-lifecycle", "execution": {}}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (unit_dir / "checkpoint_decision.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "unit_id": "pr-01",
                        "checkpoint_stage": "post_review",
                        "decision": "pause",
                        "rule_id": "checkpoint_pause_recommended",
                        "summary": "paused for manual gate",
                        "blocking_reasons": ["manual_review_required"],
                        "required_signals": ["manual_review_required"],
                        "recommended_next_action": "signal_recollect",
                        "manual_intervention_required": True,
                        "global_stop_recommended": False,
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
                        "decision": "blocked",
                        "rule_id": "merge_blocked_not_requested",
                        "summary": "blocked",
                        "blocking_reasons": ["merge_not_requested"],
                        "required_signals": ["review_passed"],
                        "recommended_next_action": "proceed_to_pr",
                        "readiness_status": "awaiting_prerequisites",
                        "readiness_next_action": "resolve_blockers",
                        "automation_eligible": False,
                        "manual_intervention_required": False,
                        "unresolved_blockers": ["merge_not_requested", "commit_readiness_not_ready"],
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
                        "decision": "not_required",
                        "rule_id": "rollback_not_required_success_path",
                        "summary": "not required",
                        "blocking_reasons": [],
                        "required_signals": ["review_passed"],
                        "recommended_next_action": "proceed_to_pr",
                        "readiness_status": "not_ready",
                        "readiness_next_action": "hold",
                        "automation_eligible": False,
                        "manual_intervention_required": True,
                        "unresolved_blockers": [],
                        "prerequisites_satisfied": False,
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
                        "status": "succeeded",
                        "summary": "commit execution succeeded",
                        "started_at": "2026-04-18T02:00:00",
                        "finished_at": "2026-04-18T02:00:01",
                        "commit_sha": "abc123",
                        "command_summary": {"git_commit_rc": 0},
                        "failure_reason": "",
                        "manual_intervention_required": False,
                        "blocking_reasons": [],
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
                        "started_at": "2026-04-18T02:00:02",
                        "finished_at": "2026-04-18T02:00:03",
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
                        "started_at": "2026-04-18T02:00:04",
                        "finished_at": "2026-04-18T02:00:05",
                        "branch_name": "feature",
                        "remote_name": "origin",
                        "base_branch": "main",
                        "head_branch": "feature",
                        "pr_number": 456,
                        "pr_url": "https://example.local/pr/456",
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
                        "status": "succeeded",
                        "summary": "merge succeeded",
                        "started_at": "2026-04-18T02:00:06",
                        "finished_at": "2026-04-18T02:00:07",
                        "branch_name": "feature",
                        "remote_name": "origin",
                        "base_branch": "main",
                        "head_branch": "feature",
                        "pr_number": 456,
                        "merge_commit_sha": "def456",
                        "command_summary": {"merge_status": "success"},
                        "failure_reason": "",
                        "manual_intervention_required": False,
                        "blocking_reasons": [],
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
                        "rollback_mode": "merged",
                        "status": "succeeded",
                        "summary": "rollback execution succeeded",
                        "started_at": "2026-04-18T01:00:08",
                        "finished_at": "2026-04-18T01:00:09",
                        "trigger_reason": "rollback_required",
                        "source_execution_state_summary": {"mode": "merged"},
                        "resulting_commit_sha": "fedcba",
                        "resulting_pr_state": "unchanged",
                        "resulting_branch_state": {"target_branch": "main"},
                        "command_summary": {"git_revert_rc": 0},
                        "failure_reason": "",
                        "manual_intervention_required": False,
                        "replan_required": True,
                        "automatic_continuation_blocked": True,
                        "blocking_reasons": [],
                        "attempted": True,
                        "rollback_aftermath_status": "remote_followup_required",
                        "rollback_aftermath_blocked": True,
                        "rollback_aftermath_blocked_reason": "rollback_remote_followup_required",
                        "rollback_aftermath_blocked_reasons": [
                            "rollback_remote_followup_required",
                            "rollback_post_validation_unavailable",
                        ],
                        "rollback_aftermath_missing_or_ambiguous": True,
                        "rollback_validation_status": "unavailable",
                        "rollback_manual_followup_required": True,
                        "rollback_remote_followup_required": True,
                        "rollback_post_validation_status": "unavailable",
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
                        "run_id": "job-summary-lifecycle",
                        "state": "paused",
                        "orchestration_state": "paused_for_manual_review",
                        "summary": "waiting for manual action",
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
                        "loop_state": "replan_required",
                        "next_safe_action": "require_replanning",
                        "loop_blocked_reason": "rollback_replan_required",
                        "loop_blocked_reasons": ["rollback_replan_required"],
                        "resumable": False,
                        "terminal": False,
                        "loop_manual_intervention_required": True,
                        "loop_replan_required": True,
                        "rollback_completed": True,
                        "delivery_completed": True,
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
                                "manual_required": 0,
                                "blocked": 0,
                                "awaiting_prerequisites": 1,
                            },
                            "rollback": {
                                "ready": 0,
                                "not_ready": 1,
                                "manual_required": 0,
                                "blocked": 0,
                                "awaiting_prerequisites": 0,
                            },
                        },
                        "readiness_blocked": True,
                        "readiness_manual_required": False,
                        "readiness_awaiting_prerequisites": True,
                        "commit_execution_summary": {
                            "succeeded": 1,
                            "failed": 0,
                            "blocked": 0,
                        },
                        "commit_execution_executed": True,
                        "commit_execution_pending": False,
                        "commit_execution_failed": False,
                        "commit_execution_manual_intervention_required": False,
                        "push_execution_summary": {"succeeded": 1, "failed": 0, "blocked": 0},
                        "pr_execution_summary": {"succeeded": 1, "failed": 0, "blocked": 0},
                        "merge_execution_summary": {"succeeded": 1, "failed": 0, "blocked": 0},
                        "push_execution_succeeded": True,
                        "pr_execution_succeeded": True,
                        "merge_execution_succeeded": True,
                        "push_execution_pending": False,
                        "pr_execution_pending": False,
                        "merge_execution_pending": False,
                        "push_execution_failed": False,
                        "pr_execution_failed": False,
                        "merge_execution_failed": False,
                        "delivery_execution_manual_intervention_required": False,
                        "rollback_execution_summary": {"succeeded": 1, "failed": 0, "blocked": 0},
                        "rollback_execution_attempted": True,
                        "rollback_execution_succeeded": True,
                        "rollback_execution_pending": False,
                        "rollback_execution_failed": False,
                        "rollback_execution_manual_intervention_required": False,
                        "rollback_replan_required": True,
                        "rollback_automatic_continuation_blocked": True,
                        "rollback_aftermath_summary": {
                            "completed_safe": 0,
                            "completed_manual_followup_required": 0,
                            "blocked": 0,
                            "incomplete": 0,
                            "ambiguous": 0,
                            "validation_failed": 0,
                            "remote_followup_required": 1,
                        },
                        "rollback_aftermath_status": "remote_followup_required",
                        "rollback_aftermath_blocked": True,
                        "rollback_aftermath_manual_required": True,
                        "rollback_aftermath_missing_or_ambiguous": True,
                        "rollback_aftermath_blocked_reason": "rollback_remote_followup_required",
                        "rollback_aftermath_blocked_reasons": [
                            "rollback_remote_followup_required",
                            "rollback_post_validation_unavailable",
                        ],
                        "rollback_remote_followup_required": True,
                        "rollback_manual_followup_required": True,
                        "rollback_validation_failed": False,
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
                        "policy_blocked_reason": "rollback_remote_followup_required",
                        "policy_blocked_reasons": [
                            "rollback_remote_followup_required",
                            "required_checks_unsatisfied",
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
                        "objective_id": "objective-job-summary-lifecycle",
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
                        "run_id": "job-summary-lifecycle",
                        "objective_id": "objective-job-summary-lifecycle",
                        "objective_summary": "Safely complete delivery",
                        "objective_type": "implementation",
                        "requested_outcome": "safe closure with objective evidence",
                        "in_scope": ["scripts/build_operator_summary.py"],
                        "out_of_scope": ["automation/control/next_action_controller.py"],
                        "acceptance_criteria": [
                            {
                                "criterion_id": "criterion_001",
                                "kind": "acceptance_criterion",
                                "status": "defined",
                                "text": "Objective artifact is visible in operator summary",
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
                        "run_id": "job-summary-lifecycle",
                        "objective_id": "objective-job-summary-lifecycle",
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
                        "execution_complete_not_accepted": False,
                        "rollback_complete_not_closed": True,
                        "delivery_complete_waiting_external_truth": False,
                        "lifecycle_alignment_status": "partially_aligned",
                        "lifecycle_closure_status": "rollback_complete_not_closed",
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
                        "run_id": "job-summary-lifecycle",
                        "objective_id": "objective-job-summary-lifecycle",
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
                        "run_id": "job-summary-lifecycle",
                        "objective_id": "objective-job-summary-lifecycle",
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
                        "reconcile_lifecycle_status": "rollback_complete_not_closed",
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
                        "run_id": "job-summary-lifecycle",
                        "objective_id": "objective-job-summary-lifecycle",
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
                        "repair_lifecycle_status": "rollback_complete_not_closed",
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
                        "run_id": "job-summary-lifecycle",
                        "objective_id": "objective-job-summary-lifecycle",
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
                        "run_id": "job-summary-lifecycle",
                        "objective_id": "objective-job-summary-lifecycle",
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
                        "run_id": "job-summary-lifecycle",
                        "objective_id": "objective-job-summary-lifecycle",
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
                        "run_id": "job-summary-lifecycle",
                        "objective_id": "objective-job-summary-lifecycle",
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
                job_id="job-summary-lifecycle",
                created_at="2026-04-13T00:00:00+00:00",
                verify_status=None,
                verify_reason=None,
                result_path_override=str(result_path),
            )
            out_dir = tmp_root / "out"

            proc = self._run(
                [
                    "--job-id",
                    "job-summary-lifecycle",
                    "--db-path",
                    str(db_path),
                    "--out-dir",
                    str(out_dir),
                ]
            )
            inspect_proc = self._run_inspect(
                [
                    "--job-id",
                    "job-summary-lifecycle",
                    "--db-path",
                    str(db_path),
                    "--json",
                ]
            )

            summary_path = out_dir / "job-summary-lifecycle_operator_summary.json"
            machine_path = out_dir / "job-summary-lifecycle_machine_review_payload.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            machine_payload = json.loads(machine_path.read_text(encoding="utf-8"))

        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertEqual(inspect_proc.returncode, 0, msg=inspect_proc.stderr)
        inspect_payload = json.loads(inspect_proc.stdout)
        self.assertEqual(summary["lifecycle_artifacts"]["checkpoint_decision"]["decision"], "pause")
        self.assertTrue(summary["lifecycle_artifacts"]["checkpoint_decision"]["manual_intervention_required"])
        self.assertEqual(summary["lifecycle_artifacts"]["commit_decision"]["decision"], "blocked")
        self.assertEqual(summary["lifecycle_artifacts"]["commit_decision"]["readiness_status"], "blocked")
        self.assertEqual(
            summary["lifecycle_artifacts"]["commit_decision"]["readiness_next_action"],
            "resolve_blockers",
        )
        self.assertEqual(summary["lifecycle_artifacts"]["merge_decision"]["decision"], "blocked")
        self.assertEqual(
            summary["lifecycle_artifacts"]["merge_decision"]["readiness_status"],
            "awaiting_prerequisites",
        )
        self.assertEqual(summary["lifecycle_artifacts"]["rollback_decision"]["decision"], "not_required")
        self.assertEqual(summary["lifecycle_artifacts"]["rollback_decision"]["readiness_status"], "not_ready")
        self.assertEqual(summary["lifecycle_artifacts"]["commit_execution"]["status"], "succeeded")
        self.assertIn("execution_authority_status", summary["lifecycle_artifacts"]["commit_execution"])
        self.assertIn("validation_status", summary["lifecycle_artifacts"]["commit_execution"])
        self.assertEqual(summary["lifecycle_artifacts"]["commit_execution"]["commit_sha"], "abc123")
        self.assertEqual(summary["lifecycle_artifacts"]["push_execution"]["status"], "succeeded")
        self.assertEqual(
            summary["lifecycle_artifacts"]["push_execution"]["remote_state_status"],
            "non_fast_forward_risk",
        )
        self.assertTrue(summary["lifecycle_artifacts"]["push_execution"]["remote_state_blocked"])
        self.assertTrue(summary["lifecycle_artifacts"]["push_execution"]["remote_github_blocked"])
        self.assertIn("execution_authority_status", summary["lifecycle_artifacts"]["push_execution"])
        self.assertIn("validation_status", summary["lifecycle_artifacts"]["push_execution"])
        self.assertEqual(summary["lifecycle_artifacts"]["pr_execution"]["status"], "succeeded")
        self.assertEqual(
            summary["lifecycle_artifacts"]["pr_execution"]["existing_pr_status"],
            "existing_open",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["pr_execution"]["pr_creation_state_status"],
            "blocked_existing_pr",
        )
        self.assertIn("execution_authority_status", summary["lifecycle_artifacts"]["pr_execution"])
        self.assertIn("validation_status", summary["lifecycle_artifacts"]["pr_execution"])
        self.assertEqual(summary["lifecycle_artifacts"]["pr_execution"]["pr_number"], 456)
        self.assertEqual(summary["lifecycle_artifacts"]["merge_execution"]["status"], "succeeded")
        self.assertEqual(
            summary["lifecycle_artifacts"]["merge_execution"]["mergeability_status"],
            "unknown",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["merge_execution"]["merge_requirements_status"],
            "unsatisfied",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["merge_execution"]["required_checks_status"],
            "unsatisfied",
        )
        self.assertIn("execution_authority_status", summary["lifecycle_artifacts"]["merge_execution"])
        self.assertIn("validation_status", summary["lifecycle_artifacts"]["merge_execution"])
        self.assertEqual(summary["lifecycle_artifacts"]["merge_execution"]["merge_commit_sha"], "def456")
        self.assertEqual(summary["lifecycle_artifacts"]["rollback_execution"]["status"], "succeeded")
        self.assertIn("execution_authority_status", summary["lifecycle_artifacts"]["rollback_execution"])
        self.assertIn("validation_status", summary["lifecycle_artifacts"]["rollback_execution"])
        self.assertEqual(summary["lifecycle_artifacts"]["rollback_execution"]["rollback_mode"], "merged")
        self.assertEqual(summary["lifecycle_artifacts"]["rollback_execution"]["resulting_commit_sha"], "fedcba")
        self.assertEqual(
            summary["lifecycle_artifacts"]["rollback_execution"]["rollback_aftermath_status"],
            "remote_followup_required",
        )
        self.assertTrue(
            summary["lifecycle_artifacts"]["rollback_execution"]["rollback_aftermath_blocked"]
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["rollback_execution"]["rollback_aftermath_blocked_reason"],
            "rollback_remote_followup_required",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["rollback_execution"]["rollback_validation_status"],
            "unavailable",
        )
        self.assertTrue(
            summary["lifecycle_artifacts"]["rollback_execution"]["rollback_manual_followup_required"]
        )
        self.assertTrue(
            summary["lifecycle_artifacts"]["rollback_execution"]["rollback_remote_followup_required"]
        )
        self.assertEqual(summary["lifecycle_artifacts"]["run_state"]["state"], "paused")
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["orchestration_state"],
            "paused_for_manual_review",
        )
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["global_stop"])
        self.assertFalse(summary["lifecycle_artifacts"]["run_state"]["continue_allowed"])
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["run_paused"])
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["manual_intervention_required"])
        self.assertFalse(summary["lifecycle_artifacts"]["run_state"]["rollback_evaluation_pending"])
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["global_stop_recommended"])
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["next_run_action"],
            "hold_for_global_stop",
        )
        self.assertEqual(summary["lifecycle_artifacts"]["run_state"]["loop_state"], "replan_required")
        self.assertEqual(summary["lifecycle_artifacts"]["run_state"]["next_safe_action"], "require_replanning")
        self.assertEqual(summary["lifecycle_artifacts"]["run_state"]["loop_blocked_reason"], "rollback_replan_required")
        self.assertFalse(summary["lifecycle_artifacts"]["run_state"]["resumable"])
        self.assertFalse(summary["lifecycle_artifacts"]["run_state"]["terminal"])
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["loop_manual_intervention_required"])
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["loop_replan_required"])
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["rollback_completed"])
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["delivery_completed"])
        self.assertIn("execute_merge", summary["lifecycle_artifacts"]["run_state"]["loop_allowed_actions"])
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["unit_blocked"])
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["readiness_blocked"])
        self.assertFalse(summary["lifecycle_artifacts"]["run_state"]["readiness_manual_required"])
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["readiness_awaiting_prerequisites"])
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["commit_execution_executed"])
        self.assertFalse(summary["lifecycle_artifacts"]["run_state"]["commit_execution_failed"])
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["push_execution_succeeded"])
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["pr_execution_succeeded"])
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["merge_execution_succeeded"])
        self.assertFalse(summary["lifecycle_artifacts"]["run_state"]["merge_execution_failed"])
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["rollback_execution_attempted"])
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["rollback_execution_succeeded"])
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["rollback_replan_required"])
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["rollback_aftermath_status"],
            "remote_followup_required",
        )
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["rollback_aftermath_blocked"])
        self.assertTrue(
            summary["lifecycle_artifacts"]["run_state"]["rollback_aftermath_manual_required"]
        )
        self.assertTrue(
            summary["lifecycle_artifacts"]["run_state"]["rollback_aftermath_missing_or_ambiguous"]
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["rollback_aftermath_blocked_reason"],
            "rollback_remote_followup_required",
        )
        self.assertTrue(
            summary["lifecycle_artifacts"]["run_state"]["rollback_remote_followup_required"]
        )
        self.assertTrue(
            summary["lifecycle_artifacts"]["run_state"]["rollback_manual_followup_required"]
        )
        self.assertFalse(summary["lifecycle_artifacts"]["run_state"]["rollback_validation_failed"])
        self.assertIn("authority_validation_blocked", summary["lifecycle_artifacts"]["run_state"])
        self.assertIn("execution_authority_blocked", summary["lifecycle_artifacts"]["run_state"])
        self.assertIn("validation_blocked", summary["lifecycle_artifacts"]["run_state"])
        self.assertIn("authority_validation_manual_required", summary["lifecycle_artifacts"]["run_state"])
        self.assertIn(
            "authority_validation_missing_or_ambiguous",
            summary["lifecycle_artifacts"]["run_state"],
        )
        self.assertIn("authority_validation_blocked_reason", summary["lifecycle_artifacts"]["run_state"])
        self.assertIn("authority_validation_blocked_reasons", summary["lifecycle_artifacts"]["run_state"])
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["remote_github_blocked"])
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["remote_github_manual_required"])
        self.assertTrue(
            summary["lifecycle_artifacts"]["run_state"]["remote_github_missing_or_ambiguous"]
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["remote_github_blocked_reason"],
            "required_checks_unsatisfied",
        )
        self.assertIn(
            "existing_open_pr_detected",
            summary["lifecycle_artifacts"]["run_state"]["remote_github_blocked_reasons"],
        )
        self.assertEqual(summary["lifecycle_artifacts"]["run_state"]["policy_status"], "manual_only")
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["policy_blocked"])
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["policy_manual_required"])
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["policy_replan_required"])
        self.assertFalse(summary["lifecycle_artifacts"]["run_state"]["policy_resume_allowed"])
        self.assertFalse(summary["lifecycle_artifacts"]["run_state"]["policy_terminal"])
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["policy_blocked_reason"],
            "rollback_remote_followup_required",
        )
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["objective_contract_present"])
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["objective_id"],
            "objective-job-summary-lifecycle",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["objective_summary"],
            "Safely complete delivery",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["requested_outcome"],
            "safe closure with objective evidence",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["objective_contract_status"],
            "underspecified",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["objective_acceptance_status"],
            "partially_defined",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["objective_scope_status"],
            "clear",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["objective_required_artifacts_status"],
            "defined",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["objective_contract_blocked_reason"],
            "acceptance_partially_defined",
        )
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["completion_contract_present"])
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["completion_status"],
            "replan_before_closure",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["done_status"],
            "not_done",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["safe_closure_status"],
            "not_safely_closed",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["completion_evidence_status"],
            "partial",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["completion_blocked_reason"],
            "replan_before_closure",
        )
        self.assertTrue(
            summary["lifecycle_artifacts"]["run_state"]["completion_manual_required"]
        )
        self.assertTrue(
            summary["lifecycle_artifacts"]["run_state"]["completion_replan_required"]
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["completion_lifecycle_alignment_status"],
            "partially_aligned",
        )
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["approval_transport_present"])
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["approval_status"],
            "deferred",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["approval_decision"],
            "defer",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["approval_scope"],
            "current_completion_state",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["approved_action"],
            "hold_for_manual_review",
        )
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["approval_required"])
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["approval_transport_status"],
            "non_actionable",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["approval_compatibility_status"],
            "partially_compatible",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["approval_blocked_reason"],
            "approval_scope_partial",
        )
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["reconcile_contract_present"])
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["reconcile_status"],
            "blocked",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["reconcile_decision"],
            "request_replan",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["reconcile_primary_mismatch"],
            "objective_underspecified",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["reconcile_blocked_reason"],
            "objective_underspecified",
        )
        self.assertFalse(
            summary["lifecycle_artifacts"]["run_state"]["reconcile_waiting_on_truth"]
        )
        self.assertTrue(
            summary["lifecycle_artifacts"]["run_state"]["reconcile_manual_required"]
        )
        self.assertTrue(
            summary["lifecycle_artifacts"]["run_state"]["reconcile_replan_required"]
        )
        self.assertTrue(
            summary["lifecycle_artifacts"]["run_state"]["repair_suggestion_contract_present"]
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["repair_suggestion_status"],
            "suggested",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["repair_suggestion_decision"],
            "request_replan",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["repair_primary_reason"],
            "objective_underspecified",
        )
        self.assertTrue(
            summary["lifecycle_artifacts"]["run_state"]["repair_manual_required"]
        )
        self.assertTrue(
            summary["lifecycle_artifacts"]["run_state"]["repair_replan_required"]
        )
        self.assertFalse(
            summary["lifecycle_artifacts"]["run_state"]["repair_truth_gathering_required"]
        )
        self.assertTrue(
            summary["lifecycle_artifacts"]["run_state"]["repair_plan_transport_present"]
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["repair_plan_status"],
            "available",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["repair_plan_decision"],
            "prepare_replan_plan",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["repair_plan_class"],
            "replan_plan",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["repair_plan_priority"],
            "high",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["repair_plan_candidate_action"],
            "request_replan",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["repair_plan_primary_reason"],
            "replan_required",
        )
        self.assertTrue(
            summary["lifecycle_artifacts"]["run_state"]["repair_plan_manual_required"]
        )
        self.assertTrue(
            summary["lifecycle_artifacts"]["run_state"]["repair_plan_replan_required"]
        )
        self.assertFalse(
            summary["lifecycle_artifacts"]["run_state"]["repair_plan_truth_gathering_required"]
        )
        self.assertTrue(
            summary["lifecycle_artifacts"]["run_state"]["repair_approval_binding_present"]
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["repair_approval_binding_status"],
            "missing",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["repair_approval_binding_decision"],
            "hold_unbound",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["repair_approval_binding_validity"],
            "insufficient_truth",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["repair_approval_binding_compatibility_status"],
            "insufficient_truth",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["repair_approval_binding_primary_reason"],
            "missing_approval",
        )
        self.assertTrue(
            summary["lifecycle_artifacts"]["run_state"]["repair_approval_binding_manual_required"]
        )
        self.assertTrue(
            summary["lifecycle_artifacts"]["run_state"]["repair_approval_binding_replan_required"]
        )
        self.assertTrue(
            summary["lifecycle_artifacts"]["run_state"]["execution_authorization_gate_present"]
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["execution_authorization_status"],
            "pending",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["execution_authorization_decision"],
            "request_replan",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["execution_authorization_validity"],
            "insufficient_truth",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["execution_authorization_confidence"],
            "partial",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["execution_authorization_primary_reason"],
            "missing_binding",
        )
        self.assertTrue(
            summary["lifecycle_artifacts"]["run_state"]["execution_authorization_manual_required"]
        )
        self.assertTrue(
            summary["lifecycle_artifacts"]["run_state"]["execution_authorization_replan_required"]
        )
        self.assertTrue(
            summary["lifecycle_artifacts"]["run_state"]["bounded_execution_bridge_present"]
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["bounded_execution_status"],
            "blocked",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["bounded_execution_decision"],
            "request_replan",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["bounded_execution_validity"],
            "insufficient_truth",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["bounded_execution_confidence"],
            "conservative_low",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["bounded_execution_primary_reason"],
            "authorization_not_eligible",
        )
        self.assertTrue(
            summary["lifecycle_artifacts"]["run_state"]["bounded_execution_manual_required"]
        )
        self.assertTrue(
            summary["lifecycle_artifacts"]["run_state"]["bounded_execution_replan_required"]
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["objective_contract"]["objective_status"],
            "underspecified",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["objective_contract"]["objective_source_status"],
            "structured_partial",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["objective_contract"]["acceptance_status"],
            "partially_defined",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["objective_contract"]["scope_status"],
            "clear",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["objective_contract"]["required_artifacts_status"],
            "defined",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["objective_contract"]["acceptance_criteria_total"],
            2,
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["objective_contract"]["acceptance_criteria_defined"],
            1,
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["objective_contract"]["required_artifacts_total"],
            2,
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["objective_contract"]["objective_contract_blocked_reason"],
            "acceptance_partially_defined",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["completion_contract"]["completion_status"],
            "replan_before_closure",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["completion_contract"]["done_status"],
            "not_done",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["completion_contract"]["safe_closure_status"],
            "not_safely_closed",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["completion_contract"]["completion_evidence_status"],
            "partial",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["completion_contract"]["closure_decision"],
            "replan",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["completion_contract"]["lifecycle_alignment_status"],
            "partially_aligned",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["completion_contract"]["required_evidence_total"],
            3,
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["completion_contract"]["missing_evidence_total"],
            1,
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["approval_transport"]["approval_status"],
            "deferred",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["approval_transport"]["approval_decision"],
            "defer",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["approval_transport"]["approval_scope"],
            "current_completion_state",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["approval_transport"]["approval_transport_status"],
            "non_actionable",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["approval_transport"]["approval_compatibility_status"],
            "partially_compatible",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["approval_transport"]["approval_blocked_reason"],
            "approval_scope_partial",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["reconcile_contract"]["reconcile_status"],
            "blocked",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["reconcile_contract"]["reconcile_decision"],
            "request_replan",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["reconcile_contract"]["reconcile_transport_status"],
            "partial",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["repair_suggestion_contract"]["repair_suggestion_status"],
            "suggested",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["repair_suggestion_contract"]["repair_suggestion_decision"],
            "request_replan",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["repair_suggestion_contract"]["repair_suggestion_class"],
            "objective_gap",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["repair_suggestion_contract"]["repair_primary_reason"],
            "objective_underspecified",
        )
        self.assertFalse(
            summary["lifecycle_artifacts"]["repair_suggestion_contract"]["repair_execution_recommended"]
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["repair_plan_transport"]["repair_plan_status"],
            "available",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["repair_plan_transport"]["repair_plan_decision"],
            "prepare_replan_plan",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["repair_plan_transport"]["repair_plan_class"],
            "replan_plan",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["repair_plan_transport"]["repair_plan_primary_reason"],
            "replan_required",
        )
        self.assertFalse(
            summary["lifecycle_artifacts"]["repair_plan_transport"]["repair_plan_execution_ready"]
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["repair_approval_binding"]["repair_approval_binding_status"],
            "missing",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["repair_approval_binding"]["repair_approval_binding_decision"],
            "hold_unbound",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["repair_approval_binding"]["repair_approval_binding_validity"],
            "insufficient_truth",
        )
        self.assertFalse(
            summary["lifecycle_artifacts"]["repair_approval_binding"][
                "repair_approval_binding_execution_authorized"
            ]
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["execution_authorization_gate"][
                "execution_authorization_status"
            ],
            "pending",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["execution_authorization_gate"][
                "execution_authorization_decision"
            ],
            "request_replan",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["execution_authorization_gate"][
                "execution_authorization_validity"
            ],
            "insufficient_truth",
        )
        self.assertFalse(
            summary["lifecycle_artifacts"]["execution_authorization_gate"][
                "execution_authorization_eligible"
            ]
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["bounded_execution_bridge"][
                "bounded_execution_status"
            ],
            "blocked",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["bounded_execution_bridge"][
                "bounded_execution_decision"
            ],
            "request_replan",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["bounded_execution_bridge"][
                "bounded_execution_validity"
            ],
            "insufficient_truth",
        )
        self.assertFalse(
            summary["lifecycle_artifacts"]["bounded_execution_bridge"][
                "bounded_execution_ready"
            ]
        )
        self.assertIsNotNone(summary["lifecycle_artifacts"]["paths"]["objective_contract"])
        self.assertIsNotNone(summary["lifecycle_artifacts"]["paths"]["completion_contract"])
        self.assertIsNotNone(summary["lifecycle_artifacts"]["paths"]["approval_transport"])
        self.assertIsNotNone(summary["lifecycle_artifacts"]["paths"]["reconcile_contract"])
        self.assertIsNotNone(summary["lifecycle_artifacts"]["paths"]["repair_suggestion_contract"])
        self.assertIsNotNone(summary["lifecycle_artifacts"]["paths"]["repair_plan_transport"])
        self.assertIsNotNone(summary["lifecycle_artifacts"]["paths"]["repair_approval_binding"])
        self.assertIsNotNone(summary["lifecycle_artifacts"]["paths"]["execution_authorization_gate"])
        self.assertIsNotNone(summary["lifecycle_artifacts"]["paths"]["bounded_execution_bridge"])
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["policy_primary_blocker_class"],
            "replan_required",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["operator_posture_summary"],
            "execution_blocked_replan_required",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["operator_primary_blocker_class"],
            "replan_required",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["operator_primary_action"],
            "rollback_required",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["operator_action_scope"],
            "run_wide",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["operator_resume_status"],
            "replan_required",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["operator_next_safe_posture"],
            "replan_required_before_execution",
        )
        self.assertIn(
            "roadmap_replan",
            summary["lifecycle_artifacts"]["run_state"]["operator_safe_actions_summary"],
        )
        self.assertIn(
            "proceed_to_pr",
            summary["lifecycle_artifacts"]["run_state"]["operator_unsafe_actions_summary"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["lifecycle_closure_status"],
            "rollback_complete_not_closed",
        )
        self.assertFalse(summary["lifecycle_artifacts"]["run_state"]["lifecycle_safely_closed"])
        self.assertFalse(summary["lifecycle_artifacts"]["run_state"]["lifecycle_terminal"])
        self.assertFalse(summary["lifecycle_artifacts"]["run_state"]["lifecycle_resumable"])
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["lifecycle_manual_required"])
        self.assertTrue(summary["lifecycle_artifacts"]["run_state"]["lifecycle_replan_required"])
        self.assertTrue(
            summary["lifecycle_artifacts"]["run_state"]["lifecycle_execution_complete_not_closed"]
        )
        self.assertTrue(
            summary["lifecycle_artifacts"]["run_state"]["lifecycle_rollback_complete_not_closed"]
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["lifecycle_primary_closure_issue"],
            "rollback_remote_followup_required",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["lifecycle_stop_class"],
            "stopped_replan_required",
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["operator_posture_summary"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["operator_posture_summary"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["operator_primary_blocker_class"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["operator_primary_blocker_class"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["operator_primary_action"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["operator_primary_action"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["operator_action_scope"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["operator_action_scope"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["operator_guidance_summary"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["operator_guidance_summary"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["objective_contract_status"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["objective_contract_status"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["objective_acceptance_status"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["objective_acceptance_status"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["objective_scope_status"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["objective_scope_status"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["completion_status"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["completion_status"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["done_status"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["done_status"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["safe_closure_status"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["safe_closure_status"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["approval_transport_status"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["approval_transport_status"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["approval_compatibility_status"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["approval_compatibility_status"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["approval_blocked_reason"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["approval_blocked_reason"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["reconcile_status"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["reconcile_status"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["reconcile_decision"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["reconcile_decision"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["reconcile_primary_mismatch"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["reconcile_primary_mismatch"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["repair_suggestion_status"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["repair_suggestion_status"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["repair_suggestion_decision"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["repair_suggestion_decision"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["repair_primary_reason"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["repair_primary_reason"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["repair_plan_status"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["repair_plan_status"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["repair_plan_decision"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["repair_plan_decision"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["repair_plan_primary_reason"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["repair_plan_primary_reason"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["repair_approval_binding_status"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["repair_approval_binding_status"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["repair_approval_binding_decision"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["repair_approval_binding_decision"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["repair_approval_binding_primary_reason"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["repair_approval_binding_primary_reason"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["bounded_execution_status"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["bounded_execution_status"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["bounded_execution_decision"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["bounded_execution_decision"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["bounded_execution_primary_reason"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["bounded_execution_primary_reason"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["objective_contract"]["objective_status"],
            inspect_payload["lifecycle_artifacts"]["objective_contract"]["objective_status"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["completion_contract"]["completion_status"],
            inspect_payload["lifecycle_artifacts"]["completion_contract"]["completion_status"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["completion_contract"]["required_evidence_total"],
            inspect_payload["lifecycle_artifacts"]["completion_contract"]["required_evidence_total"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["objective_contract"]["acceptance_criteria_total"],
            inspect_payload["lifecycle_artifacts"]["objective_contract"]["acceptance_criteria_total"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["lifecycle_closure_status"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["lifecycle_closure_status"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["lifecycle_primary_closure_issue"],
            inspect_payload["lifecycle_artifacts"]["run_state"]["lifecycle_primary_closure_issue"],
        )
        self.assertIn(
            "proceed_to_pr",
            summary["lifecycle_artifacts"]["run_state"]["policy_disallowed_actions"],
        )
        self.assertIn(
            "roadmap_replan",
            summary["lifecycle_artifacts"]["run_state"]["policy_manual_actions"],
        )
        self.assertEqual(
            summary["lifecycle_artifacts"]["run_state"]["readiness_summary"]["rollback"]["not_ready"],
            1,
        )
        self.assertIn("checkpoint_decision", machine_payload["artifact_references"])
        self.assertIn("run_state", machine_payload["artifact_references"])
        self.assertIn("commit_decision", machine_payload["artifact_references"])
        self.assertIn("commit_execution", machine_payload["artifact_references"])
        self.assertIn("push_execution", machine_payload["artifact_references"])
        self.assertIn("pr_execution", machine_payload["artifact_references"])
        self.assertIn("merge_execution", machine_payload["artifact_references"])
        self.assertIn("rollback_execution", machine_payload["artifact_references"])
        self.assertIn("objective_contract", machine_payload["artifact_references"])
        self.assertIn("completion_contract", machine_payload["artifact_references"])
        self.assertIn("approval_transport", machine_payload["artifact_references"])
        self.assertIn("reconcile_contract", machine_payload["artifact_references"])
        self.assertIn("repair_suggestion_contract", machine_payload["artifact_references"])
        self.assertIn("repair_plan_transport", machine_payload["artifact_references"])
        self.assertIn("repair_approval_binding", machine_payload["artifact_references"])
        self.assertIn("execution_authorization_gate", machine_payload["artifact_references"])
        self.assertIn("bounded_execution_bridge", machine_payload["artifact_references"])

    def test_latest_selects_most_recent_job(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            self._seed_job(
                db_path=db_path,
                job_id="job-old",
                created_at="2026-04-12T00:00:00+00:00",
                verify_status="not_run",
                verify_reason="no_validation_commands",
            )
            self._seed_job(
                db_path=db_path,
                job_id="job-new",
                created_at="2026-04-13T00:00:00+00:00",
                verify_status="failed",
                verify_reason="validation_failed",
            )
            out_dir = tmp_root / "out"
            proc = self._run(["--latest", "--db-path", str(db_path), "--out-dir", str(out_dir)])

            json_path = out_dir / "job-new_operator_summary.json"
            machine_path = out_dir / "job-new_machine_review_payload.json"
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            self.assertTrue(json_path.exists())
            self.assertTrue(machine_path.exists())
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["job_id"], "job-new")
            self.assertEqual(payload["validation"]["verify_status"], "failed")

    def test_summary_and_inspect_align_on_action_specific_operator_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            run_root = tmp_root / "runs" / "job-operator-action-specific"
            unit_dir = run_root / "pr-01"
            unit_dir.mkdir(parents=True, exist_ok=True)
            result_path = unit_dir / "result.json"
            result_path.write_text(
                json.dumps({"job_id": "job-operator-action-specific", "execution": {}}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
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
                job_id="job-operator-action-specific",
                created_at="2026-04-13T00:00:00+00:00",
                verify_status=None,
                verify_reason=None,
                result_path_override=str(result_path),
            )
            out_dir = tmp_root / "out"
            build_proc = self._run(
                [
                    "--job-id",
                    "job-operator-action-specific",
                    "--db-path",
                    str(db_path),
                    "--out-dir",
                    str(out_dir),
                ]
            )
            inspect_proc = self._run_inspect(
                [
                    "--job-id",
                    "job-operator-action-specific",
                    "--db-path",
                    str(db_path),
                    "--json",
                ]
            )
            summary = json.loads(
                (out_dir / "job-operator-action-specific_operator_summary.json").read_text(encoding="utf-8")
            )

        self.assertEqual(build_proc.returncode, 0, msg=build_proc.stderr)
        self.assertEqual(inspect_proc.returncode, 0, msg=inspect_proc.stderr)
        inspect_payload = json.loads(inspect_proc.stdout)
        summary_run_state = summary["lifecycle_artifacts"]["run_state"]
        inspect_run_state = inspect_payload["lifecycle_artifacts"]["run_state"]
        self.assertEqual(summary_run_state["operator_posture_summary"], "action_specific_denial_non_terminal")
        self.assertEqual(summary_run_state["operator_action_scope"], "action_specific")
        self.assertEqual(summary_run_state["operator_primary_action"], "proceed_to_pr")
        self.assertEqual(summary_run_state["operator_resume_status"], "resumable")
        self.assertEqual(summary_run_state["lifecycle_closure_status"], "stopped_resumable")
        self.assertTrue(summary_run_state["lifecycle_resumable"])
        self.assertFalse(summary_run_state["lifecycle_terminal"])
        self.assertEqual(
            summary_run_state["operator_posture_summary"],
            inspect_run_state["operator_posture_summary"],
        )
        self.assertEqual(
            summary_run_state["operator_action_scope"],
            inspect_run_state["operator_action_scope"],
        )
        self.assertEqual(
            summary_run_state["operator_guidance_summary"],
            inspect_run_state["operator_guidance_summary"],
        )
        self.assertEqual(
            summary_run_state["lifecycle_closure_status"],
            inspect_run_state["lifecycle_closure_status"],
        )

    def test_build_syncs_machine_review_reference_for_inspect_with_custom_out_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            job_id = "job-sync-machine-review"
            self._seed_job(
                db_path=db_path,
                job_id=job_id,
                created_at="2026-04-13T00:00:00+00:00",
                verify_status="passed",
                verify_reason="all_commands_passed",
            )
            out_dir = tmp_root / "custom-out"
            expected_machine_payload_path = (
                out_dir / f"{job_id}_machine_review_payload.json"
            ).resolve()

            build_proc = self._run(
                [
                    "--job-id",
                    job_id,
                    "--db-path",
                    str(db_path),
                    "--out-dir",
                    str(out_dir),
                ]
            )
            inspect_proc = self._run_inspect(
                [
                    "--job-id",
                    job_id,
                    "--db-path",
                    str(db_path),
                    "--json",
                ]
            )
            self.assertEqual(build_proc.returncode, 0, msg=build_proc.stderr)
            self.assertEqual(inspect_proc.returncode, 0, msg=inspect_proc.stderr)
            payload = json.loads(inspect_proc.stdout)
            self.assertTrue(expected_machine_payload_path.exists())
            self.assertEqual(
                payload["paths"]["machine_review_payload"],
                str(expected_machine_payload_path),
            )
            self.assertTrue(payload["machine_review"]["recorded"])
            self.assertEqual(payload["machine_review"]["recommended_action"], "escalate")
            self.assertEqual(
                payload["machine_review"]["policy_version"],
                "deterministic_review_policy.v2",
            )
            self.assertEqual(
                payload["machine_review"]["policy_reasons"],
                ["contract_drift", "insufficient_tests"],
            )
            self.assertTrue(payload["machine_review"]["requires_human_review"])

    def test_summary_surfaces_retry_reentry_loop_contract_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            run_root = tmp_root / "runs" / "job-summary-retry-loop"
            unit_dir = run_root / "pr-01"
            unit_dir.mkdir(parents=True, exist_ok=True)
            result_path = unit_dir / "result.json"
            result_path.write_text("{}", encoding="utf-8")

            (run_root / "run_state.json").write_text(
                json.dumps(
                    {
                        "run_id": "job-summary-retry-loop",
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
                        "run_id": "job-summary-retry-loop",
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
                job_id="job-summary-retry-loop",
                created_at="2026-04-13T00:00:00+00:00",
                verify_status=None,
                verify_reason=None,
                result_path_override=str(result_path),
            )
            out_dir = tmp_root / "out"

            proc = self._run(
                [
                    "--job-id",
                    "job-summary-retry-loop",
                    "--db-path",
                    str(db_path),
                    "--out-dir",
                    str(out_dir),
                ]
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)

            summary_path = out_dir / "job-summary-retry-loop_operator_summary.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

        run_state = summary["lifecycle_artifacts"]["run_state"]
        retry_contract = summary["lifecycle_artifacts"]["retry_reentry_loop_contract"]

        self.assertTrue(run_state["retry_reentry_loop_contract_present"])
        self.assertEqual(run_state["retry_loop_status"], "retry_ready")
        self.assertEqual(run_state["retry_loop_decision"], "same_lane_retry")
        self.assertEqual(run_state["loop_primary_reason"], "same_lane_retry_allowed")
        self.assertEqual(retry_contract["retry_loop_status"], "retry_ready")
        self.assertEqual(retry_contract["retry_loop_decision"], "same_lane_retry")
        self.assertEqual(retry_contract["loop_primary_reason"], "same_lane_retry_allowed")
        self.assertIsNotNone(summary["lifecycle_artifacts"]["paths"]["retry_reentry_loop_contract"])

    def test_summary_surfaces_endgame_closure_contract_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            run_root = tmp_root / "runs" / "job-endgame-summary"
            unit_dir = run_root / "pr-01"
            unit_dir.mkdir(parents=True, exist_ok=True)
            result_path = unit_dir / "result.json"
            result_path.write_text("{}", encoding="utf-8")

            (run_root / "run_state.json").write_text(
                json.dumps(
                    {
                        "run_id": "job-endgame-summary",
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
                        "run_id": "job-endgame-summary",
                        "objective_id": "objective-endgame-summary",
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
                job_id="job-endgame-summary",
                created_at="2026-04-13T00:00:00+00:00",
                verify_status="passed",
                verify_reason="all_commands_passed",
                result_path_override=str(result_path),
            )
            out_dir = tmp_root / "out"

            proc = self._run(
                [
                    "--job-id",
                    "job-endgame-summary",
                    "--db-path",
                    str(db_path),
                    "--out-dir",
                    str(out_dir),
                ]
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)

            summary_path = out_dir / "job-endgame-summary_operator_summary.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

        run_state = summary["lifecycle_artifacts"]["run_state"]
        endgame_contract = summary["lifecycle_artifacts"]["endgame_closure_contract"]
        self.assertTrue(run_state["endgame_closure_contract_present"])
        self.assertEqual(run_state["endgame_closure_status"], "safely_closed")
        self.assertEqual(run_state["final_closure_class"], "safely_closed")
        self.assertEqual(run_state["terminal_stop_class"], "terminal_success")
        self.assertEqual(endgame_contract["endgame_closure_status"], "safely_closed")
        self.assertEqual(endgame_contract["final_closure_class"], "safely_closed")
        self.assertEqual(endgame_contract["endgame_primary_reason"], "safely_closed")
        self.assertIsNotNone(summary["lifecycle_artifacts"]["paths"]["endgame_closure_contract"])

    def test_summary_surfaces_loop_hardening_contract_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            run_root = tmp_root / "runs" / "job-loop-hardening-summary"
            unit_dir = run_root / "pr-01"
            unit_dir.mkdir(parents=True, exist_ok=True)
            result_path = unit_dir / "result.json"
            result_path.write_text("{}", encoding="utf-8")

            (run_root / "run_state.json").write_text(
                json.dumps(
                    {
                        "run_id": "job-loop-hardening-summary",
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
                        "run_id": "job-loop-hardening-summary",
                        "objective_id": "objective-loop-hardening-summary",
                        "loop_hardening_status": "freeze",
                        "loop_hardening_decision": "freeze_retry",
                        "loop_hardening_validity": "partial",
                        "loop_hardening_confidence": "medium",
                        "loop_hardening_primary_reason": "retry_freeze_required",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            self._seed_job(
                db_path=db_path,
                job_id="job-loop-hardening-summary",
                created_at="2026-04-13T00:00:00+00:00",
                verify_status=None,
                verify_reason=None,
                result_path_override=str(result_path),
            )
            out_dir = tmp_root / "out"

            proc = self._run(
                [
                    "--job-id",
                    "job-loop-hardening-summary",
                    "--db-path",
                    str(db_path),
                    "--out-dir",
                    str(out_dir),
                ]
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)

            summary_path = out_dir / "job-loop-hardening-summary_operator_summary.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

        run_state = summary["lifecycle_artifacts"]["run_state"]
        loop_hardening_contract = summary["lifecycle_artifacts"]["loop_hardening_contract"]
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
        self.assertIsNotNone(summary["lifecycle_artifacts"]["paths"]["loop_hardening_contract"])

    def test_summary_surfaces_lane_stabilization_contract_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            run_root = tmp_root / "runs" / "job-lane-summary"
            unit_dir = run_root / "pr-01"
            unit_dir.mkdir(parents=True, exist_ok=True)
            result_path = unit_dir / "result.json"
            result_path.write_text("{}", encoding="utf-8")

            (run_root / "run_state.json").write_text(
                json.dumps(
                    {
                        "run_id": "job-lane-summary",
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
                        "run_id": "job-lane-summary",
                        "objective_id": "objective-lane-summary",
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
                job_id="job-lane-summary",
                created_at="2026-04-13T00:00:00+00:00",
                verify_status=None,
                verify_reason=None,
                result_path_override=str(result_path),
            )
            out_dir = tmp_root / "out"

            proc = self._run(
                [
                    "--job-id",
                    "job-lane-summary",
                    "--db-path",
                    str(db_path),
                    "--out-dir",
                    str(out_dir),
                ]
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)

            summary_path = out_dir / "job-lane-summary_operator_summary.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

        run_state = summary["lifecycle_artifacts"]["run_state"]
        lane_contract = summary["lifecycle_artifacts"]["lane_stabilization_contract"]
        self.assertTrue(run_state["lane_stabilization_contract_present"])
        self.assertEqual(run_state["lane_status"], "lane_transition_ready")
        self.assertEqual(run_state["lane_decision"], "transition_lane")
        self.assertEqual(run_state["lane_primary_reason"], "lane_transition_ready")
        self.assertEqual(lane_contract["lane_status"], "lane_transition_ready")
        self.assertEqual(lane_contract["lane_decision"], "transition_lane")
        self.assertEqual(lane_contract["lane_primary_reason"], "lane_transition_ready")
        self.assertIsNotNone(summary["lifecycle_artifacts"]["paths"]["lane_stabilization_contract"])

    def test_summary_surfaces_observability_rollups_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            run_root = tmp_root / "runs" / "job-observability-summary"
            unit_dir = run_root / "pr-01"
            unit_dir.mkdir(parents=True, exist_ok=True)
            result_path = unit_dir / "result.json"
            result_path.write_text("{}", encoding="utf-8")

            (run_root / "run_state.json").write_text(
                json.dumps(
                    {
                        "run_id": "job-observability-summary",
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
                        "run_id": "job-observability-summary",
                        "objective_id": "objective-observability-summary",
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
                        "run_id": "job-observability-summary",
                        "objective_id": "objective-observability-summary",
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
                        "run_id": "job-observability-summary",
                        "objective_id": "objective-observability-summary",
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
                        "run_id": "job-observability-summary",
                        "objective_id": "objective-observability-summary",
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
                        "run_id": "job-observability-summary",
                        "objective_id": "objective-observability-summary",
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
                        "run_id": "job-observability-summary",
                        "objective_id": "objective-observability-summary",
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
                        "run_id": "job-observability-summary",
                        "objective_id": "objective-observability-summary",
                        "fleet_safety_status": "hold",
                        "fleet_safety_validity": "partial",
                        "fleet_safety_confidence": "medium",
                        "fleet_safety_decision": "hold_for_review",
                        "fleet_restart_decision": "restart_hold",
                        "fleet_safety_scope": "run_only",
                        "fleet_safety_primary_reason": "hold_for_review_posture",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            self._seed_job(
                db_path=db_path,
                job_id="job-observability-summary",
                created_at="2026-04-13T00:00:00+00:00",
                verify_status=None,
                verify_reason=None,
                result_path_override=str(result_path),
            )
            out_dir = tmp_root / "out"

            proc = self._run(
                [
                    "--job-id",
                    "job-observability-summary",
                    "--db-path",
                    str(db_path),
                    "--out-dir",
                    str(out_dir),
                ]
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)

            summary_path = out_dir / "job-observability-summary_operator_summary.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

        run_state = summary["lifecycle_artifacts"]["run_state"]
        observability = summary["lifecycle_artifacts"]["observability_rollup_contract"]
        failure_bucket = summary["lifecycle_artifacts"]["failure_bucket_rollup"]
        fleet_rollup = summary["lifecycle_artifacts"]["fleet_run_rollup"]
        hardened_bucket = summary["lifecycle_artifacts"]["failure_bucketing_hardening_contract"]
        retention_manifest = summary["lifecycle_artifacts"]["retention_manifest"]
        artifact_retention = summary["lifecycle_artifacts"]["artifact_retention_contract"]
        fleet_safety = summary["lifecycle_artifacts"]["fleet_safety_control_contract"]
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
        self.assertEqual(fleet_safety["fleet_safety_status"], "hold")
        self.assertEqual(fleet_safety["fleet_safety_decision"], "hold_for_review")
        self.assertIsNotNone(summary["lifecycle_artifacts"]["paths"]["observability_rollup_contract"])
        self.assertIsNotNone(summary["lifecycle_artifacts"]["paths"]["failure_bucket_rollup"])
        self.assertIsNotNone(summary["lifecycle_artifacts"]["paths"]["fleet_run_rollup"])
        self.assertIsNotNone(
            summary["lifecycle_artifacts"]["paths"]["failure_bucketing_hardening_contract"]
        )
        self.assertIsNotNone(summary["lifecycle_artifacts"]["paths"]["retention_manifest"])
        self.assertIsNotNone(summary["lifecycle_artifacts"]["paths"]["artifact_retention_contract"])
        self.assertIsNotNone(
            summary["lifecycle_artifacts"]["paths"]["fleet_safety_control_contract"]
        )

    def test_missing_job_exits_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "state" / "jobs.db"
            self._seed_job(
                db_path=db_path,
                job_id="job-known",
                created_at="2026-04-13T00:00:00+00:00",
                verify_status="passed",
                verify_reason="all_commands_passed",
            )
            proc = self._run(["--job-id", "job-missing", "--db-path", str(db_path)])

        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Job not found: job-missing", proc.stderr)

    def test_summary_includes_rollback_trace_and_execution_status_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            self._seed_job(
                db_path=db_path,
                job_id="job-rollback-summary",
                created_at="2026-04-13T00:00:00+00:00",
                verify_status="passed",
                verify_reason="all_commands_passed",
            )
            candidate_key = record_execution_target(
                db_path=db_path,
                job_id="job-rollback-summary",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                created_at="2026-04-13T00:00:00+00:00",
            )
            record_merge_execution_outcome(
                db_path=db_path,
                job_id="job-rollback-summary",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                execution_status="succeeded",
                executed_at="2026-04-13T00:10:00+00:00",
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
                db_path=db_path,
                rollback_trace_id=str(trace["rollback_trace_id"]),
                execution_status="succeeded",
                attempted_at="2026-04-13T00:20:00+00:00",
                current_head_sha="c" * 40,
                rollback_result_sha="d" * 40,
                rollback_error=None,
                consistency_check_passed=True,
            )
            out_dir = tmp_root / "out"
            proc = self._run(
                [
                    "--job-id",
                    "job-rollback-summary",
                    "--db-path",
                    str(db_path),
                    "--out-dir",
                    str(out_dir),
                ]
            )
            payload = json.loads(
                (out_dir / "job-rollback-summary_operator_summary.json").read_text(encoding="utf-8")
            )

        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertTrue(payload["rollback"]["trace_recorded"])
        self.assertEqual(payload["rollback"]["rollback_eligible"], True)
        self.assertEqual(payload["rollback"]["rollback_execution_status"], "succeeded")

    def test_build_and_inspect_surface_merge_gate_contract_fields_consistently(self) -> None:
        merge_gate_payload = {
            "lifecycle_state": "review_pending",
            "write_authority": {
                "state": "write_preparable",
                "allowed_categories": ["docs_only"],
            },
            "replan_input": {
                "failure_type": "lifecycle_blocked",
                "retry_recommended": False,
                "retry_recommendation": "escalate",
                "retry_budget_remaining": 0,
                "escalation_required": True,
                "next_action_readiness": "manual_escalation_required",
                "primary_fail_reasons": ["write_lifecycle_not_ready"],
            },
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            job_id = "job-contract-alignment"
            self._seed_job(
                db_path=db_path,
                job_id=job_id,
                created_at="2026-04-13T00:00:00+00:00",
                verify_status="passed",
                verify_reason="all_commands_passed",
                merge_gate_payload=merge_gate_payload,
            )
            out_dir = tmp_root / "out"
            build_proc = self._run(
                ["--job-id", job_id, "--db-path", str(db_path), "--out-dir", str(out_dir)]
            )
            inspect_proc = self._run_inspect(
                ["--job-id", job_id, "--db-path", str(db_path), "--json"]
            )

            self.assertEqual(build_proc.returncode, 0, msg=build_proc.stderr)
            self.assertEqual(inspect_proc.returncode, 0, msg=inspect_proc.stderr)
            machine_payload = json.loads(
                (out_dir / f"{job_id}_machine_review_payload.json").read_text(encoding="utf-8")
            )
            inspect_payload = json.loads(inspect_proc.stdout)

        self.assertEqual(machine_payload["lifecycle_state"], "review_pending")
        self.assertEqual(machine_payload["write_authority"]["state"], "write_preparable")
        self.assertEqual(
            machine_payload["write_authority"]["allowed_categories"],
            ["docs_only"],
        )
        self.assertEqual(machine_payload["failure_type"], "lifecycle_blocked")
        self.assertEqual(machine_payload["retry_recommended"], False)
        self.assertEqual(machine_payload["retry_recommendation"], "escalate")
        self.assertEqual(machine_payload["retry_budget_remaining"], 0)
        self.assertEqual(machine_payload["escalation_required"], True)
        self.assertEqual(
            machine_payload["next_action_readiness"],
            "manual_escalation_required",
        )
        self.assertEqual(
            machine_payload["primary_fail_reasons"],
            ["write_lifecycle_not_ready"],
        )

        self.assertEqual(inspect_payload["lifecycle_state"], "review_pending")
        self.assertEqual(inspect_payload["write_authority"]["state"], "write_preparable")
        self.assertEqual(
            inspect_payload["write_authority"]["allowed_categories"],
            ["docs_only"],
        )
        self.assertEqual(inspect_payload["failure_type"], "lifecycle_blocked")
        self.assertEqual(inspect_payload["retry_recommended"], False)
        self.assertEqual(inspect_payload["retry_recommendation"], "escalate")
        self.assertEqual(inspect_payload["retry_budget_remaining"], 0)
        self.assertEqual(inspect_payload["escalation_required"], True)
        self.assertEqual(
            inspect_payload["next_action_readiness"],
            "manual_escalation_required",
        )
        self.assertEqual(
            inspect_payload["primary_fail_reasons"],
            ["write_lifecycle_not_ready"],
        )

    def test_machine_policy_recommends_rollback_for_failed_validation_when_eligible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            self._seed_job(
                db_path=db_path,
                job_id="job-policy-rollback",
                created_at="2026-04-13T00:00:00+00:00",
                verify_status="failed",
                verify_reason="validation_failed",
            )
            candidate_key = self._seed_candidate_with_merge_execution(
                db_path=db_path,
                job_id="job-policy-rollback",
                execution_status="succeeded",
                pre_merge_sha="b" * 40,
                post_merge_sha="c" * 40,
            )
            record_rollback_traceability_for_candidate(
                candidate_idempotency_key=candidate_key,
                db_path=db_path,
            )
            payload = self._build_and_read_machine_payload(
                db_path=db_path,
                job_id="job-policy-rollback",
                out_dir=tmp_root / "out",
            )
            rollback_execution = get_rollback_execution_by_job_id(
                "job-policy-rollback",
                db_path=db_path,
            )

        self.assertEqual(payload["recommended_action"], "escalate")
        self.assertIn("contract_drift", payload["policy_reasons"])
        self.assertIn("insufficient_tests", payload["policy_reasons"])
        self.assertIsNone(rollback_execution)

    def test_machine_policy_escalates_when_failed_validation_but_rollback_ineligible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            self._seed_job(
                db_path=db_path,
                job_id="job-policy-ineligible",
                created_at="2026-04-13T00:00:00+00:00",
                verify_status="failed",
                verify_reason="validation_failed",
            )
            candidate_key = self._seed_candidate_with_merge_execution(
                db_path=db_path,
                job_id="job-policy-ineligible",
                execution_status="failed",
                pre_merge_sha="b" * 40,
                post_merge_sha="c" * 40,
            )
            record_rollback_traceability_for_candidate(
                candidate_idempotency_key=candidate_key,
                db_path=db_path,
            )
            payload = self._build_and_read_machine_payload(
                db_path=db_path,
                job_id="job-policy-ineligible",
                out_dir=tmp_root / "out",
            )

        self.assertEqual(payload["recommended_action"], "escalate")
        self.assertIn("contract_drift", payload["policy_reasons"])
        self.assertIn("insufficient_tests", payload["policy_reasons"])

    def test_machine_policy_escalates_when_validation_not_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            self._seed_job(
                db_path=db_path,
                job_id="job-policy-not-run",
                created_at="2026-04-13T00:00:00+00:00",
                verify_status="not_run",
                verify_reason="no_validation_commands",
            )
            payload = self._build_and_read_machine_payload(
                db_path=db_path,
                job_id="job-policy-not-run",
                out_dir=tmp_root / "out",
            )

        self.assertEqual(payload["recommended_action"], "escalate")
        self.assertIn("contract_drift", payload["policy_reasons"])
        self.assertIn("insufficient_tests", payload["policy_reasons"])
        self.assertIsNone(payload["retry_metadata"]["retry_recommended"])
        self.assertEqual(payload["retry_metadata"]["retry_basis"], [])
        self.assertIn(
            "blocking_failure_code:contract_drift",
            payload["retry_metadata"]["retry_blockers"],
        )
        self.assertIn(
            "validation_not_run",
            payload["retry_metadata"]["retry_blockers"],
        )

    def test_machine_policy_escalates_for_unrecognized_validation_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            self._seed_job(
                db_path=db_path,
                job_id="job-policy-ambiguous",
                created_at="2026-04-13T00:00:00+00:00",
                verify_status="flaky_state",
                verify_reason="unknown_semantics",
            )
            payload = self._build_and_read_machine_payload(
                db_path=db_path,
                job_id="job-policy-ambiguous",
                out_dir=tmp_root / "out",
            )

        self.assertEqual(payload["recommended_action"], "escalate")
        self.assertIn("contract_drift", payload["policy_reasons"])
        self.assertIn("insufficient_tests", payload["policy_reasons"])

    def test_machine_policy_recommends_retry_when_prior_rollback_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            self._seed_job(
                db_path=db_path,
                job_id="job-policy-retry",
                created_at="2026-04-13T00:00:00+00:00",
                verify_status="failed",
                verify_reason="validation_failed",
            )
            candidate_key = self._seed_candidate_with_merge_execution(
                db_path=db_path,
                job_id="job-policy-retry",
                execution_status="succeeded",
                pre_merge_sha="b" * 40,
                post_merge_sha="c" * 40,
            )
            trace = record_rollback_traceability_for_candidate(
                candidate_idempotency_key=candidate_key,
                db_path=db_path,
            )
            record_rollback_execution_outcome(
                db_path=db_path,
                rollback_trace_id=str(trace["rollback_trace_id"]),
                execution_status="failed",
                attempted_at="2026-04-13T00:20:00+00:00",
                current_head_sha="c" * 40,
                rollback_result_sha=None,
                rollback_error="git_revert_conflict",
                consistency_check_passed=True,
            )
            payload = self._build_and_read_machine_payload(
                db_path=db_path,
                job_id="job-policy-retry",
                out_dir=tmp_root / "out",
            )

        self.assertEqual(payload["recommended_action"], "escalate")
        self.assertIn("contract_drift", payload["policy_reasons"])
        self.assertIn("insufficient_tests", payload["policy_reasons"])
        self.assertIsNone(payload["retry_metadata"]["retry_recommended"])
        self.assertEqual(payload["retry_metadata"]["retry_basis"], [])
        self.assertIn(
            "blocking_failure_code:contract_drift",
            payload["retry_metadata"]["retry_blockers"],
        )
        self.assertIn(
            "validation_failed",
            payload["retry_metadata"]["retry_blockers"],
        )


if __name__ == "__main__":
    unittest.main()
