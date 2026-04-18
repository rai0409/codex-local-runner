from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Mapping

from automation.scheduler.job_lease import FileJobLease
from automation.scheduler.job_registry import FileJobRegistry
from automation.scheduler.job_registry import STATE_COMPLETED
from automation.scheduler.job_registry import STATE_ESCALATED
from automation.scheduler.job_registry import STATE_FAILED_TERMINAL
from automation.scheduler.job_registry import STATE_PAUSED
from automation.scheduler.job_registry import STATE_PENDING
from automation.scheduler.job_registry import STATE_RETRY_SCHEDULED
from automation.scheduler.job_registry import STATE_RUNNABLE
from automation.scheduler.pause_state import is_pause_active
from automation.scheduler.pause_state import is_pause_resume_eligible
from automation.scheduler.pause_state import load_pause_payload
from automation.scheduler.run_dispatcher import DispatchRequest
from automation.scheduler.run_dispatcher import RunDispatcher

_REQUIRED_PLANNING_FILES = (
    "project_brief.json",
    "repo_facts.json",
    "roadmap.json",
    "pr_plan.json",
)


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return False


def _as_optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text and text.lstrip("-").isdigit():
            return int(text)
    return None


def _parse_iso_datetime(value: Any) -> datetime | None:
    text = _normalize_text(value, default="")
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _read_json_object(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    return payload


def _is_terminal_refusal_reason(text: str) -> bool:
    normalized = text.lower()
    return "terminal refusal" in normalized or "terminal_refusal" in normalized


@dataclass
class SchedulerJob:
    job_id: str | None
    artifacts_input_dir: str | Path
    output_dir: str | Path
    dry_run: bool = True
    stop_on_failure: bool = True
    max_retry_dispatches: int = 1
    repository: str | None = None
    head_branch: str | None = None
    base_branch: str | None = None
    category: str | None = None
    write_authority: Mapping[str, Any] | None = None
    policy_snapshot: Mapping[str, Any] | None = None
    pr_number: int | None = None
    expected_head_sha: str | None = None
    rollback_target: Mapping[str, Any] | None = None
    github_read_evidence: Mapping[str, Any] | None = None
    current_state: str | None = None


@dataclass
class JobScheduler:
    dispatcher: RunDispatcher
    now: Callable[[], datetime] = datetime.now
    registry: FileJobRegistry | None = None
    lease_manager: FileJobLease | None = None

    def _registry_for(self, output_root: Path) -> FileJobRegistry:
        if self.registry is not None:
            return self.registry
        return FileJobRegistry(output_root / "job_registry.json", now=self.now)

    def _lease_for(self, output_root: Path) -> FileJobLease:
        if self.lease_manager is not None:
            return self.lease_manager
        return FileJobLease(output_root / "job_leases.json", now=self.now)

    def _derive_authoritative_state(
        self,
        *,
        record: Mapping[str, Any],
        run_root: Path,
    ) -> dict[str, Any]:
        pause_payload = load_pause_payload(run_root)
        pause_active = is_pause_active(pause_payload)
        if pause_active:
            pause_eligible = is_pause_resume_eligible(pause_payload, now=self.now)
            return {
                "current_state": STATE_RUNNABLE if pause_eligible else STATE_PAUSED,
                "next_eligible_at": _normalize_text((pause_payload or {}).get("next_eligible_at"), default="") or None,
                "whether_human_required": _as_bool((pause_payload or {}).get("whether_human_required")),
                "terminal_status": None,
            }

        current_state = _normalize_text(record.get("current_state"), default=STATE_PENDING).lower()
        next_eligible_at = _normalize_text(record.get("next_eligible_at"), default="") or None
        retry_class = _normalize_text(record.get("retry_class"), default="") or None
        retry_budget_remaining = _as_optional_int(record.get("retry_budget_remaining"))
        whether_human_required = _as_bool(record.get("whether_human_required"))
        terminal_status = _normalize_text(record.get("terminal_status"), default="") or None

        audit_payload = _read_json_object(run_root / "run_audit.json")
        if isinstance(audit_payload, Mapping):
            records = audit_payload.get("records")
            if isinstance(records, list) and records:
                latest = records[-1] if isinstance(records[-1], Mapping) else {}
                outcome_status = _normalize_text(latest.get("outcome_status"), default="")
                routing_reason = _normalize_text(latest.get("routing_reason"), default="")
                if outcome_status == "executed":
                    return {
                        "current_state": STATE_COMPLETED,
                        "next_eligible_at": None,
                        "whether_human_required": _as_bool(latest.get("whether_human_required")),
                        "terminal_status": None,
                    }
                if outcome_status == "escalated":
                    if _is_terminal_refusal_reason(routing_reason):
                        return {
                            "current_state": STATE_FAILED_TERMINAL,
                            "next_eligible_at": None,
                            "whether_human_required": True,
                            "terminal_status": routing_reason or "terminal_refusal",
                        }
                    return {
                        "current_state": STATE_ESCALATED,
                        "next_eligible_at": None,
                        "whether_human_required": True,
                        "terminal_status": None,
                    }
                if outcome_status == "paused":
                    return {
                        "current_state": STATE_PAUSED,
                        "next_eligible_at": _normalize_text(latest.get("next_eligible_at"), default="") or next_eligible_at,
                        "whether_human_required": _as_bool(latest.get("whether_human_required")),
                        "terminal_status": None,
                    }

        if current_state == STATE_RETRY_SCHEDULED:
            eligible_time = _parse_iso_datetime(next_eligible_at)
            if eligible_time is None or self.now() >= eligible_time:
                current_state = STATE_RUNNABLE
                next_eligible_at = None
            else:
                current_state = STATE_RETRY_SCHEDULED

        if current_state in {STATE_COMPLETED, STATE_FAILED_TERMINAL, STATE_ESCALATED}:
            return {
                "current_state": current_state,
                "next_eligible_at": None,
                "whether_human_required": whether_human_required,
                "terminal_status": terminal_status,
            }

        manifest_exists = (run_root / "manifest.json").exists()
        if manifest_exists and current_state not in {STATE_RETRY_SCHEDULED}:
            current_state = STATE_RUNNABLE
        elif not manifest_exists and current_state not in {STATE_RETRY_SCHEDULED}:
            current_state = STATE_PENDING

        return {
            "current_state": current_state,
            "next_eligible_at": next_eligible_at,
            "retry_class": retry_class,
            "retry_budget_remaining": retry_budget_remaining,
            "whether_human_required": whether_human_required,
            "terminal_status": terminal_status,
        }

    def sync_registry_from_artifacts(
        self,
        *,
        artifacts_root: str | Path,
        output_root: str | Path,
    ) -> list[dict[str, Any]]:
        artifacts_dir = Path(artifacts_root)
        output_dir = Path(output_root)
        registry = self._registry_for(output_dir)
        if not artifacts_dir.exists() or not artifacts_dir.is_dir():
            return registry.list()

        for child in sorted(artifacts_dir.iterdir(), key=lambda p: p.name):
            if not child.is_dir():
                continue
            if not all((child / filename).exists() for filename in _REQUIRED_PLANNING_FILES):
                continue
            job_id = _normalize_text(child.name, default="")
            if not job_id:
                continue
            run_root = output_dir / job_id
            existing = registry.get(job_id) or {}
            authoritative = self._derive_authoritative_state(record=existing, run_root=run_root)
            repo_or_workspace = _normalize_text(existing.get("repo_or_workspace"), default="") or None
            if repo_or_workspace is None:
                repo_facts = _read_json_object(child / "repo_facts.json") or {}
                repo_or_workspace = _normalize_text(repo_facts.get("repo"), default="") or None

            updated = {
                **existing,
                "job_id": job_id,
                "artifact_root": str(child),
                "run_root": str(run_root),
                "repo_or_workspace": repo_or_workspace,
                "current_state": authoritative.get("current_state", STATE_PENDING),
                "next_eligible_at": authoritative.get("next_eligible_at"),
                "retry_class": authoritative.get("retry_class", existing.get("retry_class")),
                "retry_budget_remaining": authoritative.get(
                    "retry_budget_remaining",
                    existing.get("retry_budget_remaining"),
                ),
                "whether_human_required": authoritative.get(
                    "whether_human_required",
                    existing.get("whether_human_required", False),
                ),
                "terminal_status": authoritative.get("terminal_status"),
                "updated_at": self.now().isoformat(timespec="seconds"),
            }
            if "created_at" not in updated or not _normalize_text(updated.get("created_at"), default=""):
                updated["created_at"] = self.now().isoformat(timespec="seconds")
            registry.upsert(updated)

        return registry.list()

    def discover_pending_jobs(
        self,
        *,
        artifacts_root: str | Path,
        output_root: str | Path,
        dry_run: bool = True,
        stop_on_failure: bool = True,
        max_retry_dispatches: int = 1,
        write_authority: Mapping[str, Any] | None = None,
        policy_snapshot: Mapping[str, Any] | None = None,
    ) -> list[SchedulerJob]:
        artifacts_dir = Path(artifacts_root)
        output_dir = Path(output_root)
        if not artifacts_dir.exists() or not artifacts_dir.is_dir():
            return []

        jobs: list[SchedulerJob] = []
        for child in sorted(artifacts_dir.iterdir(), key=lambda p: p.name):
            if not child.is_dir():
                continue
            if not all((child / filename).exists() for filename in _REQUIRED_PLANNING_FILES):
                continue
            candidate_job_id = _normalize_text(child.name, default="")
            if not candidate_job_id:
                continue
            run_root = output_dir / candidate_job_id
            manifest_path = run_root / "manifest.json"
            pause_payload = load_pause_payload(run_root)
            pause_active = is_pause_active(pause_payload)
            pause_eligible = is_pause_resume_eligible(pause_payload, now=self.now) if pause_active else False
            if manifest_path.exists() and not pause_eligible:
                continue
            if pause_active and not pause_eligible:
                continue
            jobs.append(
                SchedulerJob(
                    job_id=candidate_job_id,
                    artifacts_input_dir=child,
                    output_dir=output_dir,
                    dry_run=dry_run,
                    stop_on_failure=stop_on_failure,
                    max_retry_dispatches=max_retry_dispatches,
                    write_authority=write_authority,
                    policy_snapshot=policy_snapshot,
                    current_state=STATE_PENDING,
                )
            )
        return jobs

    def run_cycle(self, jobs: list[SchedulerJob]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for job in jobs:
            request = DispatchRequest(
                job_id=job.job_id,
                artifacts_input_dir=job.artifacts_input_dir,
                output_dir=job.output_dir,
                dry_run=job.dry_run,
                stop_on_failure=job.stop_on_failure,
                max_retry_dispatches=job.max_retry_dispatches,
                repository=job.repository,
                head_branch=job.head_branch,
                base_branch=job.base_branch,
                category=job.category,
                write_authority=job.write_authority,
                policy_snapshot=job.policy_snapshot,
                pr_number=job.pr_number,
                expected_head_sha=job.expected_head_sha,
                rollback_target=job.rollback_target,
                github_read_evidence=job.github_read_evidence,
            )
            results.append(self.dispatcher.dispatch_once(request))
        return results

    def _scheduler_job_from_record(
        self,
        record: Mapping[str, Any],
        *,
        output_root: Path,
        dry_run: bool,
        stop_on_failure: bool,
        max_retry_dispatches: int,
        write_authority: Mapping[str, Any] | None,
        policy_snapshot: Mapping[str, Any] | None,
    ) -> SchedulerJob | None:
        job_id = _normalize_text(record.get("job_id"), default="")
        artifact_root = _normalize_text(record.get("artifact_root"), default="")
        if not job_id or not artifact_root:
            return None
        return SchedulerJob(
            job_id=job_id,
            artifacts_input_dir=artifact_root,
            output_dir=output_root,
            dry_run=dry_run,
            stop_on_failure=stop_on_failure,
            max_retry_dispatches=max_retry_dispatches,
            write_authority=write_authority,
            policy_snapshot=policy_snapshot,
            current_state=_normalize_text(record.get("current_state"), default=STATE_PENDING),
        )

    def _update_registry_from_dispatch_result(
        self,
        *,
        registry: FileJobRegistry,
        record: Mapping[str, Any],
        result: Mapping[str, Any],
    ) -> dict[str, Any]:
        job_id = _normalize_text(record.get("job_id"), default="")
        run_root_text = _normalize_text(record.get("run_root"), default="")
        run_root = Path(run_root_text) if run_root_text else None
        dispatch_status = _normalize_text(result.get("dispatch_status"), default="")
        audit = result.get("audit") if isinstance(result.get("audit"), Mapping) else {}
        routing_reason = _normalize_text(audit.get("routing_reason"), default="")

        updated = dict(record)
        updated["job_id"] = job_id
        updated["updated_at"] = self.now().isoformat(timespec="seconds")
        updated["retry_class"] = _normalize_text(audit.get("retry_class"), default="") or updated.get("retry_class")
        updated["retry_budget_remaining"] = (
            _as_optional_int(audit.get("retry_budget_remaining"))
            if audit.get("retry_budget_remaining") is not None
            else updated.get("retry_budget_remaining")
        )
        updated["whether_human_required"] = _as_bool(audit.get("whether_human_required"))

        if dispatch_status == "executed":
            updated["current_state"] = STATE_COMPLETED
            updated["terminal_status"] = None
            updated["next_eligible_at"] = None
        elif dispatch_status == "paused":
            pause_payload = load_pause_payload(run_root) if run_root is not None else None
            updated["current_state"] = STATE_PAUSED
            updated["next_eligible_at"] = _normalize_text((pause_payload or {}).get("next_eligible_at"), default="") or None
            updated["whether_human_required"] = _as_bool((pause_payload or {}).get("whether_human_required"))
            updated["terminal_status"] = None
        elif dispatch_status == "escalated":
            if _is_terminal_refusal_reason(routing_reason):
                updated["current_state"] = STATE_FAILED_TERMINAL
                updated["terminal_status"] = routing_reason or "terminal_refusal"
            else:
                updated["current_state"] = STATE_ESCALATED
                updated["terminal_status"] = None
            updated["next_eligible_at"] = None
        else:
            updated["current_state"] = STATE_ESCALATED
            updated["terminal_status"] = "unknown_dispatch_status"
            updated["next_eligible_at"] = None

        return registry.upsert(updated)

    def run_registry_cycle(
        self,
        *,
        artifacts_root: str | Path,
        output_root: str | Path,
        holder: str = "scheduler",
        lease_seconds: int = 120,
        max_jobs: int | None = None,
        dry_run: bool = True,
        stop_on_failure: bool = True,
        max_retry_dispatches: int = 1,
        write_authority: Mapping[str, Any] | None = None,
        policy_snapshot: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        output_dir = Path(output_root)
        registry = self._registry_for(output_dir)
        lease = self._lease_for(output_dir)
        records = self.sync_registry_from_artifacts(artifacts_root=artifacts_root, output_root=output_root)

        jobs_considered = len(records)
        jobs_claimed = 0
        jobs_skipped_paused = 0
        jobs_skipped_leased = 0
        jobs_skipped_retry_scheduled = 0
        jobs_run = 0
        jobs_resumed = 0
        jobs_paused = 0
        jobs_escalated = 0
        jobs_completed = 0
        jobs_failed_terminal = 0

        processed_jobs = 0
        max_jobs_limit = max_jobs if isinstance(max_jobs, int) and max_jobs > 0 else None

        for record in records:
            state = _normalize_text(record.get("current_state"), default=STATE_PENDING).lower()
            job_id = _normalize_text(record.get("job_id"), default="")
            if not job_id:
                continue

            if state in {STATE_COMPLETED, STATE_ESCALATED, STATE_FAILED_TERMINAL}:
                continue
            if state == STATE_PAUSED:
                jobs_skipped_paused += 1
                continue
            if state == STATE_RETRY_SCHEDULED:
                next_eligible_at = _parse_iso_datetime(record.get("next_eligible_at"))
                if next_eligible_at is not None and self.now() < next_eligible_at:
                    jobs_skipped_retry_scheduled += 1
                    continue
                state = STATE_RUNNABLE

            if state not in {STATE_PENDING, STATE_RUNNABLE}:
                continue
            if max_jobs_limit is not None and processed_jobs >= max_jobs_limit:
                break

            claimed, _lease_record = lease.claim(
                job_id=job_id,
                holder=holder,
                lease_seconds=lease_seconds,
            )
            if not claimed:
                jobs_skipped_leased += 1
                continue
            jobs_claimed += 1

            try:
                scheduler_job = self._scheduler_job_from_record(
                    record,
                    output_root=output_dir,
                    dry_run=dry_run,
                    stop_on_failure=stop_on_failure,
                    max_retry_dispatches=max_retry_dispatches,
                    write_authority=write_authority,
                    policy_snapshot=policy_snapshot,
                )
                if scheduler_job is None:
                    updated = dict(record)
                    updated["current_state"] = STATE_FAILED_TERMINAL
                    updated["terminal_status"] = "invalid_registry_record"
                    registry.upsert(updated)
                    jobs_failed_terminal += 1
                    continue

                result = self.run_cycle([scheduler_job])[0]
                jobs_run += 1
                processed_jobs += 1

                dispatch_status = _normalize_text(result.get("dispatch_status"), default="")
                if dispatch_status == "paused":
                    jobs_paused += 1
                elif dispatch_status == "executed":
                    jobs_completed += 1
                elif dispatch_status == "escalated":
                    audit = result.get("audit") if isinstance(result.get("audit"), Mapping) else {}
                    routing_reason = _normalize_text(audit.get("routing_reason"), default="")
                    if _is_terminal_refusal_reason(routing_reason):
                        jobs_failed_terminal += 1
                    else:
                        jobs_escalated += 1

                before_state = _normalize_text(record.get("current_state"), default=STATE_PENDING)
                updated_record = self._update_registry_from_dispatch_result(
                    registry=registry,
                    record=record,
                    result=result,
                )
                after_state = _normalize_text(updated_record.get("current_state"), default=STATE_PENDING)
                if before_state == STATE_PAUSED and after_state in {STATE_RUNNABLE, STATE_COMPLETED, STATE_ESCALATED, STATE_FAILED_TERMINAL}:
                    jobs_resumed += 1
            finally:
                lease.release(job_id=job_id, holder=holder)

        return {
            "cycle_count": 1,
            "jobs_considered": jobs_considered,
            "jobs_claimed": jobs_claimed,
            "jobs_skipped_paused": jobs_skipped_paused,
            "jobs_skipped_retry_scheduled": jobs_skipped_retry_scheduled,
            "jobs_skipped_leased": jobs_skipped_leased,
            "jobs_run": jobs_run,
            "jobs_resumed": jobs_resumed,
            "jobs_paused": jobs_paused,
            "jobs_escalated": jobs_escalated,
            "jobs_completed": jobs_completed,
            "jobs_failed_terminal": jobs_failed_terminal,
            "registry_path": str(registry.path),
            "leases_path": str(lease.path),
        }

    def run_registry_cycles(
        self,
        *,
        artifacts_root: str | Path,
        output_root: str | Path,
        holder: str = "scheduler",
        lease_seconds: int = 120,
        max_jobs: int | None = None,
        max_cycles: int = 1,
        dry_run: bool = True,
        stop_on_failure: bool = True,
        max_retry_dispatches: int = 1,
        write_authority: Mapping[str, Any] | None = None,
        policy_snapshot: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        cycle_limit = max(1, int(max_cycles))
        summaries: list[dict[str, Any]] = []
        aggregate = {
            "cycle_count": 0,
            "jobs_considered": 0,
            "jobs_claimed": 0,
            "jobs_skipped_paused": 0,
            "jobs_skipped_retry_scheduled": 0,
            "jobs_skipped_leased": 0,
            "jobs_run": 0,
            "jobs_resumed": 0,
            "jobs_paused": 0,
            "jobs_escalated": 0,
            "jobs_completed": 0,
            "jobs_failed_terminal": 0,
        }
        for _ in range(cycle_limit):
            summary = self.run_registry_cycle(
                artifacts_root=artifacts_root,
                output_root=output_root,
                holder=holder,
                lease_seconds=lease_seconds,
                max_jobs=max_jobs,
                dry_run=dry_run,
                stop_on_failure=stop_on_failure,
                max_retry_dispatches=max_retry_dispatches,
                write_authority=write_authority,
                policy_snapshot=policy_snapshot,
            )
            summaries.append(summary)
            aggregate["cycle_count"] += 1
            for key in (
                "jobs_considered",
                "jobs_claimed",
                "jobs_skipped_paused",
                "jobs_skipped_retry_scheduled",
                "jobs_skipped_leased",
                "jobs_run",
                "jobs_resumed",
                "jobs_paused",
                "jobs_escalated",
                "jobs_completed",
                "jobs_failed_terminal",
            ):
                aggregate[key] += int(summary.get(key, 0))
        aggregate["cycles"] = summaries
        if summaries:
            aggregate["registry_path"] = summaries[-1].get("registry_path")
            aggregate["leases_path"] = summaries[-1].get("leases_path")
        return aggregate

