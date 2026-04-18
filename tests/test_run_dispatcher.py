from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from automation.observability.run_audit import RunAuditLogger
import automation.scheduler.run_dispatcher as run_dispatcher_module
from automation.scheduler.run_dispatcher import DispatchRequest
from automation.scheduler.run_dispatcher import RunDispatcher


class _FakeRunner:
    def __init__(self, outcomes: list[dict[str, object]]) -> None:
        self.outcomes = list(outcomes)
        self.call_count = 0

    def run(
        self,
        *,
        artifacts_input_dir,
        output_dir,
        job_id=None,
        dry_run=True,
        stop_on_failure=True,
        retry_context=None,
        policy_snapshot=None,
        github_read_evidence=None,
    ):
        index = min(self.call_count, max(0, len(self.outcomes) - 1))
        outcome = self.outcomes[index]
        self.call_count += 1

        resolved_job_id = str(job_id or outcome.get("job_id") or "job-1")
        output_root = Path(output_dir)
        run_root = output_root / resolved_job_id
        run_root.mkdir(parents=True, exist_ok=True)

        next_action_payload = {
            "job_id": resolved_job_id,
            "next_action": outcome.get("next_action", ""),
            "reason": outcome.get("reason", ""),
            "retry_budget_remaining": outcome.get("retry_budget_remaining", 0),
            "whether_human_required": outcome.get("whether_human_required", False),
            "provider_name": outcome.get("provider_name"),
            "retry_after_seconds": outcome.get("retry_after_seconds"),
            "next_eligible_at": outcome.get("next_eligible_at"),
            "pause_state": outcome.get("pause_state"),
            "updated_retry_context": outcome.get(
                "updated_retry_context",
                {
                    "prior_attempt_count": 0,
                    "prior_retry_class": None,
                    "missing_signal_count": 0,
                    "retry_budget_remaining": 0,
                },
            ),
        }
        handoff_payload = {
            "job_id": resolved_job_id,
            "next_action": outcome.get("next_action", ""),
            "reason": outcome.get("reason", ""),
            "whether_human_required": outcome.get("whether_human_required", False),
            "retry_budget_remaining": outcome.get("retry_budget_remaining", 0),
            "provider_name": outcome.get("provider_name"),
            "retry_after_seconds": outcome.get("retry_after_seconds"),
            "next_eligible_at": outcome.get("next_eligible_at"),
            "pause_state": outcome.get("pause_state"),
            "updated_retry_context": next_action_payload["updated_retry_context"],
            "action_consumable": outcome.get("action_consumable", True),
            "unsupported_reason": outcome.get("unsupported_reason"),
        }
        handoff_overrides = outcome.get("handoff_overrides")
        if isinstance(handoff_overrides, dict):
            handoff_payload.update(handoff_overrides)
        manifest_payload = {
            "job_id": resolved_job_id,
            "run_status": outcome.get("run_status", "completed"),
            "artifact_input_dir": str(artifacts_input_dir),
            "pr_units": [],
            "next_action_path": str(run_root / "next_action.json"),
            "action_handoff_path": str(run_root / "action_handoff.json"),
        }
        (run_root / "manifest.json").write_text(
            json.dumps(manifest_payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        (run_root / "next_action.json").write_text(
            json.dumps(next_action_payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        (run_root / "action_handoff.json").write_text(
            json.dumps(handoff_payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        # Mimic runner-side retry context persistence surface.
        store_path = output_root / "retry_context_store.json"
        store_payload = {
            "schema_version": "v1",
            "contexts": {
                resolved_job_id: {
                    "retry_context": next_action_payload["updated_retry_context"],
                    "updated_at": "2026-04-18T14:00:00",
                }
            },
        }
        store_path.write_text(
            json.dumps(store_payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return manifest_payload


class _FakeActionExecutor:
    def __init__(self, responses: dict[str, dict[str, object]] | None = None) -> None:
        self.responses = dict(responses or {})
        self.calls: list[dict[str, object]] = []

    def execute_from_run_dir(self, run_dir, **kwargs):
        run_root = Path(run_dir)
        handoff = json.loads((run_root / "action_handoff.json").read_text(encoding="utf-8"))
        action = str(handoff.get("next_action", "")).strip()
        self.calls.append({"run_dir": str(run_root), "action": action, "kwargs": kwargs})
        if action in self.responses:
            return dict(self.responses[action])
        return {
            "job_id": str(handoff.get("job_id", "")).strip(),
            "requested_action": action,
            "attempted": True,
            "succeeded": True,
            "refusal_reason": None,
            "whether_human_required": False,
        }


class RunDispatcherTests(unittest.TestCase):
    def _fixed_now(self) -> datetime:
        return datetime(2026, 4, 18, 14, 0, 0)

    def _request(self, *, artifacts_input_dir: Path, output_dir: Path, **overrides):
        payload = {
            "artifacts_input_dir": artifacts_input_dir,
            "output_dir": output_dir,
            "job_id": "job-1",
            "dry_run": False,
            "stop_on_failure": True,
            "max_retry_dispatches": 1,
            "write_authority": {
                "state": "write_allowed",
                "write_actions_allowed": True,
                "allowed_actions": ["proceed_to_pr", "proceed_to_merge", "rollback_required"],
                "allowed_categories": ["docs_only"],
            },
            "category": "docs_only",
        }
        payload.update(overrides)
        return DispatchRequest(**payload)

    def _audit_payload(self, run_root: Path) -> dict[str, object]:
        return json.loads((run_root / "run_audit.json").read_text(encoding="utf-8"))

    def _pause_payload(self, run_root: Path) -> dict[str, object]:
        return json.loads((run_root / "pause_state.json").read_text(encoding="utf-8"))

    def _write_executor_receipt(
        self,
        run_root: Path,
        filename: str,
        payload: dict[str, object],
    ) -> None:
        run_root.mkdir(parents=True, exist_ok=True)
        (run_root / filename).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def test_dispatch_of_explicit_requested_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            runner = _FakeRunner(
                [{"next_action": "proceed_to_pr", "action_consumable": True, "reason": "ready"}]
            )
            executor = _FakeActionExecutor()
            dispatcher = RunDispatcher(
                runner=runner,
                action_executor=executor,
                audit_logger=RunAuditLogger(now=self._fixed_now),
                now=self._fixed_now,
            )
            result = dispatcher.dispatch_once(
                self._request(artifacts_input_dir=root / "planning", output_dir=root / "exec")
            )

        self.assertEqual(result["dispatch_status"], "executed")
        self.assertEqual(runner.call_count, 1)
        self.assertEqual(len(executor.calls), 1)

    def test_unsupported_action_is_escalated_and_not_silently_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            runner = _FakeRunner([{"next_action": "manual_only", "action_consumable": True, "reason": "unsupported"}])
            executor = _FakeActionExecutor()
            dispatcher = RunDispatcher(runner=runner, action_executor=executor, audit_logger=RunAuditLogger(now=self._fixed_now))
            result = dispatcher.dispatch_once(
                self._request(artifacts_input_dir=root / "planning", output_dir=root / "exec")
            )
            run_root = root / "exec" / "job-1"
            audit = self._audit_payload(run_root)

        self.assertEqual(result["dispatch_status"], "escalated")
        self.assertEqual(len(executor.calls), 0)
        self.assertEqual(audit["records"][-1]["routing_reason"], "authority_action_unclassified")

    def test_provider_capacity_pause_persists_state_instead_of_immediate_retry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            runner = _FakeRunner(
                [
                    {
                        "next_action": "same_prompt_retry",
                        "action_consumable": True,
                        "reason": "provider capacity unavailable for codex",
                        "retry_budget_remaining": 1,
                    }
                ]
            )
            executor = _FakeActionExecutor()
            dispatcher = RunDispatcher(
                runner=runner,
                action_executor=executor,
                audit_logger=RunAuditLogger(now=self._fixed_now),
                now=self._fixed_now,
            )
            result = dispatcher.dispatch_once(
                self._request(artifacts_input_dir=root / "planning", output_dir=root / "exec")
            )
            run_root = root / "exec" / "job-1"
            pause_payload = self._pause_payload(run_root)
            audit = self._audit_payload(run_root)

        self.assertEqual(result["dispatch_status"], "paused")
        self.assertEqual(runner.call_count, 1)
        self.assertEqual(len(executor.calls), 0)
        self.assertEqual(pause_payload["pause_state"], "waiting_for_provider_capacity")
        self.assertEqual(audit["records"][-1]["outcome_status"], "paused")

    def test_rate_limit_pause_persists_next_eligible_time(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            runner = _FakeRunner(
                [
                    {
                        "next_action": "same_prompt_retry",
                        "action_consumable": True,
                        "reason": "rate limit hit retry_after_seconds=120",
                        "retry_after_seconds": 120,
                    }
                ]
            )
            dispatcher = RunDispatcher(
                runner=runner,
                action_executor=_FakeActionExecutor(),
                audit_logger=RunAuditLogger(now=self._fixed_now),
                now=self._fixed_now,
            )
            result = dispatcher.dispatch_once(
                self._request(artifacts_input_dir=root / "planning", output_dir=root / "exec")
            )
            pause_payload = self._pause_payload(root / "exec" / "job-1")

        self.assertEqual(result["dispatch_status"], "paused")
        self.assertEqual(pause_payload["pause_state"], "waiting_for_rate_limit_reset")
        self.assertEqual(pause_payload["retry_after_seconds"], 120)
        self.assertEqual(pause_payload["next_eligible_at"], "2026-04-18T14:02:00")

    def test_wait_for_checks_leads_to_pause(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            runner = _FakeRunner(
                [{"next_action": "wait_for_checks", "action_consumable": True, "reason": "checks pending"}]
            )
            dispatcher = RunDispatcher(
                runner=runner,
                action_executor=_FakeActionExecutor(),
                audit_logger=RunAuditLogger(now=self._fixed_now),
                now=self._fixed_now,
            )
            result = dispatcher.dispatch_once(
                self._request(artifacts_input_dir=root / "planning", output_dir=root / "exec")
            )
            pause_payload = self._pause_payload(root / "exec" / "job-1")

        self.assertEqual(result["dispatch_status"], "paused")
        self.assertEqual(pause_payload["pause_state"], "waiting_for_checks")

    def test_human_required_signal_leads_to_waiting_for_human_pause(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            runner = _FakeRunner(
                [
                    {
                        "next_action": "escalate_to_human",
                        "action_consumable": True,
                        "reason": "manual review required",
                        "whether_human_required": True,
                    }
                ]
            )
            dispatcher = RunDispatcher(
                runner=runner,
                action_executor=_FakeActionExecutor(),
                audit_logger=RunAuditLogger(now=self._fixed_now),
                now=self._fixed_now,
            )
            result = dispatcher.dispatch_once(
                self._request(artifacts_input_dir=root / "planning", output_dir=root / "exec")
            )
            pause_payload = self._pause_payload(root / "exec" / "job-1")

        self.assertEqual(result["dispatch_status"], "paused")
        self.assertEqual(pause_payload["pause_state"], "waiting_for_human")

    def test_paused_job_is_skipped_before_eligibility(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            run_root = root / "exec" / "job-1"
            run_root.mkdir(parents=True, exist_ok=True)
            (run_root / "pause_state.json").write_text(
                json.dumps(
                    {
                        "pause_schema_version": "v1",
                        "job_id": "job-1",
                        "lifecycle_state": "paused",
                        "pause_state": "waiting_for_rate_limit_reset",
                        "pause_reason": "rate limit hit",
                        "next_eligible_at": "2026-04-18T15:00:00",
                        "whether_human_required": False,
                        "updated_at": "2026-04-18T14:00:00",
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )

            runner = _FakeRunner([{"next_action": "proceed_to_pr", "action_consumable": True, "reason": "ready"}])
            dispatcher = RunDispatcher(
                runner=runner,
                action_executor=_FakeActionExecutor(),
                audit_logger=RunAuditLogger(now=self._fixed_now),
                now=self._fixed_now,
            )
            result = dispatcher.dispatch_once(
                self._request(
                    artifacts_input_dir=root / "planning",
                    output_dir=root / "exec",
                    head_branch="feature/test",
                )
            )
            audit = self._audit_payload(run_root)

        self.assertEqual(result["dispatch_status"], "paused")
        self.assertEqual(runner.call_count, 0)
        self.assertEqual(audit["records"][-1]["routing_reason"], "paused_not_eligible")

    def test_paused_job_becomes_dispatchable_after_eligibility(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            run_root = root / "exec" / "job-1"
            run_root.mkdir(parents=True, exist_ok=True)
            (run_root / "pause_state.json").write_text(
                json.dumps(
                    {
                        "pause_schema_version": "v1",
                        "job_id": "job-1",
                        "lifecycle_state": "paused",
                        "pause_state": "waiting_for_rate_limit_reset",
                        "pause_reason": "rate limit hit",
                        "next_eligible_at": "2026-04-18T13:58:00",
                        "whether_human_required": False,
                        "updated_at": "2026-04-18T13:57:00",
                        "resume_count": 0,
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            runner = _FakeRunner([{"next_action": "proceed_to_pr", "action_consumable": True, "reason": "ready"}])
            dispatcher = RunDispatcher(
                runner=runner,
                action_executor=_FakeActionExecutor(),
                audit_logger=RunAuditLogger(now=self._fixed_now),
                now=self._fixed_now,
            )
            result = dispatcher.dispatch_once(
                self._request(
                    artifacts_input_dir=root / "planning",
                    output_dir=root / "exec",
                    head_branch="feature/test",
                )
            )
            audit = self._audit_payload(run_root)
            pause_payload = self._pause_payload(run_root)

        self.assertEqual(result["dispatch_status"], "executed")
        self.assertEqual(runner.call_count, 1)
        self.assertEqual(pause_payload["lifecycle_state"], "resumed")
        self.assertGreaterEqual(int(pause_payload["resume_count"]), 1)
        self.assertTrue(any(record["scheduler_action_taken"] == "resume" for record in audit["records"]))

    def test_resume_preserves_prior_artifacts_and_safety_gate_outcome(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            run_root = root / "exec" / "job-1"
            run_root.mkdir(parents=True, exist_ok=True)
            (run_root / "keep.txt").write_text("existing", encoding="utf-8")
            (run_root / "pause_state.json").write_text(
                json.dumps(
                    {
                        "pause_schema_version": "v1",
                        "job_id": "job-1",
                        "lifecycle_state": "paused",
                        "pause_state": "waiting_for_checks",
                        "pause_reason": "checks pending",
                        "next_eligible_at": "2026-04-18T13:50:00",
                        "whether_human_required": False,
                        "updated_at": "2026-04-18T13:49:00",
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            runner = _FakeRunner([{"next_action": "proceed_to_pr", "action_consumable": True, "reason": "ready"}])
            executor = _FakeActionExecutor(
                responses={
                    "proceed_to_pr": {
                        "job_id": "job-1",
                        "requested_action": "proceed_to_pr",
                        "attempted": False,
                        "succeeded": False,
                        "refusal_reason": "write_authority_blocked:dry_run_only",
                        "whether_human_required": True,
                    }
                }
            )
            dispatcher = RunDispatcher(
                runner=runner,
                action_executor=executor,
                audit_logger=RunAuditLogger(now=self._fixed_now),
                now=self._fixed_now,
            )
            result = dispatcher.dispatch_once(
                self._request(
                    artifacts_input_dir=root / "planning",
                    output_dir=root / "exec",
                    head_branch="feature/test",
                )
            )
            self.assertTrue((run_root / "keep.txt").exists())

        self.assertEqual(result["dispatch_status"], "escalated")

    def test_routes_proceed_to_pr_when_supported_and_consumable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            runner = _FakeRunner([{"next_action": "proceed_to_pr", "action_consumable": True, "reason": "ready"}])
            executor = _FakeActionExecutor()
            dispatcher = RunDispatcher(runner=runner, action_executor=executor, audit_logger=RunAuditLogger(now=self._fixed_now))
            result = dispatcher.dispatch_once(
                self._request(
                    artifacts_input_dir=root / "planning",
                    output_dir=root / "exec",
                    head_branch="feature/test",
                )
            )

        self.assertEqual(result["dispatch_status"], "executed")
        self.assertEqual(executor.calls[0]["action"], "proceed_to_pr")

    def test_lane_request_disallowed_by_authority_is_escalated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            runner = _FakeRunner([{"next_action": "proceed_to_pr", "action_consumable": True, "reason": "ready"}])
            executor = _FakeActionExecutor()
            dispatcher = RunDispatcher(runner=runner, action_executor=executor, audit_logger=RunAuditLogger(now=self._fixed_now))
            result = dispatcher.dispatch_once(
                self._request(
                    artifacts_input_dir=root / "planning",
                    output_dir=root / "exec",
                    policy_snapshot={"requested_execution_lane": "llm_backed"},
                )
            )
            run_root = root / "exec" / "job-1"
            audit = self._audit_payload(run_root)

        self.assertEqual(result["dispatch_status"], "escalated")
        self.assertEqual(len(executor.calls), 0)
        self.assertEqual(audit["records"][-1]["routing_reason"], "authority_requested_lane_not_allowed")

    def test_canonical_handoff_requested_lane_routes_consistently(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            runner = _FakeRunner(
                [
                    {
                        "next_action": "proceed_to_pr",
                        "action_consumable": True,
                        "reason": "ready",
                        "handoff_overrides": {
                            "requested_execution": {
                                "requested_lanes": {"proceed_to_pr": "github_deterministic"},
                            }
                        },
                    }
                ]
            )
            executor = _FakeActionExecutor()
            dispatcher = RunDispatcher(runner=runner, action_executor=executor, audit_logger=RunAuditLogger(now=self._fixed_now))
            result = dispatcher.dispatch_once(
                self._request(
                    artifacts_input_dir=root / "planning",
                    output_dir=root / "exec",
                )
            )

        self.assertEqual(result["dispatch_status"], "executed")
        self.assertEqual(len(executor.calls), 1)

    def test_conflicting_policy_and_handoff_lane_requests_escalate_conservatively(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            runner = _FakeRunner(
                [
                    {
                        "next_action": "proceed_to_pr",
                        "action_consumable": True,
                        "reason": "ready",
                        "handoff_overrides": {
                            "requested_execution": {
                                "requested_lanes": {"proceed_to_pr": "github_deterministic"},
                            }
                        },
                    }
                ]
            )
            executor = _FakeActionExecutor()
            dispatcher = RunDispatcher(runner=runner, action_executor=executor, audit_logger=RunAuditLogger(now=self._fixed_now))
            result = dispatcher.dispatch_once(
                self._request(
                    artifacts_input_dir=root / "planning",
                    output_dir=root / "exec",
                    policy_snapshot={"requested_execution_lane": "llm_backed"},
                )
            )
            run_root = root / "exec" / "job-1"
            audit = self._audit_payload(run_root)

        self.assertEqual(result["dispatch_status"], "escalated")
        self.assertEqual(len(executor.calls), 0)
        self.assertEqual(audit["records"][-1]["routing_reason"], "authority_requested_lane_conflict")

    def test_allowed_requested_lane_routes_normally(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            runner = _FakeRunner([{"next_action": "proceed_to_pr", "action_consumable": True, "reason": "ready"}])
            executor = _FakeActionExecutor()
            dispatcher = RunDispatcher(runner=runner, action_executor=executor, audit_logger=RunAuditLogger(now=self._fixed_now))
            result = dispatcher.dispatch_once(
                self._request(
                    artifacts_input_dir=root / "planning",
                    output_dir=root / "exec",
                    policy_snapshot={"requested_execution_lane": "github_deterministic"},
                )
            )

        self.assertEqual(result["dispatch_status"], "executed")
        self.assertEqual(len(executor.calls), 1)

    def test_control_action_is_authority_routed_to_escalation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            runner = _FakeRunner([{"next_action": "escalate_to_human", "action_consumable": True, "reason": "manual hold"}])
            executor = _FakeActionExecutor()
            dispatcher = RunDispatcher(runner=runner, action_executor=executor, audit_logger=RunAuditLogger(now=self._fixed_now))
            result = dispatcher.dispatch_once(
                self._request(artifacts_input_dir=root / "planning", output_dir=root / "exec")
            )
            audit = self._audit_payload(root / "exec" / "job-1")

        self.assertEqual(result["dispatch_status"], "escalated")
        self.assertEqual(len(executor.calls), 0)
        self.assertEqual(audit["records"][-1]["routing_reason"], "authority_control_action_no_executor_route")

    def test_routes_proceed_to_merge_only_with_explicit_pr_number(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            runner = _FakeRunner([{"next_action": "proceed_to_merge", "action_consumable": True, "reason": "ready"}])
            executor = _FakeActionExecutor()
            dispatcher = RunDispatcher(runner=runner, action_executor=executor, audit_logger=RunAuditLogger(now=self._fixed_now))
            result = dispatcher.dispatch_once(
                self._request(
                    artifacts_input_dir=root / "planning",
                    output_dir=root / "exec",
                    pr_number=42,
                )
            )

        self.assertEqual(result["dispatch_status"], "executed")
        self.assertEqual(executor.calls[0]["kwargs"]["pr_number"], 42)

    def test_routes_github_pr_update_with_explicit_pr_number_and_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            runner = _FakeRunner([{"next_action": "github.pr.update", "action_consumable": True, "reason": "update"}])
            executor = _FakeActionExecutor()
            dispatcher = RunDispatcher(runner=runner, action_executor=executor, audit_logger=RunAuditLogger(now=self._fixed_now))
            result = dispatcher.dispatch_once(
                self._request(
                    artifacts_input_dir=root / "planning",
                    output_dir=root / "exec",
                    pr_number=42,
                    pr_update={"title": "Updated title"},
                )
            )

        self.assertEqual(result["dispatch_status"], "executed")
        self.assertEqual(executor.calls[0]["kwargs"]["pr_number"], 42)
        self.assertEqual(executor.calls[0]["kwargs"]["pr_update"], {"title": "Updated title"})

    def test_escalates_when_github_pr_update_payload_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            runner = _FakeRunner([{"next_action": "github.pr.update", "action_consumable": True, "reason": "update"}])
            executor = _FakeActionExecutor()
            dispatcher = RunDispatcher(runner=runner, action_executor=executor, audit_logger=RunAuditLogger(now=self._fixed_now))
            result = dispatcher.dispatch_once(
                self._request(
                    artifacts_input_dir=root / "planning",
                    output_dir=root / "exec",
                    pr_number=42,
                    pr_update={},
                )
            )
        self.assertEqual(result["dispatch_status"], "escalated")
        self.assertEqual(len(executor.calls), 0)

    def test_escalates_when_merge_pr_number_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            runner = _FakeRunner([{"next_action": "proceed_to_merge", "action_consumable": True, "reason": "ready"}])
            executor = _FakeActionExecutor()
            dispatcher = RunDispatcher(runner=runner, action_executor=executor, audit_logger=RunAuditLogger(now=self._fixed_now))
            result = dispatcher.dispatch_once(
                self._request(artifacts_input_dir=root / "planning", output_dir=root / "exec", pr_number=None)
            )

        self.assertEqual(result["dispatch_status"], "escalated")
        self.assertEqual(len(executor.calls), 0)

    def test_routes_rollback_only_with_explicit_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            runner = _FakeRunner([{"next_action": "rollback_required", "action_consumable": True, "reason": "rollback"}])
            executor = _FakeActionExecutor()
            dispatcher = RunDispatcher(runner=runner, action_executor=executor, audit_logger=RunAuditLogger(now=self._fixed_now))
            rollback_target = {
                "repo_path": "/tmp/repo",
                "target_ref": "main",
                "pre_merge_sha": "1" * 40,
                "post_merge_sha": "2" * 40,
            }
            result = dispatcher.dispatch_once(
                self._request(
                    artifacts_input_dir=root / "planning",
                    output_dir=root / "exec",
                    rollback_target=rollback_target,
                )
            )

        self.assertEqual(result["dispatch_status"], "executed")
        self.assertEqual(executor.calls[0]["kwargs"]["rollback_target"], rollback_target)

    def test_escalates_when_rollback_target_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            runner = _FakeRunner([{"next_action": "rollback_required", "action_consumable": True, "reason": "rollback"}])
            executor = _FakeActionExecutor()
            dispatcher = RunDispatcher(runner=runner, action_executor=executor, audit_logger=RunAuditLogger(now=self._fixed_now))
            result = dispatcher.dispatch_once(
                self._request(
                    artifacts_input_dir=root / "planning",
                    output_dir=root / "exec",
                    rollback_target={},
                )
            )
        self.assertEqual(result["dispatch_status"], "escalated")
        self.assertEqual(len(executor.calls), 0)

    def test_merge_still_escalates_without_pr_number_after_resume(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            run_root = root / "exec" / "job-1"
            run_root.mkdir(parents=True, exist_ok=True)
            (run_root / "pause_state.json").write_text(
                json.dumps(
                    {
                        "pause_schema_version": "v1",
                        "job_id": "job-1",
                        "lifecycle_state": "paused",
                        "pause_state": "waiting_for_checks",
                        "pause_reason": "checks pending",
                        "next_eligible_at": "2026-04-18T13:58:00",
                        "whether_human_required": False,
                        "updated_at": "2026-04-18T13:57:00",
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            runner = _FakeRunner([{"next_action": "proceed_to_merge", "action_consumable": True, "reason": "ready"}])
            dispatcher = RunDispatcher(
                runner=runner,
                action_executor=_FakeActionExecutor(),
                audit_logger=RunAuditLogger(now=self._fixed_now),
                now=self._fixed_now,
            )
            result = dispatcher.dispatch_once(
                self._request(artifacts_input_dir=root / "planning", output_dir=root / "exec", pr_number=None)
            )

        self.assertEqual(result["dispatch_status"], "escalated")

    def test_rollback_still_escalates_when_target_missing_after_resume(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            run_root = root / "exec" / "job-1"
            run_root.mkdir(parents=True, exist_ok=True)
            (run_root / "pause_state.json").write_text(
                json.dumps(
                    {
                        "pause_schema_version": "v1",
                        "job_id": "job-1",
                        "lifecycle_state": "paused",
                        "pause_state": "waiting_for_checks",
                        "pause_reason": "checks pending",
                        "next_eligible_at": "2026-04-18T13:58:00",
                        "whether_human_required": False,
                        "updated_at": "2026-04-18T13:57:00",
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            runner = _FakeRunner([{"next_action": "rollback_required", "action_consumable": True, "reason": "rollback"}])
            dispatcher = RunDispatcher(
                runner=runner,
                action_executor=_FakeActionExecutor(),
                audit_logger=RunAuditLogger(now=self._fixed_now),
                now=self._fixed_now,
            )
            result = dispatcher.dispatch_once(
                self._request(
                    artifacts_input_dir=root / "planning",
                    output_dir=root / "exec",
                    rollback_target={},
                )
            )

        self.assertEqual(result["dispatch_status"], "escalated")

    def test_audit_includes_paused_and_resumed_entries_deterministically(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            runner = _FakeRunner(
                [
                    {"next_action": "wait_for_checks", "action_consumable": True, "reason": "checks pending"},
                    {"next_action": "proceed_to_pr", "action_consumable": True, "reason": "ready"},
                ]
            )
            dispatcher = RunDispatcher(
                runner=runner,
                action_executor=_FakeActionExecutor(),
                audit_logger=RunAuditLogger(now=self._fixed_now),
                now=self._fixed_now,
            )
            first = dispatcher.dispatch_once(
                self._request(artifacts_input_dir=root / "planning", output_dir=root / "exec")
            )
            run_root = root / "exec" / "job-1"
            pause_payload = self._pause_payload(run_root)
            pause_payload["next_eligible_at"] = "2026-04-18T13:58:00"
            (run_root / "pause_state.json").write_text(
                json.dumps(pause_payload, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            second = dispatcher.dispatch_once(
                self._request(
                    artifacts_input_dir=root / "planning",
                    output_dir=root / "exec",
                    head_branch="feature/test",
                )
            )
            audit = self._audit_payload(run_root)

        self.assertEqual(first["dispatch_status"], "paused")
        self.assertEqual(second["dispatch_status"], "executed")
        action_sequence = [record["scheduler_action_taken"] for record in audit["records"]]
        self.assertIn("pause", action_sequence)
        self.assertIn("resume", action_sequence)
        self.assertEqual(audit["records"][-1]["outcome_status"], "executed")

    def test_bounded_retry_progression(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            runner = _FakeRunner(
                [
                    {
                        "next_action": "signal_recollect",
                        "action_consumable": True,
                        "reason": "missing signals",
                        "retry_budget_remaining": 1,
                        "updated_retry_context": {
                            "prior_attempt_count": 0,
                            "prior_retry_class": None,
                            "missing_signal_count": 1,
                            "retry_budget_remaining": 1,
                        },
                    },
                    {"next_action": "proceed_to_pr", "action_consumable": True, "reason": "ready"},
                ]
            )
            executor = _FakeActionExecutor()
            dispatcher = RunDispatcher(runner=runner, action_executor=executor, audit_logger=RunAuditLogger(now=self._fixed_now))
            result = dispatcher.dispatch_once(
                self._request(
                    artifacts_input_dir=root / "planning",
                    output_dir=root / "exec",
                    head_branch="feature/test",
                    max_retry_dispatches=1,
                )
            )

        self.assertEqual(result["dispatch_status"], "executed")
        self.assertEqual(runner.call_count, 2)
        self.assertEqual(len(executor.calls), 1)

    def test_retry_short_circuit_on_existing_update_already_applied_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            run_root = root / "exec" / "job-1"
            self._write_executor_receipt(
                run_root,
                "pr_update_receipt.json",
                {
                    "job_id": "job-1",
                    "requested_action": "github.pr.update",
                    "attempted": False,
                    "succeeded": True,
                    "refusal_reason": None,
                    "whether_human_required": False,
                    "executed_at": "2026-04-18T13:59:00",
                    "write_idempotency": {"dedupe_status": "already_applied"},
                    "evidence_used_summary": {"write_result": {"status": "already_applied"}},
                },
            )
            runner = _FakeRunner(
                [
                    {
                        "next_action": "signal_recollect",
                        "action_consumable": True,
                        "reason": "missing or incomplete artifacts/signals require recollection",
                        "retry_budget_remaining": 1,
                        "updated_retry_context": {
                            "prior_attempt_count": 0,
                            "prior_retry_class": None,
                            "missing_signal_count": 1,
                            "retry_budget_remaining": 1,
                        },
                    }
                ]
            )
            executor = _FakeActionExecutor()
            dispatcher = RunDispatcher(
                runner=runner,
                action_executor=executor,
                audit_logger=RunAuditLogger(now=self._fixed_now),
                now=self._fixed_now,
            )
            result = dispatcher.dispatch_once(
                self._request(
                    artifacts_input_dir=root / "planning",
                    output_dir=root / "exec",
                    max_retry_dispatches=1,
                )
            )
            audit = self._audit_payload(run_root)

        self.assertEqual(result["dispatch_status"], "executed")
        self.assertEqual(runner.call_count, 1)
        self.assertEqual(len(executor.calls), 0)
        self.assertEqual(audit["records"][-1]["scheduler_action_taken"], "short_circuit")
        self.assertEqual(
            audit["records"][-1]["routing_reason"],
            "short_circuit_existing_terminal_write_result:github.pr.update:already_applied",
        )

    def test_retry_short_circuit_on_existing_terminal_refusal_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            run_root = root / "exec" / "job-1"
            self._write_executor_receipt(
                run_root,
                "merge_receipt.json",
                {
                    "job_id": "job-1",
                    "requested_action": "proceed_to_merge",
                    "attempted": False,
                    "succeeded": False,
                    "refusal_reason": "idempotency_precondition_changed:head_sha_changed",
                    "whether_human_required": True,
                    "executed_at": "2026-04-18T13:59:30",
                },
            )
            runner = _FakeRunner(
                [
                    {
                        "next_action": "same_prompt_retry",
                        "action_consumable": True,
                        "reason": "execution failure",
                        "retry_budget_remaining": 1,
                    }
                ]
            )
            executor = _FakeActionExecutor()
            dispatcher = RunDispatcher(
                runner=runner,
                action_executor=executor,
                audit_logger=RunAuditLogger(now=self._fixed_now),
                now=self._fixed_now,
            )
            result = dispatcher.dispatch_once(
                self._request(
                    artifacts_input_dir=root / "planning",
                    output_dir=root / "exec",
                    max_retry_dispatches=1,
                )
            )
            audit = self._audit_payload(run_root)

        self.assertEqual(result["dispatch_status"], "escalated")
        self.assertEqual(runner.call_count, 1)
        self.assertEqual(len(executor.calls), 0)
        self.assertEqual(audit["records"][-1]["scheduler_action_taken"], "short_circuit")
        self.assertEqual(
            audit["records"][-1]["routing_reason"],
            "short_circuit_existing_terminal_refusal:proceed_to_merge:idempotency_precondition_changed:head_sha_changed",
        )

    def test_routing_resolution_is_carried_forward_for_same_step_retry_reentry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            runner = _FakeRunner(
                [
                    {
                        "next_action": "same_prompt_retry",
                        "action_consumable": True,
                        "reason": "execution failure",
                        "retry_budget_remaining": 1,
                        "updated_retry_context": {
                            "prior_attempt_count": 0,
                            "prior_retry_class": None,
                            "missing_signal_count": 0,
                            "retry_budget_remaining": 1,
                        },
                    },
                    {
                        "next_action": "same_prompt_retry",
                        "action_consumable": True,
                        "reason": "execution failure",
                        "retry_budget_remaining": 1,
                        "updated_retry_context": {
                            "prior_attempt_count": 0,
                            "prior_retry_class": None,
                            "missing_signal_count": 0,
                            "retry_budget_remaining": 1,
                        },
                    },
                ]
            )
            dispatcher = RunDispatcher(
                runner=runner,
                action_executor=_FakeActionExecutor(),
                audit_logger=RunAuditLogger(now=self._fixed_now),
                now=self._fixed_now,
            )
            original_resolver = run_dispatcher_module.resolve_action_routing
            resolver_calls = 0

            def _counting_resolver(*args, **kwargs):
                nonlocal resolver_calls
                resolver_calls += 1
                return original_resolver(*args, **kwargs)

            with patch(
                "automation.scheduler.run_dispatcher.resolve_action_routing",
                side_effect=_counting_resolver,
            ):
                result = dispatcher.dispatch_once(
                    self._request(
                        artifacts_input_dir=root / "planning",
                        output_dir=root / "exec",
                        max_retry_dispatches=1,
                    )
                )

        self.assertEqual(result["dispatch_status"], "escalated")
        self.assertEqual(runner.call_count, 2)
        self.assertEqual(resolver_calls, 1)

    def test_routing_cache_uses_canonical_lane_fingerprint_for_equivalent_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            runner = _FakeRunner(
                [
                    {
                        "next_action": "same_prompt_retry",
                        "action_consumable": True,
                        "reason": "execution failure",
                        "retry_budget_remaining": 1,
                        "handoff_overrides": {"requested_execution_lane": "llm_backed"},
                        "updated_retry_context": {
                            "prior_attempt_count": 0,
                            "prior_retry_class": None,
                            "missing_signal_count": 0,
                            "retry_budget_remaining": 1,
                        },
                    },
                    {
                        "next_action": "same_prompt_retry",
                        "action_consumable": True,
                        "reason": "execution failure",
                        "retry_budget_remaining": 1,
                        "handoff_overrides": {
                            "requested_execution": {
                                "requested_lane": "llm_backed",
                            }
                        },
                        "updated_retry_context": {
                            "prior_attempt_count": 0,
                            "prior_retry_class": None,
                            "missing_signal_count": 0,
                            "retry_budget_remaining": 1,
                        },
                    },
                ]
            )
            dispatcher = RunDispatcher(
                runner=runner,
                action_executor=_FakeActionExecutor(),
                audit_logger=RunAuditLogger(now=self._fixed_now),
                now=self._fixed_now,
            )
            original_resolver = run_dispatcher_module.resolve_action_routing
            resolver_calls = 0

            def _counting_resolver(*args, **kwargs):
                nonlocal resolver_calls
                resolver_calls += 1
                return original_resolver(*args, **kwargs)

            with patch(
                "automation.scheduler.run_dispatcher.resolve_action_routing",
                side_effect=_counting_resolver,
            ):
                result = dispatcher.dispatch_once(
                    self._request(
                        artifacts_input_dir=root / "planning",
                        output_dir=root / "exec",
                        max_retry_dispatches=1,
                    )
                )

        self.assertEqual(result["dispatch_status"], "escalated")
        self.assertEqual(runner.call_count, 2)
        self.assertEqual(resolver_calls, 1)

    def test_escalates_on_retry_budget_exhausted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            runner = _FakeRunner(
                [
                    {
                        "next_action": "same_prompt_retry",
                        "action_consumable": True,
                        "reason": "execution failure",
                        "retry_budget_remaining": 0,
                        "updated_retry_context": {
                            "prior_attempt_count": 0,
                            "prior_retry_class": None,
                            "missing_signal_count": 0,
                            "retry_budget_remaining": 0,
                        },
                    }
                ]
            )
            executor = _FakeActionExecutor()
            dispatcher = RunDispatcher(runner=runner, action_executor=executor, audit_logger=RunAuditLogger(now=self._fixed_now))
            result = dispatcher.dispatch_once(
                self._request(
                    artifacts_input_dir=root / "planning",
                    output_dir=root / "exec",
                    max_retry_dispatches=1,
                )
            )
            audit = self._audit_payload(root / "exec" / "job-1")

        self.assertEqual(result["dispatch_status"], "escalated")
        self.assertEqual(audit["records"][-1]["routing_reason"], "retry_budget_exhausted")
        self.assertEqual(runner.call_count, 1)

    def test_escalates_on_retry_class_exhausted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            runner = _FakeRunner(
                [
                    {
                        "next_action": "same_prompt_retry",
                        "action_consumable": True,
                        "reason": "execution failure",
                        "retry_budget_remaining": 1,
                        "updated_retry_context": {
                            "prior_attempt_count": 0,
                            "prior_retry_class": None,
                            "missing_signal_count": 0,
                            "retry_budget_remaining": 1,
                        },
                    },
                    {
                        "next_action": "same_prompt_retry",
                        "action_consumable": True,
                        "reason": "execution failure again",
                        "retry_budget_remaining": 1,
                        "updated_retry_context": {
                            "prior_attempt_count": 2,
                            "prior_retry_class": "same_prompt_retry",
                            "missing_signal_count": 0,
                            "retry_budget_remaining": 1,
                        },
                    },
                ]
            )
            dispatcher = RunDispatcher(
                runner=runner,
                action_executor=_FakeActionExecutor(),
                audit_logger=RunAuditLogger(now=self._fixed_now),
            )
            result = dispatcher.dispatch_once(
                self._request(
                    artifacts_input_dir=root / "planning",
                    output_dir=root / "exec",
                    max_retry_dispatches=2,
                )
            )
            audit = self._audit_payload(root / "exec" / "job-1")

        self.assertEqual(result["dispatch_status"], "escalated")
        self.assertEqual(runner.call_count, 2)
        self.assertEqual(audit["records"][-1]["routing_reason"], "retry_class_exhausted")

    def test_escalates_on_persisted_retry_class_exhaustion_without_second_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            runner = _FakeRunner(
                [
                    {
                        "next_action": "same_prompt_retry",
                        "action_consumable": True,
                        "reason": "execution failure",
                        "retry_budget_remaining": 1,
                        "updated_retry_context": {
                            "prior_attempt_count": 1,
                            "prior_retry_class": "same_prompt_retry",
                            "missing_signal_count": 0,
                            "retry_budget_remaining": 1,
                        },
                    }
                ]
            )
            dispatcher = RunDispatcher(
                runner=runner,
                action_executor=_FakeActionExecutor(),
                audit_logger=RunAuditLogger(now=self._fixed_now),
            )
            result = dispatcher.dispatch_once(
                self._request(
                    artifacts_input_dir=root / "planning",
                    output_dir=root / "exec",
                    max_retry_dispatches=2,
                )
            )
            audit = self._audit_payload(root / "exec" / "job-1")

        self.assertEqual(result["dispatch_status"], "escalated")
        self.assertEqual(runner.call_count, 1)
        self.assertEqual(audit["records"][-1]["routing_reason"], "retry_class_exhausted")

    def test_audit_persistence_is_deterministic_for_equivalent_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            outcomes = [{"next_action": "manual_only", "action_consumable": True, "reason": "unsupported"}]
            dispatcher_a = RunDispatcher(
                runner=_FakeRunner(outcomes),
                action_executor=_FakeActionExecutor(),
                audit_logger=RunAuditLogger(now=self._fixed_now),
            )
            dispatcher_b = RunDispatcher(
                runner=_FakeRunner(outcomes),
                action_executor=_FakeActionExecutor(),
                audit_logger=RunAuditLogger(now=self._fixed_now),
            )
            dispatcher_a.dispatch_once(
                self._request(artifacts_input_dir=root / "a" / "planning", output_dir=root / "a" / "exec")
            )
            dispatcher_b.dispatch_once(
                self._request(artifacts_input_dir=root / "b" / "planning", output_dir=root / "b" / "exec")
            )
            audit_a = self._audit_payload(root / "a" / "exec" / "job-1")
            audit_b = self._audit_payload(root / "b" / "exec" / "job-1")

        self.assertEqual(audit_a, audit_b)

    def test_dispatch_cycle_has_no_infinite_loop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            runner = _FakeRunner(
                [
                    {
                        "next_action": "signal_recollect",
                        "action_consumable": True,
                        "reason": "missing signals",
                        "retry_budget_remaining": 1,
                        "updated_retry_context": {
                            "prior_attempt_count": 0,
                            "prior_retry_class": None,
                            "missing_signal_count": 1,
                            "retry_budget_remaining": 1,
                        },
                    }
                ]
            )
            dispatcher = RunDispatcher(
                runner=runner,
                action_executor=_FakeActionExecutor(),
                audit_logger=RunAuditLogger(now=self._fixed_now),
            )
            result = dispatcher.dispatch_once(
                self._request(
                    artifacts_input_dir=root / "planning",
                    output_dir=root / "exec",
                    max_retry_dispatches=2,
                )
            )

        self.assertEqual(result["dispatch_status"], "escalated")
        self.assertEqual(runner.call_count, 3)

    def test_scheduler_never_bypasses_action_executor_safety_gates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            runner = _FakeRunner([{"next_action": "proceed_to_pr", "action_consumable": True, "reason": "ready"}])
            executor = _FakeActionExecutor(
                responses={
                    "proceed_to_pr": {
                        "job_id": "job-1",
                        "requested_action": "proceed_to_pr",
                        "attempted": False,
                        "succeeded": False,
                        "refusal_reason": "write_authority_blocked:dry_run_only",
                        "whether_human_required": True,
                    }
                }
            )
            dispatcher = RunDispatcher(runner=runner, action_executor=executor, audit_logger=RunAuditLogger(now=self._fixed_now))
            result = dispatcher.dispatch_once(
                self._request(
                    artifacts_input_dir=root / "planning",
                    output_dir=root / "exec",
                    head_branch="feature/test",
                )
            )
            audit = self._audit_payload(root / "exec" / "job-1")

        self.assertEqual(result["dispatch_status"], "escalated")
        self.assertEqual(audit["records"][-1]["routing_reason"], "write_authority_blocked:dry_run_only")
        self.assertEqual(len(executor.calls), 1)


if __name__ == "__main__":
    unittest.main()
