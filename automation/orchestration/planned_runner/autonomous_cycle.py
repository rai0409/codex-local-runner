from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping


AUTONOMOUS_CYCLE_ENABLE_TOKEN = "LOCAL_AUTONOMOUS_RUNTIME_ENABLE"
MIGRATED_LEGACY_FUNCTIONS = [
    "_build_prompt379_generated_prompt_codex_execution_bridge_state",
    "_build_local_codex_one_shot_execution_handoff_state",
    "_build_local_codex_one_shot_execution_result_state",
    "_build_prompt385_success_path_next_cycle_handoff_state",
    "_build_prompt420_success_only_next_cycle_loop_state",
    "_build_prompt422_targeted_fix_codex_execution_adapter_state",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _as_positive_int(value: Any, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int) and value > 0:
        return value
    text = _normalize_text(value)
    if text.isdigit() and int(text) > 0:
        return int(text)
    return default


def _as_positive_float(value: Any, *, default: float) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)) and float(value) > 0:
        return float(value)
    text = _normalize_text(value)
    try:
        parsed = float(text)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def _read_json_object(path: Path | None) -> tuple[dict[str, Any], str]:
    if path is None:
        return {}, "unavailable"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}, "invalid_json"
    except OSError:
        return {}, "read_failed"
    if not isinstance(payload, dict):
        return {}, "invalid_payload"
    return payload, "assimilated"


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_summary(path: Path, payload: Mapping[str, Any]) -> None:
    lines = [
        "# Autonomous Cycle Summary",
        "",
        f"- status: {payload.get('status', '')}",
        f"- enabled: {payload.get('enabled', False)}",
        f"- stop_reason: {payload.get('stop_reason', '')}",
        f"- next_action: {payload.get('next_action', '')}",
        f"- codex_invoked: {payload.get('codex_invoked', False)}",
        f"- result_assimilation_status: {payload.get('result_assimilation_status', '')}",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _result_status(payload: Mapping[str, Any], assimilation_status: str) -> str:
    if assimilation_status == "unavailable":
        return "missing"
    if assimilation_status != "assimilated":
        return assimilation_status

    status = _normalize_text(payload.get("status")).lower()
    returncode = payload.get("returncode", payload.get("execution_returncode"))
    classification = _normalize_text(
        payload.get("returncode_classification", payload.get("execution_returncode_classification"))
    ).lower()
    if status in {"success", "succeeded", "completed", "passed", "ok"}:
        return "success"
    if classification == "success":
        return "success"
    if isinstance(returncode, int) and not isinstance(returncode, bool) and returncode == 0:
        return "success"
    if status in {"failed", "failure", "blocked", "timeout", "execution_error", "error"}:
        return "failed"
    if classification in {"failed", "failure", "timeout", "execution_error", "error"}:
        return "failed"
    if isinstance(returncode, int) and not isinstance(returncode, bool) and returncode != 0:
        return "failed"
    return "unknown"


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return _normalize_text(value).lower() in {"1", "true", "yes", "y", "required"}


def _review_decision(
    *,
    codex_result_status: str,
    result_payload: Mapping[str, Any],
    cycle_index: int,
    max_cycles: int,
) -> tuple[str, bool, str, str, str]:
    raw_next_action = _normalize_text(result_payload.get("next_action")).lower()
    raw_review_route = _normalize_text(
        result_payload.get("review_route", result_payload.get("route"))
    ).lower()
    targeted = bool(
        _truthy(result_payload.get("targeted_fix_required"))
        or "targeted_fix" in raw_next_action
        or "targeted_fix" in raw_review_route
    )

    if codex_result_status == "success":
        if targeted:
            return (
                "targeted_fix_required",
                True,
                "targeted_fix_required",
                "targeted_fix_required",
                "targeted_fix_required",
            )
        if raw_next_action in {"continue_next_cycle", "next_cycle_ready"}:
            return ("next_cycle_ready", False, "ready", "continue_next_cycle", "none")
        if raw_next_action in {"stop_terminal_success", "terminal_success"}:
            return ("terminal_success", False, "not_required", "stop_terminal_success", "success_terminal")
        if cycle_index >= max_cycles:
            return ("commit_tag_gate_ready", False, "not_required", "commit_tag_gate", "none")
        return ("commit_tag_gate_ready", False, "ready", "commit_tag_gate", "none")

    if codex_result_status == "failed":
        return (
            "targeted_fix_required",
            True,
            "targeted_fix_required",
            "targeted_fix_required",
            "targeted_fix_required",
        )

    return (
        "manual_review_required",
        False,
        "blocked",
        "stop_terminal_blocked",
        "terminal_blocked",
    )


def build_autonomous_cycle_execution_state(
    *,
    generated_prompt_path: str | Path | None = None,
    codex_result_path: str | Path | None = None,
    previous_cycle_state_path: str | Path | None = None,
    output_dir: str | Path = ".",
    cycle_index: Any = 1,
    max_cycles: Any = 1,
    max_seconds: Any = 30,
    autonomous_enable_token: str = "",
    legacy_source_used: bool = True,
    migrated_legacy_functions: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    output_root = Path(output_dir)
    state_path = output_root / "autonomous_cycle_state.json"
    summary_path = output_root / "autonomous_cycle_summary.md"
    cycle = _as_positive_int(cycle_index, default=1)
    bounded_max_cycles = _as_positive_int(max_cycles, default=1)
    bounded_max_seconds = _as_positive_float(max_seconds, default=30.0)
    token_valid = _normalize_text(autonomous_enable_token) == AUTONOMOUS_CYCLE_ENABLE_TOKEN
    generated_path_text = _normalize_text(generated_prompt_path)
    result_path_text = _normalize_text(codex_result_path)
    previous_path_text = _normalize_text(previous_cycle_state_path)
    generated_path = Path(generated_path_text) if generated_path_text else None
    result_path = Path(result_path_text) if result_path_text else None
    generated_exists = bool(generated_path and generated_path.exists() and generated_path.is_file())
    result_exists = bool(result_path and result_path.exists() and result_path.is_file())
    result_payload, assimilation_status = _read_json_object(result_path) if result_exists else ({}, "unavailable")
    codex_result_status = _result_status(result_payload, assimilation_status)

    status = "blocked"
    stop_reason = "codex_result_missing"
    classification = "codex_result_missing"
    codex_handoff_status = "blocked"
    review_route = "unavailable"
    targeted_fix_required = False
    next_cycle_handoff_status = "blocked"
    next_action = "stop_terminal_blocked"

    if not token_valid:
        status = "disabled"
        stop_reason = "disabled_missing_enable_token"
        classification = "disabled_missing_enable_token"
        codex_result_status = "unavailable"
    elif not generated_exists:
        stop_reason = "missing_generated_prompt"
        classification = "missing_generated_prompt"
        codex_result_status = "unavailable"
    else:
        codex_handoff_status = "ready_for_codex_execution"
        if not result_exists:
            stop_reason = "codex_result_missing"
            classification = "codex_result_missing"
        else:
            review_route, targeted_fix_required, next_cycle_handoff_status, next_action, stop_reason = (
                _review_decision(
                    codex_result_status=codex_result_status,
                    result_payload=result_payload,
                    cycle_index=cycle,
                    max_cycles=bounded_max_cycles,
                )
            )
            classification = (
                "codex_result_success"
                if codex_result_status == "success"
                else "codex_result_failed"
                if codex_result_status == "failed"
                else "terminal_blocked"
            )
            status = "success" if codex_result_status == "success" and not targeted_fix_required else "blocked"

    artifact_paths = [state_path.as_posix(), summary_path.as_posix()]
    payload: dict[str, Any] = {
        "status": status,
        "enabled": token_valid,
        "explicit_enable_required": True,
        "enable_token_valid": token_valid,
        "cycle_index": cycle,
        "max_cycles": bounded_max_cycles,
        "max_seconds": bounded_max_seconds,
        "generated_prompt_path": generated_path_text,
        "generated_prompt_exists": generated_exists,
        "codex_execution_enabled": False,
        "codex_invoked": False,
        "codex_handoff_status": codex_handoff_status,
        "codex_result_path": result_path_text,
        "codex_result_exists": result_exists,
        "codex_result_status": codex_result_status,
        "result_assimilation_status": assimilation_status,
        "review_route": review_route,
        "targeted_fix_required": targeted_fix_required,
        "next_cycle_handoff_status": next_cycle_handoff_status,
        "next_action": next_action,
        "stop_reason": stop_reason,
        "artifact_paths": artifact_paths,
        "legacy_source_used": bool(legacy_source_used),
        "migrated_legacy_functions": list(migrated_legacy_functions or MIGRATED_LEGACY_FUNCTIONS),
        "classification": classification,
        "previous_cycle_state_path": previous_path_text,
        "previous_cycle_state_exists": bool(
            previous_path_text and Path(previous_path_text).exists() and Path(previous_path_text).is_file()
        ),
        "started_at": _utc_now(),
        "finished_at": _utc_now(),
        "local_only": True,
        "metadata_only": True,
        "commit_performed": False,
        "tag_performed": False,
    }
    _write_json(state_path, payload)
    _write_summary(summary_path, payload)
    return payload


def run_autonomous_cycle_metadata(**kwargs: Any) -> dict[str, Any]:
    return build_autonomous_cycle_execution_state(**kwargs)


__all__ = [
    "AUTONOMOUS_CYCLE_ENABLE_TOKEN",
    "MIGRATED_LEGACY_FUNCTIONS",
    "build_autonomous_cycle_execution_state",
    "run_autonomous_cycle_metadata",
]
