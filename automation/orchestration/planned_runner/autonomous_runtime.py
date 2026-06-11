from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

from automation.orchestration.planned_runner.commit_tag import (
    DEFAULT_COMMIT_TAG_ENABLE_TOKEN,
    build_commit_tag_execution_gate,
    execute_bounded_commit_tag,
)
from automation.orchestration.planned_runner.autonomous_cycle import (
    run_autonomous_cycle_metadata,
)
from automation.orchestration.planned_runner.daemon import (
    build_daemon_lite_observed_run_state,
)
from automation.orchestration.planned_runner.loop_controller import (
    dirty_paths_outside_allowed_artifacts,
    run_bounded_success_loop,
)


AUTONOMOUS_RUNTIME_ENABLE_TOKEN = "LOCAL_AUTONOMOUS_RUNTIME_ENABLE"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _as_required_positive_int(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be > 0")
    if isinstance(value, int) and value > 0:
        return value
    text = _normalize_text(value)
    if text.isdigit() and int(text) > 0:
        return int(text)
    raise ValueError(f"{field_name} must be > 0")


def _as_required_positive_float(value: Any, *, field_name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be > 0")
    if isinstance(value, (int, float)) and float(value) > 0:
        return float(value)
    text = _normalize_text(value)
    try:
        parsed = float(text)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be > 0") from exc
    if parsed <= 0:
        raise ValueError(f"{field_name} must be > 0")
    return parsed


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_summary(path: Path, payload: Mapping[str, Any]) -> None:
    lines = [
        "# Autonomous Runtime Summary",
        "",
        f"- status: {payload.get('status', '')}",
        f"- enabled: {payload.get('enabled', False)}",
        f"- final_status: {payload.get('final_status', '')}",
        f"- stop_reason: {payload.get('stop_reason', '')}",
        f"- next_action: {payload.get('next_action', '')}",
        f"- cycle_count: {payload.get('cycle_count', 0)}",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _metadata_cycle_runner(artifact_root: Path):
    def _run(cycle_index: int) -> dict[str, Any]:
        result_path = artifact_root / f"autonomous_runtime_cycle_{cycle_index}.json"
        payload = {
            "status": "running",
            "blocked_reason": "none",
            "progress_marker": f"metadata_cycle_{cycle_index}",
            "next_prompt": "",
            "result_path": result_path.as_posix(),
            "metadata_only": True,
            "codex_invoked": False,
            "commit_performed": False,
            "tag_performed": False,
        }
        _write_json(result_path, payload)
        return payload

    return _run


def _runtime_payload(
    *,
    status: str,
    enabled: bool,
    enable_token_valid: bool,
    max_cycles: int,
    max_seconds: float,
    started_at: str,
    finished_at: str,
    loop_payload: Mapping[str, Any] | None,
    dirty_paths: list[str] | None,
    legacy_source_used: bool,
    migrated_legacy_functions: list[str],
    artifact_paths: list[str],
) -> dict[str, Any]:
    loop = dict(loop_payload or {})
    cycle_count = int(loop.get("cycle_index", 0) or 0)
    final_status = _normalize_text(loop.get("final_status"), default=status)
    stop_reason = _normalize_text(loop.get("stop_reason"), default="explicit_enable_required")
    return {
        "status": status,
        "enabled": enabled,
        "explicit_enable_required": True,
        "enable_token_valid": enable_token_valid,
        "max_cycles": max_cycles,
        "max_seconds": max_seconds,
        "started_at": started_at,
        "finished_at": finished_at,
        "cycle_count": cycle_count,
        "final_status": final_status,
        "stop_reason": stop_reason,
        "next_action": _normalize_text(loop.get("next_action"), default="manual_review_required"),
        "per_cycle_result_paths": list(loop.get("per_cycle_result_paths", [])),
        "dirty_paths_outside_allowed_artifacts": list(dirty_paths or []),
        "legacy_source_used": legacy_source_used,
        "migrated_legacy_functions": list(migrated_legacy_functions),
        "artifact_paths": artifact_paths,
        "metadata_only": True,
        "codex_invoked": False,
        "commit_performed": False,
        "tag_performed": False,
    }


def run_autonomous_runtime(
    *,
    repo_path: str | Path,
    out_dir: str | Path,
    autonomous_loop: bool = False,
    daemon_lite: bool = False,
    max_cycles: Any = None,
    max_seconds: Any = None,
    autonomous_enable_token: str = "",
    commit_tag_on_success: bool = False,
    commit_tag_enable_token: str = "",
    autonomous_runtime_out_dir: str | Path | None = None,
    legacy_source_used: bool = True,
    migrated_legacy_functions: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    if not autonomous_loop and not daemon_lite:
        raise ValueError("autonomous runtime requires --autonomous-loop or --daemon-lite")

    bounded_max_cycles = _as_required_positive_int(max_cycles, field_name="max_cycles")
    bounded_max_seconds = _as_required_positive_float(max_seconds, field_name="max_seconds")
    artifact_root = Path(autonomous_runtime_out_dir or out_dir)
    runtime_state_path = artifact_root / "autonomous_runtime_state.json"
    runtime_summary_path = artifact_root / "autonomous_runtime_summary.md"
    daemon_state_path = artifact_root / "daemon_lite_observed_run_state.json"
    commit_gate_path = artifact_root / "commit_tag_gate_state.json"
    allowed_artifacts = [artifact_root.as_posix()]
    started_at = _utc_now()
    token_valid = _normalize_text(autonomous_enable_token) == AUTONOMOUS_RUNTIME_ENABLE_TOKEN
    migrated = list(migrated_legacy_functions or [])

    loop_payload: Mapping[str, Any]
    if daemon_lite:
        daemon_payload = build_daemon_lite_observed_run_state(
            artifact_dir=artifact_root,
            repo_path=repo_path,
            cycle_runner=_metadata_cycle_runner(artifact_root),
            max_cycles=bounded_max_cycles,
            max_seconds=bounded_max_seconds,
            enabled=token_valid,
            explicit_enable_token=_normalize_text(autonomous_enable_token),
            required_enable_token=AUTONOMOUS_RUNTIME_ENABLE_TOKEN,
            allowed_artifact_paths=allowed_artifacts,
        )
        _write_json(daemon_state_path, daemon_payload)
        loop_payload = daemon_payload
    else:
        loop_payload = run_bounded_success_loop(
            cycle_runner=_metadata_cycle_runner(artifact_root),
            repo_path=repo_path,
            max_cycles=bounded_max_cycles,
            max_seconds=bounded_max_seconds,
            allowed_artifact_paths=allowed_artifacts,
            enabled=token_valid,
            explicit_enable_token=_normalize_text(autonomous_enable_token),
            required_enable_token=AUTONOMOUS_RUNTIME_ENABLE_TOKEN,
        ).payload

    dirty_state = dirty_paths_outside_allowed_artifacts(
        repo_path=repo_path,
        allowed_artifact_paths=allowed_artifacts,
    )
    dirty_paths = list(dirty_state.get("dirty_paths_outside_allowed_artifacts", []))
    status = _normalize_text(loop_payload.get("status"), default="blocked")
    if not token_valid:
        status = "disabled"
    finished_at = _utc_now()

    artifact_paths = [runtime_state_path.as_posix(), runtime_summary_path.as_posix()]
    if daemon_lite:
        artifact_paths.append(daemon_state_path.as_posix())

    runtime_payload = _runtime_payload(
        status=status,
        enabled=token_valid,
        enable_token_valid=token_valid,
        max_cycles=bounded_max_cycles,
        max_seconds=bounded_max_seconds,
        started_at=started_at,
        finished_at=finished_at,
        loop_payload=loop_payload,
        dirty_paths=dirty_paths,
        legacy_source_used=legacy_source_used,
        migrated_legacy_functions=migrated,
        artifact_paths=artifact_paths,
    )

    if commit_tag_on_success:
        commit_enabled = (
            runtime_payload["final_status"] == "success"
            and _normalize_text(commit_tag_enable_token) == DEFAULT_COMMIT_TAG_ENABLE_TOKEN
        )
        if commit_enabled:
            commit_gate = execute_bounded_commit_tag(
                repo_path=repo_path,
                commit_message="prompt611 autonomous runtime metadata",
                tag_name="prompt611-autonomous-runtime",
                changed_files=[],
                artifact_dir=artifact_root,
                enabled=True,
                explicit_enable_token=_normalize_text(commit_tag_enable_token),
                required_enable_token=DEFAULT_COMMIT_TAG_ENABLE_TOKEN,
            )
        else:
            commit_gate = build_commit_tag_execution_gate(
                repo_path=repo_path,
                artifact_dir=artifact_root,
                enabled=False,
                explicit_enable_token=_normalize_text(commit_tag_enable_token),
                required_enable_token=DEFAULT_COMMIT_TAG_ENABLE_TOKEN,
            )
        _write_json(commit_gate_path, commit_gate)
        runtime_payload["commit_tag_gate_state_path"] = commit_gate_path.as_posix()
        runtime_payload["artifact_paths"].append(commit_gate_path.as_posix())

    _write_json(runtime_state_path, runtime_payload)
    _write_summary(runtime_summary_path, runtime_payload)
    return runtime_payload


def run_autonomous_cycle_metadata_from_runtime(**kwargs: Any) -> dict[str, Any]:
    return run_autonomous_cycle_metadata(**kwargs)
