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
        self.assertIn("lifecycle_operator_posture_summary:", human_proc.stdout)
        self.assertIn("lifecycle_operator_safe_actions_summary:", human_proc.stdout)
        self.assertIn("lifecycle_operator_unsafe_actions_summary:", human_proc.stdout)
        self.assertIn("lifecycle_closure_status:", human_proc.stdout)
        self.assertIn("lifecycle_execution_complete_not_closed:", human_proc.stdout)
        self.assertIn("lifecycle_rollback_complete_not_closed:", human_proc.stdout)

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
