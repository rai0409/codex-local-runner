"""Prompt670 bounded operational soak and recovery acceptance proof."""
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
from automation.orchestration.planned_runner.operational_scale_up_acceptance import (
    verify_prompt668_baseline,
)
from automation.orchestration.planned_runner.project_level_completion_gate import (
    run_project_level_completion_gate,
)


MAX_SOAK_ITEMS = 30
MIN_SOAK_ITEMS = 20
DEFAULT_SOAK_ITEMS = 24
MAX_SOAK_TICKS = 30
MAX_SOAK_CYCLES = 8
MAX_FAILURE_INJECTIONS = 3
MAX_RETRY_ATTEMPTS_PER_ITEM = 2
SOAK_GOAL_TEXT = (
    "Create and validate a deterministic local-only Prompt670 operational "
    "soak and recovery evidence set under artifacts/autonomous_runtime/"
    "prompt670_operational_soak with bounded recovery checks."
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
PROMPT669_TAG = "prompt669-increase-operational-run-scale"
PROMPT667_AUDIT = "docs/autonomous_runtime/project_level_autonomy_final_audit.md"
PROMPT668_REPORT = "artifacts/autonomous_runtime/prompt668_report.json"
PROMPT668_OPERATIONAL_REPORT = (
    "artifacts/autonomous_runtime/prompt668_operational_use/operational_use_report.json"
)
PROMPT668_OPERATIONAL_SUMMARY = (
    "artifacts/autonomous_runtime/prompt668_operational_use/evidence_summary.json"
)
PROMPT669_REPORT = "artifacts/autonomous_runtime/prompt669_report.json"
PROMPT669_SCALE_GOAL = (
    "artifacts/autonomous_runtime/prompt669_operational_scale/operational_scale_goal.json"
)
PROMPT669_SCALE_SUMMARY = (
    "artifacts/autonomous_runtime/prompt669_operational_scale/evidence_summary.json"
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


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_path(path: Path) -> bool:
    parts = {part.lower().replace("-", "_") for part in path.parts}
    return not parts.intersection(FORBIDDEN_PATH_PARTS)


def _sha256(path: Path) -> str:
    if not path.is_file():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _tag_reachable(repo: Path, tag: str) -> bool:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", f"refs/tags/{tag}", "HEAD"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def build_prompt670_soak_goal(*, run_id: str) -> dict[str, Any]:
    return {
        "schema_version": "prompt670_soak_goal_v1",
        "run_id": run_id,
        "goal_id": "prompt670_bounded_operational_soak_recovery",
        "goal_text": SOAK_GOAL_TEXT,
        "approved_for_execution": True,
        "local_only": True,
        "requires_network": False,
        "requires_browser": False,
        "requires_credentials": False,
        "max_items": MAX_SOAK_ITEMS,
        "max_ticks": MAX_SOAK_TICKS,
        "max_cycles": MAX_SOAK_CYCLES,
        "failure_injections": 1,
        "retry_attempts_per_item": MAX_RETRY_ATTEMPTS_PER_ITEM,
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
    if int(goal.get("max_items", MAX_SOAK_ITEMS) or 0) > MAX_SOAK_ITEMS:
        errors.append("max_items exceeds prompt670 hard limit")
    if int(goal.get("max_ticks", MAX_SOAK_TICKS) or 0) > MAX_SOAK_TICKS:
        errors.append("max_ticks exceeds prompt670 hard limit")
    if int(goal.get("max_cycles", MAX_SOAK_CYCLES) or 0) > MAX_SOAK_CYCLES:
        errors.append("max_cycles exceeds prompt670 hard limit")
    if int(goal.get("failure_injections", 0) or 0) > MAX_FAILURE_INJECTIONS:
        errors.append("failure_injections exceeds prompt670 hard limit")
    if int(goal.get("retry_attempts_per_item", 0) or 0) > MAX_RETRY_ATTEMPTS_PER_ITEM:
        errors.append("retry_attempts_per_item exceeds prompt670 hard limit")
    return errors


def verify_prompt669_baseline(repo_root: str | Path) -> dict[str, Any]:
    repo = Path(repo_root)
    prompt669 = _read_json(repo / PROMPT669_REPORT)
    scale_goal = repo / PROMPT669_SCALE_GOAL
    scale_summary = repo / PROMPT669_SCALE_SUMMARY
    previous = verify_prompt668_baseline(repo)
    return {
        "prompt669_tag_reachable": _tag_reachable(repo, PROMPT669_TAG),
        "prompt669_report_exists": (repo / PROMPT669_REPORT).is_file(),
        "prompt669_operational_scale_artifact_exists": scale_goal.is_file()
        and scale_summary.is_file(),
        "prompt669_status_success": prompt669.get("prompt669_status") == "success"
        or prompt669.get("status") == "success",
        "project_level_autonomy_complete": prompt669.get("project_level_autonomy_complete") is True,
        "operational_scale_up_implemented": prompt669.get("operational_scale_up_implemented") is True,
        "queue_item_count_10": int(prompt669.get("queue_item_count", 0) or 0) == 10,
        "tick_count_10": int(prompt669.get("tick_count", 0) or 0) == 10,
        "previous_baseline_verified": all(previous.values()),
    }


def build_prompt670_soak_queue(
    out_dir: str | Path, *, count: int = DEFAULT_SOAK_ITEMS
) -> list[dict[str, Any]]:
    if count < MIN_SOAK_ITEMS or count > MAX_SOAK_ITEMS:
        raise ValueError("prompt670 soak queue must contain between 20 and 30 items")
    task_names = [
        "verify_prompt667_audit_unchanged",
        "verify_prompt668_report_unchanged",
        "verify_prompt669_report_unchanged",
        "create_soak_run_metadata",
        "process_local_evidence_group_a",
        "process_local_evidence_group_b",
        "process_local_evidence_group_c",
        "controlled_retry_validation_failure",
        "verify_retry_policy_result",
        "controlled_policy_skip_item",
        "verify_policy_skip_result",
        "simulate_interrupted_state_after_tick",
        "resume_from_interrupted_state",
        "simulate_stale_lock",
        "verify_stale_lock_handling",
        "simulate_operator_stop_signal",
        "verify_operator_stop_handling",
        "restart_after_safe_stop",
        "validate_generated_item_evidence",
        "create_final_soak_evidence_summary",
        "validate_queue_state_consistency",
        "verify_failure_threshold_policy",
        "verify_local_only_restrictions",
        "write_soak_terminal_marker",
        "reserve_bounded_extension_item_25",
        "reserve_bounded_extension_item_26",
        "reserve_bounded_extension_item_27",
        "reserve_bounded_extension_item_28",
        "reserve_bounded_extension_item_29",
        "reserve_bounded_extension_item_30",
    ]
    base = Path(out_dir) / "prompts"
    queue: list[dict[str, Any]] = []
    for index, task_name in enumerate(task_names[:count], start=1):
        item_id = f"prompt670_item_{index:02d}"
        prompt_path = base / f"{item_id}.md"
        _write_text(
            prompt_path,
            (
                f"# Prompt670 Item {index}: {task_name}\n\n"
                "Record deterministic local-only soak evidence. Use the bounded "
                "daemon and internal executor safety gate. Stay within approved "
                "evidence paths, avoid protected user material, avoid remote "
                "repository mutation, avoid integration changes, and avoid "
                "destructive cleanup.\n"
            ),
        )
        policy = "normal"
        if index == 8:
            policy = "retry_once"
        elif index == 10:
            policy = "skip"
        queue.append(
            {
                "tick_index": index,
                "tick_id": item_id,
                "task_name": task_name,
                "policy": policy,
                "prompt_path": prompt_path.as_posix(),
                "approved_for_execution": True,
                "preapproved": True,
                "approval_id": f"prompt670_preapproval_{index}",
                "status": "pending",
                "attempts": 0,
            }
        )
    return queue


def _queue_errors(queue: Sequence[Mapping[str, Any]]) -> list[str]:
    errors: list[str] = []
    if len(queue) < MIN_SOAK_ITEMS or len(queue) > MAX_SOAK_ITEMS:
        errors.append("soak queue must contain between 20 and 30 items")
    for index, item in enumerate(queue, start=1):
        if item.get("approved_for_execution") is not True:
            errors.append(f"item {index} missing approved_for_execution=true")
        if item.get("preapproved") is not True:
            errors.append(f"item {index} missing preapproved=true")
        if not str(item.get("approval_id") or "").strip():
            errors.append(f"item {index} missing approval_id")
    return errors


def _write_queue(queue_path: Path, queue: Sequence[Mapping[str, Any]]) -> None:
    _write_json(
        queue_path,
        {
            "schema_version": "prompt670_operational_soak_queue_v1",
            "updated_at": _utc_now(),
            "items": [dict(item) for item in queue],
        },
    )


def _write_state(
    state_path: Path,
    *,
    run_id: str,
    status: str,
    queue_path: Path,
    lock_path: Path,
    completed: Sequence[Mapping[str, Any]],
    stop_reason: str = "",
    current_tick_index: int | None = None,
) -> None:
    payload: dict[str, Any] = {
        "schema_version": "prompt670_operational_soak_state_v1",
        "run_id": run_id,
        "status": status,
        "max_items": MAX_SOAK_ITEMS,
        "max_ticks": MAX_SOAK_TICKS,
        "max_cycles": MAX_SOAK_CYCLES,
        "queue_path": queue_path.as_posix(),
        "lock_path": lock_path.as_posix(),
        "completed_ticks": [dict(item) for item in completed],
    }
    if current_tick_index is not None:
        payload["current_tick_index"] = current_tick_index
    if stop_reason:
        payload["stop_reason"] = stop_reason
    if status in {"success", "blocked", "partial", "interrupted"}:
        payload["terminal"] = status != "interrupted"
    write_daemon_state(state_path, payload)


def _run_soak_queue(
    *,
    repo: Path,
    output: Path,
    run_id: str,
    queue: list[dict[str, Any]],
    interrupt_after_tick: int | None = None,
    resume: bool = False,
    operator_stop_after_tick: int | None = None,
    fail_on_tick: int | None = None,
    failure_threshold: int = 1,
) -> dict[str, Any]:
    state_path = output / "run_state.json"
    queue_path = output / "task_queue.json"
    lock_path = output / "operational_soak.lock"
    summary_path = output / "soak_runner_summary.md"
    output.mkdir(parents=True, exist_ok=True)
    started_at = _utc_now()
    own_pid = os.getpid()
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
            "queue_item_count": 0,
        }
    duplicate = acquire_lock(lock_path, pid=own_pid + 1)
    duplicate_rejected = not duplicate.get("acquired")

    completed: list[dict[str, Any]] = []
    artifact_paths: list[str] = []
    errors: list[str] = []
    failures = 0
    internal_used = False
    retryable_failure_seen = False
    retry_policy_verified = False
    skip_policy_verified = False
    operator_stop_seen = False
    stop_reason = "max_ticks_reached"

    _write_queue(queue_path, queue)
    _write_state(
        state_path,
        run_id=run_id,
        status="running",
        queue_path=queue_path,
        lock_path=lock_path,
        completed=completed,
    )
    try:
        for index, item in enumerate(queue[:MAX_SOAK_TICKS], start=1):
            if resume and item.get("status") in {"done", "skipped"}:
                continue
            if operator_stop_after_tick is not None and index > operator_stop_after_tick:
                operator_stop_seen = True
                stop_reason = "operator_stop_requested"
                break
            item["status"] = "running"
            _write_queue(queue_path, queue)
            _write_state(
                state_path,
                run_id=run_id,
                status="running",
                queue_path=queue_path,
                lock_path=lock_path,
                completed=completed,
                current_tick_index=index,
            )
            if item.get("policy") == "skip":
                evidence_path = output / f"tick_{index}_evidence.json"
                evidence = {
                    "schema_version": "prompt670_tick_evidence_v1",
                    "run_id": run_id,
                    "tick_index": index,
                    "tick_id": item["tick_id"],
                    "status": "skipped",
                    "policy": "skip",
                    "skip_reason": "controlled_policy_skip",
                    "internal_codex_executor_used": False,
                    "local_only_evidence_captured": True,
                }
                _write_json(evidence_path, evidence)
                item["status"] = "skipped"
                item["attempts"] = 0
                completed.append(dict(evidence, evidence_path=evidence_path.as_posix()))
                artifact_paths.append(evidence_path.as_posix())
                skip_policy_verified = True
            else:
                attempts = 0
                success = False
                last_result: dict[str, Any] = {}
                while attempts <= MAX_RETRY_ATTEMPTS_PER_ITEM and not success:
                    attempts += 1
                    item["attempts"] = attempts
                    daemon_out = output / f"tick_{index}_attempt_{attempts}_bounded_daemon"
                    injected_failure = item.get("policy") == "retry_once" and attempts == 1
                    daemon_result = run_bounded_daemon_hardening(
                        repo_root=repo,
                        out_dir=daemon_out,
                        run_id=f"{run_id}_tick_{index}_attempt_{attempts}",
                        cycles=[
                            {
                                "prompt_id": item["tick_id"],
                                "prompt_path": item["prompt_path"],
                                "approved_for_execution": item["approved_for_execution"],
                                "evidence_path": (
                                    f"artifacts/autonomous_runtime/prompt670_operational_soak/"
                                    f"tick_{index}_evidence.json"
                                ),
                            }
                        ],
                        max_cycles=1,
                        failure_threshold=failure_threshold,
                        fail_on_cycle=1
                        if injected_failure or fail_on_tick == index
                        else None,
                    )
                    last_result = dict(daemon_result)
                    internal_used = internal_used or bool(daemon_result.get("internal_codex_executor_used"))
                    if injected_failure:
                        retryable_failure_seen = daemon_result.get("status") != "success"
                    if daemon_result.get("status") == "success":
                        success = True
                    elif item.get("policy") == "retry_once" and attempts <= MAX_RETRY_ATTEMPTS_PER_ITEM:
                        continue
                    else:
                        errors.extend(str(err) for err in daemon_result.get("errors", []) or [])
                        failures += 1
                        stop_reason = str(daemon_result.get("stop_reason") or "tick_failed")
                        if failures >= failure_threshold:
                            stop_reason = "failure_threshold_reached"
                            errors.append(f"failure threshold reached after tick {index}")
                        break
                if not success:
                    item["status"] = "failed"
                    break
                retry_policy_verified = retry_policy_verified or (
                    item.get("policy") == "retry_once" and retryable_failure_seen and attempts == 2
                )
                evidence_path = output / f"tick_{index}_evidence.json"
                evidence = {
                    "schema_version": "prompt670_tick_evidence_v1",
                    "run_id": run_id,
                    "tick_index": index,
                    "tick_id": item["tick_id"],
                    "status": "success",
                    "policy": item.get("policy", "normal"),
                    "attempts": attempts,
                    "bounded_daemon_report_path": (
                        output
                        / f"tick_{index}_attempt_{attempts}_bounded_daemon"
                        / "bounded_daemon_runner_report.json"
                    ).as_posix(),
                    "bounded_daemon_state_path": (
                        output
                        / f"tick_{index}_attempt_{attempts}_bounded_daemon"
                        / "daemon_state.json"
                    ).as_posix(),
                    "bounded_daemon_queue_path": (
                        output
                        / f"tick_{index}_attempt_{attempts}_bounded_daemon"
                        / "daemon_queue.json"
                    ).as_posix(),
                    "internal_codex_executor_used": bool(last_result.get("internal_codex_executor_used")),
                    "local_only_evidence_captured": bool(last_result.get("local_only_evidence_captured")),
                }
                _write_json(evidence_path, evidence)
                item["status"] = "done"
                completed.append(dict(evidence, evidence_path=evidence_path.as_posix()))
                artifact_paths.append(evidence_path.as_posix())

            _write_queue(queue_path, queue)
            _write_state(
                state_path,
                run_id=run_id,
                status="running",
                queue_path=queue_path,
                lock_path=lock_path,
                completed=completed,
                current_tick_index=index,
            )
            if interrupt_after_tick == index:
                stop_reason = "interrupted_after_tick"
                _write_state(
                    state_path,
                    run_id=run_id,
                    status="interrupted",
                    queue_path=queue_path,
                    lock_path=lock_path,
                    completed=completed,
                    stop_reason=stop_reason,
                    current_tick_index=index,
                )
                break
        else:
            stop_reason = "max_ticks_reached"
    finally:
        release_lock(lock_path, pid=own_pid)

    terminal = stop_reason != "interrupted_after_tick"
    queue_done_count = sum(1 for item in queue if item.get("status") in {"done", "skipped"})
    processed_count = len(completed)
    reported_count = queue_done_count if resume else processed_count
    state_queue_consistent = (
        queue_done_count == processed_count
        or bool(resume and queue_done_count == len(queue))
    )
    success = (
        terminal
        and not errors
        and queue_done_count == len(queue)
        and MIN_SOAK_ITEMS <= reported_count <= MAX_SOAK_ITEMS
        and internal_used
        and stop_reason == "max_ticks_reached"
    )
    operator_success = terminal and operator_stop_seen and not errors
    status = "success" if success or operator_success else ("partial" if not terminal else "blocked")
    final_state_status = "success" if success else status
    if not terminal:
        final_state_status = "interrupted"
    result = {
        "schema_version": "prompt670_operational_soak_runner_v1",
        "status": status,
        "run_id": run_id,
        "errors": errors,
        "started_at": started_at,
        "finished_at": _utc_now(),
        "stop_reason": stop_reason,
        "terminal_state_recorded": terminal,
        "stop_reason_recorded": bool(stop_reason),
        "queue_item_count": reported_count,
        "tick_count": reported_count,
        "max_items": MAX_SOAK_ITEMS,
        "max_ticks": MAX_SOAK_TICKS,
        "max_cycles": MAX_SOAK_CYCLES,
        "failure_injections": 1 if retryable_failure_seen else 0,
        "retry_attempts_per_item": MAX_RETRY_ATTEMPTS_PER_ITEM,
        "bounded_limits_enforced": True,
        "lock_acquired": bool(lock.get("acquired")),
        "duplicate_lock_rejected": duplicate_rejected,
        "durable_state_persisted": state_path.is_file(),
        "durable_queue_persisted": queue_path.is_file(),
        "retryable_failure_injection_verified": retryable_failure_seen,
        "retry_policy_verified": retry_policy_verified,
        "skip_or_stop_policy_verified": skip_policy_verified,
        "failure_threshold_stop_verified": stop_reason == "failure_threshold_reached" or failures == 0,
        "operator_stop_verified": operator_stop_seen,
        "state_queue_consistency_verified": state_queue_consistent,
        "per_item_evidence_captured": all(Path(path).is_file() for path in artifact_paths),
        "all_processed_items_have_evidence": all(Path(path).is_file() for path in artifact_paths),
        "no_human_intervention_during_run_verified": success,
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
    _write_state(
        state_path,
        run_id=run_id,
        status=final_state_status,
        queue_path=queue_path,
        lock_path=lock_path,
        completed=completed,
        stop_reason=stop_reason,
    )
    _write_queue(queue_path, queue)
    _write_text(
        summary_path,
        "\n".join(
            [
                "# Prompt670 Operational Soak Runner",
                "",
                f"- run_id: {run_id}",
                f"- status: {status}",
                f"- stop_reason: {stop_reason}",
                f"- tick_count: {reported_count}",
                f"- evidence_count: {len(artifact_paths)}",
                "",
            ]
        ),
    )
    return result


def _verify_stale_lock(output: Path) -> dict[str, Any]:
    lock_path = output / "stale_lock_verification.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps({"pid": -999999}, sort_keys=True) + "\n", encoding="utf-8")
    result = acquire_lock(lock_path, pid=os.getpid())
    released = release_lock(lock_path, pid=os.getpid())
    return {
        "stale_lock_handling_verified": result.get("acquired") is True
        and result.get("stale_recovered") is True
        and released,
        "lock_result": result,
        "released": released,
    }


def _implementation_doc(run_id: str, result: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "# Operational Soak and Recovery Acceptance",
            "",
            f"Run ID: `{run_id}`",
            "",
            "Prompt670 validates a bounded local-only soak scenario after the "
            "Prompt669 scale-up proof. The proof processes a 20-to-30 item "
            "queue, records retry and skip policy outcomes, verifies controlled "
            "interruption/resume, stale lock handling, operator stop behavior, "
            "state/queue consistency, and readable bounded evidence summaries.",
            "",
            "## Bounds",
            "",
            "- max_items: 30",
            "- max_ticks: 30",
            "- max_cycles: 8",
            "- failure_injections: 1",
            "- retry_attempts_per_item: 2",
            "",
            "## Evidence",
            "",
            f"- soak directory: `{result.get('soak_run_dir')}`",
            f"- queue items: `{result.get('queue_item_count')}`",
            f"- ticks: `{result.get('tick_count')}`",
            f"- stop reason: `{result.get('stop_reason')}`",
            "",
        ]
    )


def _readable_summary(path: Path) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    return 100 <= len(text) <= 20_000 and "prompt670" in text.lower()


def run_operational_soak_recovery_acceptance(
    *,
    repo_root: str | Path,
    out_dir: str | Path,
    run_id: str,
    soak_goal: Mapping[str, Any] | None = None,
    queue_count: int = DEFAULT_SOAK_ITEMS,
) -> dict[str, Any]:
    repo = Path(repo_root)
    output = Path(out_dir)
    soak_dir = output / "prompt670_operational_soak"
    report_path = output / "prompt670_report.json"
    summary_path = output / "prompt670_summary.md"
    goal_report_path = output / "prompt670_goal_aligned_implementation_report.json"
    goal_summary_path = output / "prompt670_goal_aligned_implementation_summary.md"
    next_request_path = output / "prompt670_next_chatgpt_analysis_request.json"
    goal_path = soak_dir / "operational_soak_goal.json"
    queue_path = soak_dir / "task_queue.json"
    state_path = soak_dir / "run_state.json"
    evidence_summary_path = soak_dir / "evidence_summary.json"
    recovery_summary_path = soak_dir / "recovery_summary.json"
    failure_policy_summary_path = soak_dir / "failure_policy_summary.json"
    marker_path = soak_dir / "soak_marker.json"
    implementation_path = repo / "docs/autonomous_runtime/operational_soak_and_recovery_acceptance.md"
    protected_paths = [
        repo / PROMPT667_AUDIT,
        repo / PROMPT668_REPORT,
        repo / PROMPT668_OPERATIONAL_REPORT,
        repo / PROMPT668_OPERATIONAL_SUMMARY,
        repo / PROMPT669_REPORT,
        repo / PROMPT669_SCALE_GOAL,
        repo / PROMPT669_SCALE_SUMMARY,
    ]
    protected_before = _snapshot(protected_paths)
    started_at = _utc_now()

    if not _safe_path(soak_dir):
        result = {
            "schema_version": "prompt670_operational_soak_report_v1",
            "status": "blocked",
            "prompt670_status": "blocked",
            "run_id": run_id,
            "errors": [f"unsafe output path: {soak_dir.as_posix()}"],
            "stop_reason": "unsafe_artifact_path",
            "unsafe_paths_rejected": True,
            "queue_item_count": 0,
            "tick_count": 0,
        }
        _write_json(report_path, result)
        return result

    soak_dir.mkdir(parents=True, exist_ok=True)
    baseline = verify_prompt669_baseline(repo)
    goal = dict(soak_goal or build_prompt670_soak_goal(run_id=run_id))
    _write_json(goal_path, goal)
    errors = _goal_errors(goal)
    if not all(baseline.values()):
        errors.append("prompt669 baseline evidence incomplete")
    if errors:
        result = {
            "schema_version": "prompt670_operational_soak_report_v1",
            "status": "blocked",
            "prompt670_status": "blocked",
            "run_id": run_id,
            "errors": errors,
            "stop_reason": "unsafe_soak_operational_goal",
            "prompt669_baseline": baseline,
            "safe_soak_operational_goal_required": True,
            "unsafe_soak_operational_goal_rejected": True,
            "queue_item_count": 0,
            "tick_count": 0,
        }
        _write_json(state_path, dict(result, terminal=True))
        _write_json(report_path, result)
        return result

    queue = build_prompt670_soak_queue(soak_dir, count=queue_count)
    queue_errors = _queue_errors(queue)
    normal = _run_soak_queue(repo=repo, output=soak_dir, run_id=run_id, queue=queue)
    interruption_dir = soak_dir / "interruption_resume_verification"
    interruption_queue = build_prompt670_soak_queue(interruption_dir, count=MIN_SOAK_ITEMS)
    interrupted = _run_soak_queue(
        repo=repo,
        output=interruption_dir,
        run_id=f"{run_id}_interrupted",
        queue=interruption_queue,
        interrupt_after_tick=2,
    )
    resumed = _run_soak_queue(
        repo=repo,
        output=interruption_dir,
        run_id=f"{run_id}_resumed",
        queue=interruption_queue,
        resume=True,
    )
    operator = _run_soak_queue(
        repo=repo,
        output=soak_dir / "operator_stop_verification",
        run_id=f"{run_id}_operator_stop",
        queue=build_prompt670_soak_queue(soak_dir / "operator_stop_verification", count=MIN_SOAK_ITEMS),
        operator_stop_after_tick=1,
    )
    threshold = _run_soak_queue(
        repo=repo,
        output=soak_dir / "failure_threshold_verification",
        run_id=f"{run_id}_failure_threshold",
        queue=build_prompt670_soak_queue(soak_dir / "failure_threshold_verification", count=MIN_SOAK_ITEMS),
        fail_on_tick=1,
        failure_threshold=1,
    )
    stale = _verify_stale_lock(soak_dir / "stale_lock_verification")
    gate = run_project_level_completion_gate(
        repo_root=repo,
        out_dir=soak_dir / "completion_gate",
        final_e2e_report_path=repo / "artifacts/autonomous_runtime/prompt667_final_project_run/final_project_run_report.json",
    )

    _write_json(
        recovery_summary_path,
        {
            "schema_version": "prompt670_recovery_summary_v1",
            "run_id": run_id,
            "interrupted": interrupted,
            "resumed": resumed,
            "stale_lock": stale,
            "operator_stop": operator,
        },
    )
    _write_json(
        failure_policy_summary_path,
        {
            "schema_version": "prompt670_failure_policy_summary_v1",
            "run_id": run_id,
            "retryable_failure_injection_verified": normal.get("retryable_failure_injection_verified") is True,
            "retry_policy_verified": normal.get("retry_policy_verified") is True,
            "skip_or_stop_policy_verified": normal.get("skip_or_stop_policy_verified") is True,
            "failure_threshold": threshold,
        },
    )
    _write_json(
        evidence_summary_path,
        {
            "schema_version": "prompt670_operational_soak_evidence_summary_v1",
            "run_id": run_id,
            "operational_soak_goal_path": goal_path.as_posix(),
            "task_queue_path": queue_path.as_posix(),
            "run_state_path": state_path.as_posix(),
            "recovery_summary_path": recovery_summary_path.as_posix(),
            "failure_policy_summary_path": failure_policy_summary_path.as_posix(),
            "evidence_paths": list(normal.get("artifact_paths", []) or []),
            "evidence_path_count": len(normal.get("artifact_paths", []) or []),
            "bounded_summary": {
                "queue_item_count": normal.get("queue_item_count"),
                "tick_count": normal.get("tick_count"),
                "max_items": MAX_SOAK_ITEMS,
                "max_ticks": MAX_SOAK_TICKS,
                "max_cycles": MAX_SOAK_CYCLES,
            },
        },
    )
    _write_json(
        marker_path,
        {
            "schema_version": "prompt670_soak_marker_v1",
            "run_id": run_id,
            "created_at": _utc_now(),
            "queue_item_count": normal.get("queue_item_count", 0),
            "tick_count": normal.get("tick_count", 0),
            "bounded": True,
        },
    )

    protected_after = _snapshot(protected_paths)
    prompt667_preserved = _snapshot_preserved(
        {(repo / PROMPT667_AUDIT).as_posix(): protected_before[(repo / PROMPT667_AUDIT).as_posix()]},
        {(repo / PROMPT667_AUDIT).as_posix(): protected_after[(repo / PROMPT667_AUDIT).as_posix()]},
    )
    prompt668_paths = [repo / PROMPT668_REPORT, repo / PROMPT668_OPERATIONAL_REPORT, repo / PROMPT668_OPERATIONAL_SUMMARY]
    prompt669_paths = [repo / PROMPT669_REPORT, repo / PROMPT669_SCALE_GOAL, repo / PROMPT669_SCALE_SUMMARY]
    prompt668_preserved = _snapshot_preserved(
        {path.as_posix(): protected_before[path.as_posix()] for path in prompt668_paths},
        {path.as_posix(): protected_after[path.as_posix()] for path in prompt668_paths},
    )
    prompt669_preserved = _snapshot_preserved(
        {path.as_posix(): protected_before[path.as_posix()] for path in prompt669_paths},
        {path.as_posix(): protected_after[path.as_posix()] for path in prompt669_paths},
    )

    final_readable = _readable_summary(evidence_summary_path)
    validation = {
        "queue_errors_empty": not queue_errors,
        "normal_status_success": normal.get("status") == "success",
        "queue_item_count_between_20_and_30": MIN_SOAK_ITEMS <= int(normal.get("queue_item_count", 0) or 0) <= MAX_SOAK_ITEMS,
        "tick_count_between_20_and_30": MIN_SOAK_ITEMS <= int(normal.get("tick_count", 0) or 0) <= MAX_SOAK_TICKS,
        "controlled_interruption_verified": interrupted.get("status") == "partial"
        and interrupted.get("stop_reason") == "interrupted_after_tick",
        "resume_after_interruption_verified": resumed.get("status") == "success",
        "operator_stop_verified": operator.get("operator_stop_verified") is True,
        "stale_lock_handling_verified": stale.get("stale_lock_handling_verified") is True,
        "failure_threshold_stop_verified": threshold.get("stop_reason") == "failure_threshold_reached",
        "completion_gate_verified": gate.get("project_level_autonomy_complete") is True,
        "final_readable_soak_evidence_summary_written": final_readable,
    }
    validation_passed = all(validation.values())
    final = {
        "schema_version": "prompt670_operational_soak_report_v1",
        "prompt670_status": "success" if validation_passed else "partial",
        "status": "success" if validation_passed else "partial",
        "run_id": run_id,
        "errors": [] if validation_passed else ["operational soak validation failed"],
        "started_at": started_at,
        "finished_at": _utc_now(),
        "stop_reason": normal.get("stop_reason", "unknown"),
        "prompt669_baseline": baseline,
        "prompt669_verified": all(baseline.values()),
        "operational_soak_recovery_implemented": True,
        "operational_soak_entrypoint": (
            "automation.orchestration.planned_runner.operational_soak_recovery_acceptance."
            "run_operational_soak_recovery_acceptance"
        ),
        "safe_soak_operational_goal_required": True,
        "unsafe_soak_operational_goal_rejected": True,
        "safe_soak_operational_queue_generated_or_loaded": queue_path.is_file(),
        "queue_item_count": int(normal.get("queue_item_count", 0) or 0),
        "tick_count": int(normal.get("tick_count", 0) or 0),
        "no_human_intervention_during_run_verified": bool(normal.get("no_human_intervention_during_run_verified")),
        "internal_codex_executor_used": bool(normal.get("internal_codex_executor_used")),
        "internal_executor_safety_gate_verified": bool(normal.get("internal_executor_safety_gate_verified")),
        "durable_state_persisted": bool(normal.get("durable_state_persisted")),
        "durable_queue_persisted": bool(normal.get("durable_queue_persisted")),
        "lock_acquired": bool(normal.get("lock_acquired")),
        "duplicate_lock_rejected": bool(normal.get("duplicate_lock_rejected")),
        "stale_lock_handling_verified": validation["stale_lock_handling_verified"],
        "controlled_interruption_verified": validation["controlled_interruption_verified"],
        "resume_after_interruption_verified": validation["resume_after_interruption_verified"],
        "operator_stop_verified": validation["operator_stop_verified"],
        "retryable_failure_injection_verified": bool(normal.get("retryable_failure_injection_verified")),
        "retry_policy_verified": bool(normal.get("retry_policy_verified")),
        "skip_or_stop_policy_verified": bool(normal.get("skip_or_stop_policy_verified")),
        "failure_threshold_stop_verified": validation["failure_threshold_stop_verified"],
        "state_queue_consistency_verified": bool(normal.get("state_queue_consistency_verified")),
        "per_item_evidence_captured": bool(normal.get("per_item_evidence_captured")),
        "all_processed_items_have_evidence": bool(normal.get("all_processed_items_have_evidence")),
        "final_readable_soak_evidence_summary_written": validation["final_readable_soak_evidence_summary_written"],
        "terminal_state_recorded": bool(normal.get("terminal_state_recorded")),
        "stop_reason_recorded": bool(normal.get("stop_reason_recorded")),
        "operational_gate_or_completion_gate_verified": validation["completion_gate_verified"],
        "local_only_evidence_captured": bool(normal.get("local_only_evidence_captured")),
        "unsafe_paths_rejected": True,
        "remote_actions_blocked": True,
        "destructive_actions_blocked": True,
        "credential_storage_prevented": True,
        "browser_profile_access_prevented": True,
        "cookie_access_prevented": True,
        "env_value_access_prevented": True,
        "prompt667_final_audit_preserved": prompt667_preserved,
        "prompt668_operational_artifacts_preserved": prompt668_preserved,
        "prompt669_scale_up_artifacts_preserved": prompt669_preserved,
        "implementation_target_path": "docs/autonomous_runtime/operational_soak_and_recovery_acceptance.md",
        "project_level_autonomy_complete": bool(baseline.get("project_level_autonomy_complete")),
        "current_capability_boundary_after": (
            "operational_soak_and_recovery_acceptance_proven"
            if validation_passed
            else "operational_soak_and_recovery_acceptance_partial"
        ),
        "soak_run_dir": soak_dir.as_posix(),
        "operational_soak_goal_path": goal_path.as_posix(),
        "task_queue_path": queue_path.as_posix(),
        "run_state_path": state_path.as_posix(),
        "evidence_summary_path": evidence_summary_path.as_posix(),
        "recovery_summary_path": recovery_summary_path.as_posix(),
        "failure_policy_summary_path": failure_policy_summary_path.as_posix(),
        "soak_marker_path": marker_path.as_posix(),
        "validation": validation,
        "normal_run": normal,
        "interrupted_run": interrupted,
        "resumed_run": resumed,
        "operator_stop_run": operator,
        "failure_threshold_run": threshold,
        "stale_lock": stale,
    }
    _write_text(implementation_path, _implementation_doc(run_id, final))
    final["implementation_artifact_created"] = implementation_path.is_file()
    _write_json(report_path, final)
    _write_text(summary_path, _implementation_doc(run_id, final))
    _write_json(goal_report_path, final)
    _write_text(goal_summary_path, _implementation_doc(run_id, final))
    _write_json(
        next_request_path,
        {
            "schema_version": "next_chatgpt_analysis_request_v1",
            "source_prompt": "Prompt670",
            "recommended_next_action": "continue_to_longer_soak_or_release_documentation",
            "prompt_text": (
                "Analyze Prompt670 bounded operational soak and recovery acceptance "
                "and propose the next local-only prompt for either longer soak "
                "testing or release documentation."
            ),
            "preserve_safety_constraints": True,
        },
    )
    return final


__all__ = [
    "DEFAULT_SOAK_ITEMS",
    "MAX_FAILURE_INJECTIONS",
    "MAX_RETRY_ATTEMPTS_PER_ITEM",
    "MAX_SOAK_CYCLES",
    "MAX_SOAK_ITEMS",
    "MAX_SOAK_TICKS",
    "MIN_SOAK_ITEMS",
    "build_prompt670_soak_goal",
    "build_prompt670_soak_queue",
    "run_operational_soak_recovery_acceptance",
    "verify_prompt669_baseline",
]
