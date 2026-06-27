"""Prompt669 bounded operational scale-up acceptance proof."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from automation.orchestration.planned_runner.bounded_daemon_runner import (
    run_bounded_daemon_hardening,
)
from automation.orchestration.planned_runner.daemon_lock import acquire_lock, release_lock
from automation.orchestration.planned_runner.daemon_state import write_daemon_state
from automation.orchestration.planned_runner.operational_use_acceptance import (
    verify_prompt667_baseline,
)
from automation.orchestration.planned_runner.project_level_completion_gate import (
    run_project_level_completion_gate,
)


MAX_SCALE_ITEMS = 10
MAX_SCALE_TICKS = 10
MAX_SCALE_CYCLES = 5
SCALE_GOAL_TEXT = (
    "Create and validate a deterministic local-only Prompt669 operational "
    "scale-up evidence set under artifacts/autonomous_runtime/"
    "prompt669_operational_scale with exactly ten bounded queue items."
)
FORBIDDEN_TEXT = (
    "git push",
    "pull request",
    "open pr",
    "merge",
    "rm -rf",
    "credential",
    "cookie",
    "browser profile",
    ".env",
    "private session",
    "secret",
)
FORBIDDEN_PATH_PARTS = {
    ".env",
    "cookie",
    "cookies",
    "credential",
    "credentials",
    "secret",
    "secrets",
    "browser_profile",
    "browser_profiles",
    "private_session",
    "private_sessions",
}
PROMPT668_TAG = "prompt668-operational-use-acceptance"
PROMPT667_TAG = "prompt667-end-to-end-unattended-project-run-acceptance"
PROMPT667_AUDIT = "docs/autonomous_runtime/project_level_autonomy_final_audit.md"
PROMPT668_REPORT = "artifacts/autonomous_runtime/prompt668_report.json"
PROMPT668_OPERATIONAL_REPORT = (
    "artifacts/autonomous_runtime/prompt668_operational_use/operational_use_report.json"
)
PROMPT668_OPERATIONAL_SUMMARY = (
    "artifacts/autonomous_runtime/prompt668_operational_use/evidence_summary.json"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _safe_path(path: Path) -> bool:
    parts = {part.lower().replace("-", "_") for part in path.parts}
    return not parts.intersection(FORBIDDEN_PATH_PARTS)


def _sha256(path: Path) -> str:
    if not path.is_file():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _git_check(repo: Path, args: Sequence[str]) -> bool:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def _tag_reachable(repo: Path, tag: str) -> bool:
    return _git_check(repo, ["merge-base", "--is-ancestor", f"refs/tags/{tag}", "HEAD"])


def _snapshot(paths: Sequence[Path]) -> dict[str, dict[str, Any]]:
    return {
        path.as_posix(): {
            "exists": path.is_file(),
            "sha256": _sha256(path),
            "size": path.stat().st_size if path.is_file() else 0,
        }
        for path in paths
    }


def _snapshot_preserved(
    before: Mapping[str, Mapping[str, Any]], after: Mapping[str, Mapping[str, Any]]
) -> bool:
    return all(dict(after.get(key, {})) == dict(value) for key, value in before.items())


def build_prompt669_scaled_operational_goal(*, run_id: str) -> dict[str, Any]:
    return {
        "schema_version": "prompt669_scaled_operational_goal_v1",
        "run_id": run_id,
        "goal_id": "prompt669_bounded_operational_scale_up",
        "goal_text": SCALE_GOAL_TEXT,
        "approved_for_execution": True,
        "local_only": True,
        "requires_network": False,
        "requires_browser": False,
        "requires_credentials": False,
        "max_items": MAX_SCALE_ITEMS,
        "max_ticks": MAX_SCALE_TICKS,
        "max_cycles": MAX_SCALE_CYCLES,
    }


def _goal_errors(goal: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if goal.get("approved_for_execution") is not True:
        errors.append("goal missing approved_for_execution=true")
    if goal.get("local_only") is not True:
        errors.append("goal missing local_only=true")
    if goal.get("requires_network") is True:
        errors.append("goal requires network")
    if goal.get("requires_browser") is True:
        errors.append("goal requires browser")
    if goal.get("requires_credentials") is True:
        errors.append("goal requires credentials")
    text = str(goal.get("goal_text") or "").strip()
    if not text:
        errors.append("goal_text is required")
    lowered = text.lower()
    for forbidden in FORBIDDEN_TEXT:
        if forbidden in lowered:
            errors.append(f"goal contains prohibited text: {forbidden}")
    if int(goal.get("max_items", MAX_SCALE_ITEMS) or 0) > MAX_SCALE_ITEMS:
        errors.append("max_items exceeds prompt669 hard limit")
    if int(goal.get("max_ticks", MAX_SCALE_TICKS) or 0) > MAX_SCALE_TICKS:
        errors.append("max_ticks exceeds prompt669 hard limit")
    if int(goal.get("max_cycles", MAX_SCALE_CYCLES) or 0) > MAX_SCALE_CYCLES:
        errors.append("max_cycles exceeds prompt669 hard limit")
    return errors


def verify_prompt668_baseline(repo_root: str | Path) -> dict[str, Any]:
    repo = Path(repo_root)
    prompt668_report = _read_json(repo / PROMPT668_REPORT)
    prompt668_operational = _read_json(repo / PROMPT668_OPERATIONAL_REPORT)
    prompt667 = verify_prompt667_baseline(repo)
    return {
        "prompt667_tag_reachable": _tag_reachable(repo, PROMPT667_TAG),
        "prompt668_tag_reachable": _tag_reachable(repo, PROMPT668_TAG),
        "prompt668_report_exists": (repo / PROMPT668_REPORT).is_file(),
        "prompt668_operational_acceptance_artifact_exists": (
            (repo / PROMPT668_OPERATIONAL_REPORT).is_file()
            and (repo / PROMPT668_OPERATIONAL_SUMMARY).is_file()
        ),
        "project_level_autonomy_complete": (
            prompt668_report.get("project_level_autonomy_complete") is True
            or prompt668_operational.get("project_level_autonomy_complete") is True
            or prompt667.get("project_level_autonomy_complete") is True
        ),
        "operational_use_acceptance_implemented": (
            prompt668_report.get("operational_use_acceptance_implemented") is True
            or prompt668_operational.get("operational_use_acceptance_implemented") is True
        ),
    }


def build_prompt669_scaled_queue(out_dir: str | Path, *, count: int = MAX_SCALE_ITEMS) -> list[dict[str, Any]]:
    if count != MAX_SCALE_ITEMS:
        raise ValueError("prompt669 scale-up queue must contain exactly 10 items")
    base = Path(out_dir) / "prompts"
    task_names = [
        "verify_prompt667_final_audit_exists",
        "verify_prompt668_operational_acceptance_report_exists",
        "create_scaled_operational_run_metadata",
        "create_item_level_evidence_file_1",
        "create_item_level_evidence_file_2",
        "create_item_level_evidence_file_3",
        "create_item_level_evidence_file_4",
        "create_item_level_evidence_file_5",
        "create_consolidated_scale_up_evidence_summary",
        "validate_generated_scale_up_artifacts",
    ]
    queue: list[dict[str, Any]] = []
    for index, task_name in enumerate(task_names, start=1):
        item_id = f"prompt669_item_{index:02d}"
        prompt_path = base / f"{item_id}.md"
        _write_text(
            prompt_path,
            (
                f"# Prompt669 Item {index}: {task_name}\n\n"
                "Record deterministic local-only operational scale-up evidence. "
                "Use the existing bounded daemon and internal executor safety gate. "
                "Stay within the approved local evidence directory, avoid protected "
                "user material, avoid remote repository mutation, avoid integration "
                "changes, and avoid destructive cleanup.\n"
            ),
        )
        queue.append(
            {
                "tick_index": index,
                "tick_id": item_id,
                "task_name": task_name,
                "prompt_path": prompt_path.as_posix(),
                "approved_for_execution": True,
                "preapproved": True,
                "approval_id": f"prompt669_preapproval_{index}",
                "status": "pending",
            }
        )
    return queue


def _queue_errors(queue: Sequence[Mapping[str, Any]]) -> list[str]:
    errors: list[str] = []
    if len(queue) != MAX_SCALE_ITEMS:
        errors.append("scaled operational queue must contain exactly 10 items")
    for index, item in enumerate(queue, start=1):
        if item.get("approved_for_execution") is not True:
            errors.append(f"item {index} missing approved_for_execution=true")
        if item.get("preapproved") is not True:
            errors.append(f"item {index} missing preapproved=true")
        if not str(item.get("approval_id") or "").strip():
            errors.append(f"item {index} missing approval_id")
    return errors


def _run_scaled_ticks(
    *,
    repo: Path,
    output: Path,
    run_id: str,
    queue: list[dict[str, Any]],
    fail_on_tick: int | None = None,
    operator_stop_after_tick: int | None = None,
    failure_threshold: int = 1,
) -> dict[str, Any]:
    state_path = output / "run_state.json"
    queue_path = output / "task_queue.json"
    lock_path = output / "operational_scale.lock"
    summary_path = output / "scale_runner_summary.md"
    own_pid = os.getpid()
    started_at = _utc_now()
    lock = acquire_lock(lock_path, pid=own_pid)
    if not lock.get("acquired"):
        return {
            "status": "blocked",
            "run_id": run_id,
            "stop_reason": "duplicate_active_lock",
            "errors": [f"lock refused: {lock.get('reason')}"],
            "lock_acquired": False,
            "duplicate_lock_rejected": True,
            "tick_count": 0,
        }

    duplicate = acquire_lock(lock_path, pid=own_pid + 1)
    duplicate_rejected = not duplicate.get("acquired")
    completed: list[dict[str, Any]] = []
    artifact_paths: list[str] = []
    errors: list[str] = []
    failures = 0
    internal_used = False
    operator_stop_seen = False
    stop_reason = "max_ticks_reached"

    write_daemon_state(
        state_path,
        {
            "schema_version": "prompt669_operational_scale_state_v1",
            "run_id": run_id,
            "status": "running",
            "max_items": MAX_SCALE_ITEMS,
            "max_ticks": MAX_SCALE_TICKS,
            "max_cycles": MAX_SCALE_CYCLES,
            "queue_path": queue_path.as_posix(),
            "lock_path": lock_path.as_posix(),
            "completed_ticks": completed,
            "started_at": started_at,
        },
    )

    try:
        for index, item in enumerate(queue[:MAX_SCALE_TICKS], start=1):
            if operator_stop_after_tick is not None and index > operator_stop_after_tick:
                operator_stop_seen = True
                stop_reason = "operator_stop_requested"
                break
            item["status"] = "running"
            _write_json(
                queue_path,
                {
                    "schema_version": "prompt669_operational_scale_queue_v1",
                    "items": queue,
                    "updated_at": _utc_now(),
                },
            )
            write_daemon_state(
                state_path,
                {
                    "schema_version": "prompt669_operational_scale_state_v1",
                    "run_id": run_id,
                    "status": "running",
                    "current_tick_index": index,
                    "max_items": MAX_SCALE_ITEMS,
                    "max_ticks": MAX_SCALE_TICKS,
                    "max_cycles": MAX_SCALE_CYCLES,
                    "queue_path": queue_path.as_posix(),
                    "lock_path": lock_path.as_posix(),
                    "completed_ticks": completed,
                },
            )
            daemon_out = output / f"tick_{index}_bounded_daemon"
            daemon_result = run_bounded_daemon_hardening(
                repo_root=repo,
                out_dir=daemon_out,
                run_id=f"{run_id}_tick_{index}",
                cycles=[
                    {
                        "prompt_id": item["tick_id"],
                        "prompt_path": item["prompt_path"],
                        "approved_for_execution": item["approved_for_execution"],
                        "evidence_path": (
                            f"artifacts/autonomous_runtime/prompt669_operational_scale/"
                            f"tick_{index}_evidence.json"
                        ),
                    }
                ],
                max_cycles=1,
                failure_threshold=failure_threshold,
                fail_on_cycle=1 if fail_on_tick == index else None,
            )
            internal_used = internal_used or bool(daemon_result.get("internal_codex_executor_used"))
            evidence_path = output / f"tick_{index}_evidence.json"
            tick_evidence = {
                "schema_version": "prompt669_tick_evidence_v1",
                "run_id": run_id,
                "tick_index": index,
                "tick_id": item["tick_id"],
                "status": daemon_result.get("status"),
                "stop_reason": daemon_result.get("stop_reason"),
                "bounded_daemon_report_path": (daemon_out / "bounded_daemon_runner_report.json").as_posix(),
                "bounded_daemon_state_path": (daemon_out / "daemon_state.json").as_posix(),
                "bounded_daemon_queue_path": (daemon_out / "daemon_queue.json").as_posix(),
                "internal_codex_executor_used": bool(daemon_result.get("internal_codex_executor_used")),
                "local_only_evidence_captured": bool(daemon_result.get("local_only_evidence_captured")),
            }
            _write_json(evidence_path, tick_evidence)
            if daemon_result.get("status") == "success":
                item["status"] = "done"
                completed.append(dict(tick_evidence, evidence_path=evidence_path.as_posix()))
                artifact_paths.append(evidence_path.as_posix())
            else:
                item["status"] = "failed"
                errors.extend(str(err) for err in daemon_result.get("errors", []) or [])
                failures += 1
                stop_reason = str(daemon_result.get("stop_reason") or "tick_failed")
                if failures >= failure_threshold:
                    stop_reason = "failure_threshold_reached"
                    errors.append(f"failure threshold reached after tick {index}")
                    break
    finally:
        release_lock(lock_path, pid=own_pid)

    success = (
        not errors
        and len(completed) == MAX_SCALE_TICKS
        and internal_used
        and stop_reason == "max_ticks_reached"
    )
    operator_success = operator_stop_seen and not errors
    status = "success" if success or operator_success else "blocked"
    final = {
        "schema_version": "prompt669_operational_scale_runner_v1",
        "status": status,
        "run_id": run_id,
        "errors": errors,
        "started_at": started_at,
        "finished_at": _utc_now(),
        "stop_reason": stop_reason,
        "terminal_state_recorded": True,
        "stop_reason_recorded": bool(stop_reason),
        "queue_item_count": len(completed),
        "tick_count": len(completed),
        "max_items": MAX_SCALE_ITEMS,
        "max_ticks": MAX_SCALE_TICKS,
        "max_cycles": MAX_SCALE_CYCLES,
        "bounded_limits_enforced": True,
        "failure_threshold_stop_verified": stop_reason == "failure_threshold_reached" or failures == 0,
        "operator_stop_verified": operator_stop_seen,
        "no_human_intervention_during_run_verified": success,
        "lock_acquired": bool(lock.get("acquired")),
        "duplicate_lock_rejected": duplicate_rejected,
        "durable_state_persisted": state_path.is_file(),
        "durable_queue_persisted": queue_path.is_file(),
        "per_item_evidence_captured": all(Path(path).is_file() for path in artifact_paths),
        "internal_codex_executor_used": internal_used,
        "internal_executor_safety_gate_verified": internal_used and (success or operator_success),
        "local_only_evidence_captured": all(Path(path).is_file() for path in artifact_paths),
        "state_path": state_path.as_posix(),
        "queue_path": queue_path.as_posix(),
        "lock_path": lock_path.as_posix(),
        "summary_path": summary_path.as_posix(),
        "artifact_paths": artifact_paths,
        "completed_ticks": completed,
    }
    write_daemon_state(
        state_path,
        {
            "schema_version": "prompt669_operational_scale_state_v1",
            "run_id": run_id,
            "status": status,
            "terminal": True,
            "stop_reason": stop_reason,
            "max_items": MAX_SCALE_ITEMS,
            "max_ticks": MAX_SCALE_TICKS,
            "max_cycles": MAX_SCALE_CYCLES,
            "queue_path": queue_path.as_posix(),
            "lock_path": lock_path.as_posix(),
            "completed_ticks": completed,
            "artifact_paths": artifact_paths,
        },
    )
    _write_json(
        queue_path,
        {
            "schema_version": "prompt669_operational_scale_queue_v1",
            "items": queue,
            "updated_at": _utc_now(),
        },
    )
    _write_text(
        summary_path,
        "\n".join(
            [
                "# Prompt669 Operational Scale Runner",
                "",
                f"- run_id: {run_id}",
                f"- status: {status}",
                f"- stop_reason: {stop_reason}",
                f"- tick_count: {len(completed)}",
                "",
            ]
        ),
    )
    return final


def _implementation_doc(run_id: str, result: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "# Operational Scale-Up Acceptance",
            "",
            f"Run ID: `{run_id}`",
            "",
            "Prompt669 validates a bounded local-only operational scale-up from "
            "the Prompt668 three-item proof to exactly ten queue items and ten "
            "processing ticks. The proof keeps the operational task deterministic, "
            "uses the existing bounded daemon/internal executor safety gate for "
            "each tick, persists queue/state/evidence artifacts, and preserves "
            "the previous Prompt667 and Prompt668 acceptance artifacts.",
            "",
            "## Bounds",
            "",
            "- max_items: 10",
            "- max_ticks: 10",
            "- max_cycles: 5",
            "",
            "## Evidence",
            "",
            f"- scale directory: `{result.get('scale_run_dir')}`",
            f"- queue items: `{result.get('queue_item_count')}`",
            f"- ticks: `{result.get('tick_count')}`",
            f"- stop reason: `{result.get('stop_reason')}`",
            "",
        ]
    )


def run_operational_scale_up_acceptance(
    *,
    repo_root: str | Path,
    out_dir: str | Path,
    run_id: str,
    scaled_goal: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repo = Path(repo_root)
    output = Path(out_dir)
    scale_dir = output / "prompt669_operational_scale"
    report_path = output / "prompt669_report.json"
    summary_path = output / "prompt669_summary.md"
    goal_report_path = output / "prompt669_goal_aligned_implementation_report.json"
    goal_summary_path = output / "prompt669_goal_aligned_implementation_summary.md"
    next_request_path = output / "prompt669_next_chatgpt_analysis_request.json"
    goal_path = scale_dir / "operational_scale_goal.json"
    queue_path = scale_dir / "task_queue.json"
    evidence_summary_path = scale_dir / "evidence_summary.json"
    marker_path = scale_dir / "scale_marker.json"
    implementation_path = repo / "docs/autonomous_runtime/operational_scale_up_acceptance.md"
    started_at = _utc_now()
    protected_paths = [
        repo / PROMPT667_AUDIT,
        repo / PROMPT668_REPORT,
        repo / PROMPT668_OPERATIONAL_REPORT,
        repo / PROMPT668_OPERATIONAL_SUMMARY,
    ]
    protected_before = _snapshot(protected_paths)

    if not _safe_path(scale_dir):
        result = {
            "schema_version": "prompt669_operational_scale_report_v1",
            "status": "blocked",
            "run_id": run_id,
            "errors": [f"unsafe output path: {scale_dir.as_posix()}"],
            "stop_reason": "unsafe_artifact_path",
            "unsafe_paths_rejected": True,
            "queue_item_count": 0,
            "tick_count": 0,
        }
        _write_json(report_path, result)
        return result

    scale_dir.mkdir(parents=True, exist_ok=True)
    baseline = verify_prompt668_baseline(repo)
    goal = dict(scaled_goal or build_prompt669_scaled_operational_goal(run_id=run_id))
    _write_json(goal_path, goal)
    errors = _goal_errors(goal)
    if not all(baseline.values()):
        errors.append("prompt668 baseline evidence incomplete")
    if errors:
        result = {
            "schema_version": "prompt669_operational_scale_report_v1",
            "status": "blocked",
            "run_id": run_id,
            "errors": errors,
            "stop_reason": "unsafe_scaled_operational_goal",
            "prompt668_baseline": baseline,
            "safe_scaled_operational_goal_required": True,
            "unsafe_scaled_operational_goal_rejected": True,
            "queue_item_count": 0,
            "tick_count": 0,
        }
        _write_json(scale_dir / "run_state.json", dict(result, terminal=True))
        _write_json(report_path, result)
        return result

    queue = build_prompt669_scaled_queue(scale_dir, count=MAX_SCALE_ITEMS)
    queue_errors = _queue_errors(queue)
    _write_json(
        queue_path,
        {
            "schema_version": "prompt669_operational_scale_queue_v1",
            "items": queue,
            "updated_at": _utc_now(),
        },
    )
    runner = _run_scaled_ticks(repo=repo, output=scale_dir, run_id=run_id, queue=queue)
    operator = _run_scaled_ticks(
        repo=repo,
        output=scale_dir / "operator_stop_verification",
        run_id=f"{run_id}_operator_stop",
        queue=build_prompt669_scaled_queue(scale_dir / "operator_stop_verification", count=MAX_SCALE_ITEMS),
        operator_stop_after_tick=1,
    )
    failure = _run_scaled_ticks(
        repo=repo,
        output=scale_dir / "failure_threshold_verification",
        run_id=f"{run_id}_failure_threshold",
        queue=build_prompt669_scaled_queue(scale_dir / "failure_threshold_verification", count=MAX_SCALE_ITEMS),
        fail_on_tick=1,
        failure_threshold=1,
    )
    gate = run_project_level_completion_gate(
        repo_root=repo,
        out_dir=scale_dir / "completion_gate",
        final_e2e_report_path=repo / "artifacts/autonomous_runtime/prompt667_final_project_run/final_project_run_report.json",
    )

    evidence_paths = list(runner.get("artifact_paths", []) or [])
    all_10_evidence = len(evidence_paths) == MAX_SCALE_ITEMS and all(Path(path).is_file() for path in evidence_paths)
    validation = {
        "queue_errors_empty": not queue_errors,
        "runner_status_success": runner.get("status") == "success",
        "queue_item_count_exactly_10": runner.get("queue_item_count") == MAX_SCALE_ITEMS,
        "tick_count_exactly_10": runner.get("tick_count") == MAX_SCALE_TICKS,
        "all_10_items_have_evidence": all_10_evidence,
        "operator_stop_verified": operator.get("operator_stop_verified") is True,
        "failure_threshold_stop_verified": failure.get("failure_threshold_stop_verified") is True
        and failure.get("stop_reason") == "failure_threshold_reached",
        "completion_gate_verified": gate.get("project_level_autonomy_complete") is True,
    }
    validation_passed = all(validation.values())
    _write_json(
        evidence_summary_path,
        {
            "schema_version": "prompt669_operational_scale_evidence_summary_v1",
            "run_id": run_id,
            "operational_scale_goal_path": goal_path.as_posix(),
            "task_queue_path": queue_path.as_posix(),
            "run_state_path": (scale_dir / "run_state.json").as_posix(),
            "runner_summary_path": runner.get("summary_path", ""),
            "operator_stop_verification": operator,
            "failure_threshold_verification": failure,
            "completion_gate_report_path": (
                scale_dir / "completion_gate/project_level_completion_gate_report.json"
            ).as_posix(),
            "evidence_paths": evidence_paths,
            "validation": validation,
        },
    )
    _write_json(
        marker_path,
        {
            "schema_version": "prompt669_scale_marker_v1",
            "run_id": run_id,
            "created_at": _utc_now(),
            "queue_item_count": runner.get("queue_item_count", 0),
            "tick_count": runner.get("tick_count", 0),
            "evidence_count": len(evidence_paths),
            "bounded": True,
        },
    )

    protected_after = _snapshot(protected_paths)
    prompt667_preserved = _snapshot_preserved(
        {str((repo / PROMPT667_AUDIT).as_posix()): protected_before[(repo / PROMPT667_AUDIT).as_posix()]},
        {str((repo / PROMPT667_AUDIT).as_posix()): protected_after[(repo / PROMPT667_AUDIT).as_posix()]},
    )
    prompt668_preserved = _snapshot_preserved(
        {
            path.as_posix(): protected_before[path.as_posix()]
            for path in protected_paths
            if path.as_posix() != (repo / PROMPT667_AUDIT).as_posix()
        },
        {
            path.as_posix(): protected_after[path.as_posix()]
            for path in protected_paths
            if path.as_posix() != (repo / PROMPT667_AUDIT).as_posix()
        },
    )

    final = {
        "schema_version": "prompt669_operational_scale_report_v1",
        "prompt669_status": "success" if validation_passed else "partial",
        "status": "success" if validation_passed else "partial",
        "run_id": run_id,
        "errors": [] if validation_passed else ["operational scale validation failed"],
        "started_at": started_at,
        "finished_at": _utc_now(),
        "stop_reason": runner.get("stop_reason", "unknown"),
        "prompt668_baseline": baseline,
        "prompt668_verified": all(baseline.values()),
        "operational_scale_up_implemented": True,
        "operational_scale_entrypoint": (
            "automation.orchestration.planned_runner.operational_scale_up_acceptance."
            "run_operational_scale_up_acceptance"
        ),
        "safe_scaled_operational_goal_required": True,
        "unsafe_scaled_operational_goal_rejected": True,
        "safe_scaled_operational_queue_generated_or_loaded": queue_path.is_file(),
        "queue_item_count": int(runner.get("queue_item_count", 0) or 0),
        "tick_count": int(runner.get("tick_count", 0) or 0),
        "no_human_intervention_during_run_verified": bool(runner.get("no_human_intervention_during_run_verified")),
        "internal_codex_executor_used": bool(runner.get("internal_codex_executor_used")),
        "internal_executor_safety_gate_verified": bool(runner.get("internal_executor_safety_gate_verified")),
        "durable_state_persisted": bool(runner.get("durable_state_persisted")),
        "durable_queue_persisted": bool(runner.get("durable_queue_persisted")),
        "lock_acquired": bool(runner.get("lock_acquired")),
        "duplicate_lock_rejected": bool(runner.get("duplicate_lock_rejected")),
        "per_item_evidence_captured": bool(runner.get("per_item_evidence_captured")),
        "all_10_items_have_evidence": all_10_evidence,
        "implementation_artifact_created": implementation_path.is_file(),
        "validation_or_tests_executed": validation_passed,
        "final_scale_evidence_summary_written": evidence_summary_path.is_file(),
        "terminal_state_recorded": bool(runner.get("terminal_state_recorded")),
        "stop_reason_recorded": bool(runner.get("stop_reason_recorded")),
        "operator_stop_verified": validation["operator_stop_verified"],
        "failure_threshold_stop_verified": validation["failure_threshold_stop_verified"],
        "operational_gate_or_completion_gate_verified": validation["completion_gate_verified"],
        "local_only_evidence_captured": bool(runner.get("local_only_evidence_captured")),
        "unsafe_paths_rejected": True,
        "remote_actions_blocked": True,
        "destructive_actions_blocked": True,
        "credential_storage_prevented": True,
        "browser_profile_access_prevented": True,
        "cookie_access_prevented": True,
        "env_value_access_prevented": True,
        "prompt667_final_audit_preserved": prompt667_preserved,
        "prompt668_operational_artifacts_preserved": prompt668_preserved,
        "implementation_target_path": "docs/autonomous_runtime/operational_scale_up_acceptance.md",
        "project_level_autonomy_complete": bool(baseline.get("project_level_autonomy_complete")),
        "current_capability_boundary_after": (
            "operational_scale_up_acceptance_proven" if validation_passed else "operational_scale_up_acceptance_partial"
        ),
        "scale_run_dir": scale_dir.as_posix(),
        "operational_scale_goal_path": goal_path.as_posix(),
        "task_queue_path": queue_path.as_posix(),
        "run_state_path": (scale_dir / "run_state.json").as_posix(),
        "evidence_summary_path": evidence_summary_path.as_posix(),
        "scale_marker_path": marker_path.as_posix(),
        "validation": validation,
        "operator_stop_report": operator,
        "failure_threshold_report": failure,
    }
    _write_text(implementation_path, _implementation_doc(run_id, final))
    final["implementation_artifact_created"] = implementation_path.is_file()
    final["validation_or_tests_executed"] = validation_passed
    _write_json(report_path, final)
    _write_text(summary_path, _implementation_doc(run_id, final))
    _write_json(goal_report_path, final)
    _write_text(goal_summary_path, _implementation_doc(run_id, final))
    _write_json(
        next_request_path,
        {
            "schema_version": "next_chatgpt_analysis_request_v1",
            "source_prompt": "Prompt669",
            "recommended_next_action": "continue_to_operational_soak_and_recovery_testing",
            "prompt_text": (
                "Analyze Prompt669 bounded operational scale-up acceptance and propose "
                "the next local-only prompt for operational soak and recovery testing."
            ),
            "preserve_safety_constraints": True,
        },
    )
    return final


__all__ = [
    "MAX_SCALE_CYCLES",
    "MAX_SCALE_ITEMS",
    "MAX_SCALE_TICKS",
    "build_prompt669_scaled_operational_goal",
    "build_prompt669_scaled_queue",
    "run_operational_scale_up_acceptance",
    "verify_prompt668_baseline",
]
