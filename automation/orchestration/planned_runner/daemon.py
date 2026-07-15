from __future__ import annotations

from pathlib import Path
import json
import time
from typing import Any, Callable, Mapping

from automation.orchestration.planned_runner.loop_controller import (
    run_bounded_success_loop,
)


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_daemon_lite_observed_run_state(
    *,
    artifact_dir: str | Path,
    repo_path: str | Path = ".",
    cycle_runner: Callable[[int], Mapping[str, Any]] | None = None,
    max_cycles: int = 1,
    max_seconds: float = 60.0,
    enabled: bool = False,
    explicit_enable_token: str = "",
    required_enable_token: str = "ENABLE_DAEMON_LITE_OBSERVED_RUN",
    allowed_artifact_paths: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    artifact_root = Path(artifact_dir)
    result_path = artifact_root / "daemon_lite_observed_run_result.json"
    stdout_path = artifact_root / "daemon_lite_observed_run_stdout.txt"
    stderr_path = artifact_root / "daemon_lite_observed_run_stderr.txt"
    started = time.monotonic()
    allowed_paths = list(allowed_artifact_paths or [artifact_root.as_posix()])
    loop_result = run_bounded_success_loop(
        cycle_runner=cycle_runner,
        repo_path=repo_path,
        max_cycles=max_cycles,
        max_seconds=max_seconds,
        allowed_artifact_paths=allowed_paths,
        enabled=enabled,
        explicit_enable_token=explicit_enable_token,
        required_enable_token=required_enable_token,
    ).payload
    elapsed = time.monotonic() - started
    payload: dict[str, Any] = {
        "status": loop_result.get("status", "blocked"),
        "next_action": loop_result.get("next_action", "manual_review_required"),
        "blocked_reason": loop_result.get("blocked_reason", "unknown"),
        "runtime_posture": (
            "local_only_observed_daemon_lite"
            if loop_result.get("enabled")
            else "dry_run_disabled"
        ),
        "artifact_paths": [artifact_root.as_posix(), *list(loop_result.get("artifact_paths", []))],
        "enabled": bool(loop_result.get("enabled", False)),
        "explicit_enable_required": True,
        "executed": bool(loop_result.get("executed", False)),
        "command": "daemon_lite_observed_run",
        "argv": [],
        "stdout_path": stdout_path.as_posix(),
        "stderr_path": stderr_path.as_posix(),
        "result_path": result_path.as_posix(),
        "max_cycles": int(loop_result.get("max_cycles", max_cycles)),
        "max_seconds": float(loop_result.get("max_seconds", max_seconds)),
        "cycle_index": int(loop_result.get("cycle_index", 0)),
        "final_status": loop_result.get("final_status", loop_result.get("status", "blocked")),
        "stop_reason": loop_result.get("stop_reason", "unknown"),
        "per_cycle_result_paths": list(loop_result.get("per_cycle_result_paths", [])),
        "elapsed_seconds": elapsed,
    }
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.write_text("", encoding="utf-8")
    stderr_path.write_text(
        ""
        if payload["blocked_reason"] in {"none", "explicit_enable_required"}
        else _normalize_text(payload["blocked_reason"]) + "\n",
        encoding="utf-8",
    )
    _write_json(result_path, payload)
    return payload
