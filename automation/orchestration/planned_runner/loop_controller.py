from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import time
from typing import Any, Callable, Mapping


TERMINAL_SUCCESS_STATUSES = frozenset({"success", "completed", "terminal_success"})
TERMINAL_BLOCKED_STATUSES = frozenset({"blocked", "failed", "terminal_blocked"})


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _as_positive_int(value: Any, *, default: int, upper_bound: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return min(max(value, 1), upper_bound)
    text = _normalize_text(value)
    if text.isdigit():
        return min(max(int(text), 1), upper_bound)
    return default


def _as_positive_float(value: Any, *, default: float, upper_bound: float) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return min(max(float(value), 1.0), upper_bound)
    text = _normalize_text(value)
    try:
        parsed = float(text)
    except ValueError:
        return default
    return min(max(parsed, 1.0), upper_bound)


def _normalize_path_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        return []
    paths: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _normalize_text(item).replace("\\", "/").lstrip("./")
        if not text or text in seen:
            continue
        seen.add(text)
        paths.append(text)
    return paths


def _git_status_paths(repo_path: Path) -> tuple[bool, list[str], str]:
    completed = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        reason = _normalize_text(completed.stderr, default="git_status_failed")
        return False, [], reason
    paths: list[str] = []
    for line in completed.stdout.splitlines():
        if not line.strip():
            continue
        path_text = line[3:].strip()
        if " -> " in path_text:
            path_text = path_text.split(" -> ", 1)[1].strip()
        path_text = path_text.replace("\\", "/").lstrip("./")
        if path_text:
            paths.append(path_text)
    return True, sorted(set(paths)), "none"


def dirty_paths_outside_allowed_artifacts(
    *,
    repo_path: str | Path,
    allowed_artifact_paths: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    repo = Path(repo_path)
    allowed_prefixes = tuple(
        path.rstrip("/") + "/"
        for path in _normalize_path_list(allowed_artifact_paths or [])
        if path
    )
    allowed_exact = set(_normalize_path_list(allowed_artifact_paths or []))
    ok, status_paths, failure_reason = _git_status_paths(repo)
    outside = [
        path
        for path in status_paths
        if path not in allowed_exact and not any(path.startswith(prefix) for prefix in allowed_prefixes)
    ]
    return {
        "status": "ready" if ok and not outside else "blocked",
        "next_action": "continue_loop" if ok and not outside else "manual_review_required",
        "blocked_reason": "none" if ok and not outside else (
            "git_status_failed" if not ok else "dirty_worktree_outside_allowed_artifacts"
        ),
        "runtime_posture": "local_only_observation",
        "artifact_paths": _normalize_path_list(allowed_artifact_paths or []),
        "git_status_available": ok,
        "git_status_failure_reason": failure_reason,
        "dirty_paths": status_paths,
        "dirty_paths_outside_allowed_artifacts": outside,
    }


def classify_loop_stop(
    *,
    cycle_index: int,
    max_cycles: int,
    elapsed_seconds: float,
    max_seconds: float,
    latest_result: Mapping[str, Any] | None,
    previous_result: Mapping[str, Any] | None = None,
    next_prompt: str | None = None,
) -> dict[str, Any]:
    latest = dict(latest_result) if isinstance(latest_result, Mapping) else {}
    previous = dict(previous_result) if isinstance(previous_result, Mapping) else {}
    latest_status = _normalize_text(latest.get("status"), default="unknown").lower()
    latest_failure = _normalize_text(
        latest.get("blocked_reason"),
        default=_normalize_text(latest.get("failure_reason"), default="none"),
    )
    previous_failure = _normalize_text(
        previous.get("blocked_reason"),
        default=_normalize_text(previous.get("failure_reason"), default=""),
    )
    progress_marker = _normalize_text(latest.get("progress_marker"))
    previous_progress_marker = _normalize_text(previous.get("progress_marker"))
    next_prompt_text = _normalize_text(next_prompt, default=_normalize_text(latest.get("next_prompt")))

    stop = False
    stop_reason = "continue"
    final_status = "running"
    blocked_reason = "none"
    next_action = "continue_loop"

    if latest_status in TERMINAL_SUCCESS_STATUSES:
        stop = True
        stop_reason = "success_terminal"
        final_status = "success"
        next_action = "success_handoff"
    elif latest_status in TERMINAL_BLOCKED_STATUSES:
        stop = True
        stop_reason = "blocked_terminal"
        final_status = "blocked"
        blocked_reason = latest_failure if latest_failure != "none" else "blocked_terminal"
        next_action = "manual_review_required"
    elif cycle_index >= max_cycles:
        stop = True
        stop_reason = "max_cycles_exhausted"
        final_status = "blocked"
        blocked_reason = "max_cycles_exhausted"
        next_action = "manual_review_required"
    elif elapsed_seconds >= max_seconds:
        stop = True
        stop_reason = "max_seconds_exhausted"
        final_status = "blocked"
        blocked_reason = "max_seconds_exhausted"
        next_action = "manual_review_required"
    elif previous and progress_marker and progress_marker == previous_progress_marker:
        stop = True
        stop_reason = "no_progress"
        final_status = "blocked"
        blocked_reason = "no_progress"
        next_action = "manual_review_required"
    elif previous and latest_failure != "none" and latest_failure == previous_failure:
        stop = True
        stop_reason = "repeated_same_failure"
        final_status = "blocked"
        blocked_reason = "repeated_same_failure"
        next_action = "manual_review_required"
    elif not next_prompt_text:
        stop = True
        stop_reason = "missing_next_prompt"
        final_status = "blocked"
        blocked_reason = "missing_next_prompt"
        next_action = "manual_review_required"

    return {
        "status": final_status,
        "next_action": next_action,
        "blocked_reason": blocked_reason,
        "runtime_posture": "local_only_bounded_loop",
        "artifact_paths": _normalize_path_list(latest.get("artifact_paths")),
        "stop": stop,
        "stop_reason": stop_reason,
        "cycle_index": cycle_index,
        "max_cycles": max_cycles,
        "elapsed_seconds": elapsed_seconds,
        "max_seconds": max_seconds,
    }


@dataclass(frozen=True)
class BoundedLoopResult:
    payload: dict[str, Any]


def run_bounded_success_loop(
    *,
    cycle_runner: Callable[[int], Mapping[str, Any]] | None = None,
    repo_path: str | Path = ".",
    max_cycles: int = 1,
    max_seconds: float = 60.0,
    allowed_artifact_paths: list[str] | tuple[str, ...] | None = None,
    enabled: bool = False,
    explicit_enable_token: str = "",
    required_enable_token: str = "ENABLE_LOCAL_BOUNDED_SUCCESS_LOOP",
) -> BoundedLoopResult:
    bounded_max_cycles = _as_positive_int(max_cycles, default=1, upper_bound=25)
    bounded_max_seconds = _as_positive_float(max_seconds, default=60.0, upper_bound=3600.0)
    artifact_paths = _normalize_path_list(allowed_artifact_paths or [])
    base_payload: dict[str, Any] = {
        "status": "blocked",
        "next_action": "enable_local_bounded_success_loop",
        "blocked_reason": "explicit_enable_required",
        "runtime_posture": "dry_run_disabled",
        "artifact_paths": artifact_paths,
        "enabled": bool(enabled and explicit_enable_token == required_enable_token),
        "explicit_enable_required": True,
        "executed": False,
        "command": None,
        "argv": [],
        "stdout_path": None,
        "stderr_path": None,
        "result_path": None,
        "max_cycles": bounded_max_cycles,
        "max_seconds": bounded_max_seconds,
        "cycle_index": 0,
        "final_status": "blocked",
        "stop_reason": "explicit_enable_required",
        "per_cycle_result_paths": [],
    }
    if not base_payload["enabled"]:
        return BoundedLoopResult(base_payload)
    if cycle_runner is None:
        payload = dict(base_payload)
        payload.update(
            {
                "blocked_reason": "missing_cycle_runner",
                "next_action": "manual_review_required",
                "runtime_posture": "local_only_bounded_loop",
                "stop_reason": "missing_cycle_runner",
            }
        )
        return BoundedLoopResult(payload)

    started = time.monotonic()
    previous_result: Mapping[str, Any] | None = None
    per_cycle_result_paths: list[str] = []
    final_payload = dict(base_payload)
    final_payload.update(
        {
            "status": "running",
            "next_action": "continue_loop",
            "blocked_reason": "none",
            "runtime_posture": "local_only_bounded_loop",
            "executed": True,
            "stop_reason": "continue",
        }
    )
    for cycle_index in range(1, bounded_max_cycles + 1):
        dirty_state = dirty_paths_outside_allowed_artifacts(
            repo_path=repo_path,
            allowed_artifact_paths=artifact_paths,
        )
        if dirty_state["status"] == "blocked":
            final_payload.update(dirty_state)
            final_payload.update(
                {
                    "cycle_index": cycle_index,
                    "final_status": "blocked",
                    "stop_reason": "dirty_worktree_outside_allowed_artifacts",
                    "per_cycle_result_paths": per_cycle_result_paths,
                }
            )
            break
        latest_result = dict(cycle_runner(cycle_index))
        result_path = _normalize_text(latest_result.get("result_path"))
        if result_path:
            per_cycle_result_paths.append(result_path)
        elapsed = time.monotonic() - started
        stop_state = classify_loop_stop(
            cycle_index=cycle_index,
            max_cycles=bounded_max_cycles,
            elapsed_seconds=elapsed,
            max_seconds=bounded_max_seconds,
            latest_result=latest_result,
            previous_result=previous_result,
            next_prompt=_normalize_text(latest_result.get("next_prompt")),
        )
        final_payload.update(stop_state)
        final_payload.update(
            {
                "cycle_index": cycle_index,
                "final_status": stop_state["status"],
                "per_cycle_result_paths": list(per_cycle_result_paths),
            }
        )
        if stop_state["stop"]:
            break
        previous_result = latest_result
    return BoundedLoopResult(final_payload)
