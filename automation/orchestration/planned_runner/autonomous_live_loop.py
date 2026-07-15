from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any, Mapping

from automation.orchestration.planned_runner.autonomous_cycle import (
    AUTONOMOUS_CYCLE_ENABLE_TOKEN,
    run_autonomous_cycle_metadata,
)
from automation.orchestration.planned_runner.live_codex_gate import (
    LIVE_CODEX_GATE_ENABLE_TOKEN,
    run_live_codex_gate,
)
from automation.orchestration.planned_runner.effect_gate import (
    evaluate_strict_effect_gate,
)
from automation.orchestration.planned_runner.failure_digest import build_failure_digest
from automation.orchestration.planned_runner.loop_controller import (
    dirty_paths_outside_allowed_artifacts,
)


AUTONOMOUS_LIVE_LOOP_MIGRATED_LEGACY_FUNCTIONS = [
    "_build_prompt379_generated_prompt_codex_execution_bridge_state",
    "_build_prompt385_success_path_next_cycle_handoff_state",
    "_build_prompt387_success_path_loop_dispatch_bridge_state",
    "_build_prompt389_explicit_bounded_repeated_success_path_loop_execution_state",
    "_build_prompt420_success_only_next_cycle_loop_state",
]


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


def _load_prompt_manifest(path_text: str) -> tuple[list[dict[str, str]], list[str]]:
    try:
        payload = json.loads(Path(path_text).read_text(encoding="utf-8"))
    except OSError:
        return [], [f"prompt manifest unreadable: {path_text}"]
    except json.JSONDecodeError:
        return [], [f"prompt manifest is not valid JSON: {path_text}"]
    cycles = payload.get("cycles") if isinstance(payload, dict) else None
    if not isinstance(cycles, list) or not cycles:
        return [], [f"prompt manifest must contain a non-empty cycles list: {path_text}"]
    entries: list[dict[str, str]] = []
    errors: list[str] = []
    for index, raw in enumerate(cycles, start=1):
        if not isinstance(raw, dict):
            errors.append(f"manifest cycle {index} must be an object")
            continue
        prompt_path = _normalize_text(raw.get("generated_prompt_path"))
        if not prompt_path or not Path(prompt_path).is_file():
            errors.append(f"manifest cycle {index} generated_prompt_path missing or not a file")
        entries.append(
            {
                "generated_prompt_path": prompt_path,
                "repo_path": _normalize_text(raw.get("repo_path")),
                "effect_spec_path": _normalize_text(raw.get("effect_spec_path")),
            }
        )
    return entries, errors


def _write_summary(path: Path, payload: Mapping[str, Any]) -> None:
    lines = [
        "# Autonomous Live Loop Summary",
        "",
        f"- status: {payload.get('status', '')}",
        f"- enabled: {payload.get('enabled', False)}",
        f"- final_status: {payload.get('final_status', '')}",
        f"- stop_reason: {payload.get('stop_reason', '')}",
        f"- next_action: {payload.get('next_action', '')}",
        f"- cycle_count: {payload.get('cycle_count', 0)}",
        f"- codex_invoked_count: {payload.get('codex_invoked_count', 0)}",
        f"- verification_only: {payload.get('verification_only', False)}",
        f"- commit_tag_gate_observed_count: {payload.get('commit_tag_gate_observed_count', 0)}",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _attach_failure_digest(payload: dict[str, Any], out_dir: Path) -> None:
    if payload.get("status") == "success":
        payload["failure_digest_path"] = ""
        return
    digest = build_failure_digest(state=payload, out_dir=out_dir, run_kind="autonomous_live_loop")
    payload["failure_digest_path"] = digest["digest_path"]


def _disabled_payload(
    *,
    status: str,
    stop_reason: str,
    next_action: str,
    state_path: Path,
    summary_path: Path,
    max_cycles: int,
    max_seconds: float,
    started_at: str,
    autonomous_token_valid: bool,
    live_token_valid: bool,
    generated_prompt_path: str,
    legacy_source_used: bool,
    verification_continue: bool = False,
) -> dict[str, Any]:
    return {
        "status": status,
        "enabled": False,
        "explicit_autonomous_enable_required": True,
        "explicit_live_enable_required": True,
        "autonomous_enable_token_valid": autonomous_token_valid,
        "live_codex_enable_token_valid": live_token_valid,
        "max_cycles": max_cycles,
        "max_seconds": max_seconds,
        "generated_prompt_path": generated_prompt_path,
        "generated_prompt_exists": bool(generated_prompt_path and Path(generated_prompt_path).is_file()),
        "cycle_count": 0,
        "final_status": status,
        "stop_reason": stop_reason,
        "next_action": next_action,
        "codex_invoked_count": 0,
        "per_cycle_result_paths": [],
        "per_cycle_state_paths": [],
        "dirty_paths_outside_allowed_artifacts": [],
        "verification_only": bool(verification_continue),
        "verification_continue_after_commit_gate": bool(verification_continue),
        "commit_tag_gate_observed_count": 0,
        "commit_tag_gate_observed_cycles": [],
        "commit_performed": False,
        "tag_performed": False,
        "local_only": True,
        "legacy_source_used": legacy_source_used,
        "migrated_legacy_functions": list(AUTONOMOUS_LIVE_LOOP_MIGRATED_LEGACY_FUNCTIONS),
        "artifact_paths": [state_path.as_posix(), summary_path.as_posix()],
        "started_at": started_at,
        "finished_at": _utc_now(),
    }


def _cycle_stop_state(
    *,
    classification: Mapping[str, Any],
    cycle_index: int,
    max_cycles: int,
    elapsed_seconds: float,
    max_seconds: float,
    previous_failure: str,
    previous_progress: str,
    verification_continue: bool = False,
) -> dict[str, Any]:
    status = _normalize_text(classification.get("status"), default="blocked").lower()
    next_action = _normalize_text(classification.get("next_action"), default="manual_review_required")
    stop_reason = _normalize_text(classification.get("stop_reason"), default="terminal_blocked")
    failure = _normalize_text(
        classification.get("blocked_reason"),
        default=_normalize_text(classification.get("classification"), default=stop_reason),
    )
    progress = _normalize_text(
        classification.get("progress_marker"),
        default=f"{next_action}:{stop_reason}:{status}",
    )

    if next_action == "commit_tag_gate":
        if not verification_continue:
            return {
                "stop": True,
                "final_status": "success",
                "stop_reason": "commit_tag_gate",
                "blocked_reason": "none",
                "next_action": "commit_tag_gate",
                "failure": failure,
                "progress": progress,
            }
        # Verification-only mode: observe the gate without committing/tagging and
        # keep cycling until max_cycles so a true multi-cycle live run can be proven.
        if cycle_index >= max_cycles:
            return {
                "stop": True,
                "final_status": "success",
                "stop_reason": "verification_max_cycles_reached",
                "blocked_reason": "none",
                "next_action": "commit_tag_gate",
                "failure": failure,
                "progress": progress,
            }
        if elapsed_seconds >= max_seconds:
            return {
                "stop": True,
                "final_status": "success",
                "stop_reason": "max_seconds_reached",
                "blocked_reason": "none",
                "next_action": "commit_tag_gate",
                "failure": failure,
                "progress": progress,
            }
        return {
            "stop": False,
            "final_status": "running",
            "stop_reason": "continue",
            "blocked_reason": "none",
            "next_action": "continue_loop",
            "failure": failure,
            "progress": progress,
        }
    if next_action == "targeted_fix_required" or bool(classification.get("targeted_fix_required")):
        return {
            "stop": True,
            "final_status": "blocked",
            "stop_reason": "targeted_fix_required",
            "blocked_reason": "targeted_fix_required",
            "next_action": "targeted_fix_required",
            "failure": failure,
            "progress": progress,
        }
    if stop_reason in {"success_terminal", "terminal_success"} or next_action == "stop_terminal_success":
        return {
            "stop": True,
            "final_status": "success",
            "stop_reason": "terminal_success",
            "blocked_reason": "none",
            "next_action": next_action,
            "failure": failure,
            "progress": progress,
        }
    if stop_reason in {"terminal_blocked", "blocked_terminal"} or next_action == "stop_terminal_blocked":
        return {
            "stop": True,
            "final_status": "blocked",
            "stop_reason": "terminal_blocked",
            "blocked_reason": failure or "terminal_blocked",
            "next_action": next_action,
            "failure": failure,
            "progress": progress,
        }
    if previous_progress and progress == previous_progress:
        return {
            "stop": True,
            "final_status": "blocked",
            "stop_reason": "no_progress",
            "blocked_reason": "no_progress",
            "next_action": "manual_review_required",
            "failure": failure,
            "progress": progress,
        }
    if previous_failure and failure != "none" and failure == previous_failure:
        return {
            "stop": True,
            "final_status": "blocked",
            "stop_reason": "repeated_same_failure",
            "blocked_reason": "repeated_same_failure",
            "next_action": "manual_review_required",
            "failure": failure,
            "progress": progress,
        }
    if cycle_index >= max_cycles:
        return {
            "stop": True,
            "final_status": "blocked",
            "stop_reason": "max_cycles_reached",
            "blocked_reason": "max_cycles_reached",
            "next_action": "manual_review_required",
            "failure": failure,
            "progress": progress,
        }
    if elapsed_seconds >= max_seconds:
        return {
            "stop": True,
            "final_status": "blocked",
            "stop_reason": "max_seconds_reached",
            "blocked_reason": "max_seconds_reached",
            "next_action": "manual_review_required",
            "failure": failure,
            "progress": progress,
        }
    return {
        "stop": False,
        "final_status": "running",
        "stop_reason": "continue",
        "blocked_reason": "none",
        "next_action": "continue_loop",
        "failure": failure,
        "progress": progress,
    }


def run_autonomous_live_loop(
    *,
    repo_path: str | Path,
    out_dir: str | Path,
    generated_prompt_path: str | Path | None,
    max_cycles: Any,
    max_seconds: Any,
    autonomous_enable_token: str = "",
    live_codex_enable_token: str = "",
    live_loop_timeout_seconds: Any = 60,
    legacy_source_used: bool = True,
    verification_continue: bool = False,
    sandbox_mode: str = "default",
    effect_spec_path: str | Path | None = None,
    generated_prompt_manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    bounded_max_cycles = _as_required_positive_int(max_cycles, field_name="max_cycles")
    bounded_max_seconds = _as_required_positive_float(max_seconds, field_name="max_seconds")
    timeout_seconds = _as_required_positive_int(
        live_loop_timeout_seconds,
        field_name="live_loop_timeout_seconds",
    )
    output_root = Path(out_dir)
    state_path = output_root / "autonomous_live_loop_state.json"
    summary_path = output_root / "autonomous_live_loop_summary.md"
    generated_path_text = _normalize_text(generated_prompt_path)
    started_at = _utc_now()
    autonomous_token_valid = _normalize_text(autonomous_enable_token) == AUTONOMOUS_CYCLE_ENABLE_TOKEN
    live_token_valid = _normalize_text(live_codex_enable_token) == LIVE_CODEX_GATE_ENABLE_TOKEN
    sandbox_text = _normalize_text(sandbox_mode, default="default")
    effect_spec_text = _normalize_text(effect_spec_path)
    manifest_text = _normalize_text(generated_prompt_manifest_path)
    manifest_entries: list[dict[str, str]] = []
    manifest_errors: list[str] = []
    if manifest_text:
        manifest_entries, manifest_errors = _load_prompt_manifest(manifest_text)
    loop_option_fields = {
        "sandbox_mode": sandbox_text,
        "effect_spec_path": effect_spec_text,
        "generated_prompt_manifest_path": manifest_text,
        "manifest_cycle_count": len(manifest_entries),
        "manifest_errors": list(manifest_errors),
        "per_cycle_effect_verification_statuses": [],
        "per_cycle_generated_prompt_paths": [],
    }
    # A manifest never extends the loop: cycles are bounded by both max_cycles
    # and the number of manifest entries.
    effective_max_cycles = (
        min(bounded_max_cycles, len(manifest_entries)) if manifest_entries else bounded_max_cycles
    )

    if not autonomous_token_valid:
        payload = _disabled_payload(
            status="disabled",
            stop_reason="missing_autonomous_enable_token",
            next_action="enable_autonomous_runtime",
            state_path=state_path,
            summary_path=summary_path,
            max_cycles=bounded_max_cycles,
            max_seconds=bounded_max_seconds,
            started_at=started_at,
            autonomous_token_valid=autonomous_token_valid,
            live_token_valid=live_token_valid,
            generated_prompt_path=generated_path_text,
            legacy_source_used=legacy_source_used,
            verification_continue=verification_continue,
        )
        payload.update(loop_option_fields)
        _attach_failure_digest(payload, state_path.parent)
        _write_json(state_path, payload)
        _write_summary(summary_path, payload)
        return payload

    if not live_token_valid:
        payload = _disabled_payload(
            status="disabled",
            stop_reason="missing_live_codex_enable_token",
            next_action="enable_live_codex_gate",
            state_path=state_path,
            summary_path=summary_path,
            max_cycles=bounded_max_cycles,
            max_seconds=bounded_max_seconds,
            started_at=started_at,
            autonomous_token_valid=autonomous_token_valid,
            live_token_valid=live_token_valid,
            generated_prompt_path=generated_path_text,
            legacy_source_used=legacy_source_used,
            verification_continue=verification_continue,
        )
        payload.update(loop_option_fields)
        _attach_failure_digest(payload, state_path.parent)
        _write_json(state_path, payload)
        _write_summary(summary_path, payload)
        return payload

    if manifest_text and manifest_errors:
        payload = _disabled_payload(
            status="blocked",
            stop_reason="invalid_prompt_manifest",
            next_action="manual_review_required",
            state_path=state_path,
            summary_path=summary_path,
            max_cycles=bounded_max_cycles,
            max_seconds=bounded_max_seconds,
            started_at=started_at,
            autonomous_token_valid=autonomous_token_valid,
            live_token_valid=live_token_valid,
            generated_prompt_path=generated_path_text,
            legacy_source_used=legacy_source_used,
            verification_continue=verification_continue,
        )
        payload["enabled"] = True
        payload.update(loop_option_fields)
        _attach_failure_digest(payload, state_path.parent)
        _write_json(state_path, payload)
        _write_summary(summary_path, payload)
        return payload

    output_root.mkdir(parents=True, exist_ok=True)
    allowed_artifacts = [output_root.as_posix()]
    dirty_state = dirty_paths_outside_allowed_artifacts(
        repo_path=repo_path,
        allowed_artifact_paths=allowed_artifacts,
    )
    if dirty_state["status"] == "blocked":
        payload = _disabled_payload(
            status="blocked",
            stop_reason="dirty_worktree_outside_allowed_artifacts",
            next_action="manual_review_required",
            state_path=state_path,
            summary_path=summary_path,
            max_cycles=bounded_max_cycles,
            max_seconds=bounded_max_seconds,
            started_at=started_at,
            autonomous_token_valid=autonomous_token_valid,
            live_token_valid=live_token_valid,
            generated_prompt_path=generated_path_text,
            legacy_source_used=legacy_source_used,
            verification_continue=verification_continue,
        )
        payload["enabled"] = True
        payload["dirty_paths_outside_allowed_artifacts"] = list(
            dirty_state.get("dirty_paths_outside_allowed_artifacts", [])
        )
        payload.update(loop_option_fields)
        _attach_failure_digest(payload, state_path.parent)
        _write_json(state_path, payload)
        _write_summary(summary_path, payload)
        return payload

    started_monotonic = time.monotonic()
    per_cycle_result_paths: list[str] = []
    per_cycle_state_paths: list[str] = []
    per_cycle_effect_statuses: list[str] = []
    per_cycle_prompt_paths: list[str] = []
    codex_invoked_count = 0
    commit_tag_gate_observed_cycles: list[int] = []
    previous_failure = ""
    previous_progress = ""
    final_status = "blocked"
    stop_reason = "max_cycles_reached"
    blocked_reason = "max_cycles_reached"
    next_action = "manual_review_required"
    cycle_count = 0

    for cycle_index in range(1, effective_max_cycles + 1):
        elapsed_before = time.monotonic() - started_monotonic
        if elapsed_before >= bounded_max_seconds:
            stop_reason = "max_seconds_reached"
            blocked_reason = "max_seconds_reached"
            break

        dirty_state = dirty_paths_outside_allowed_artifacts(
            repo_path=repo_path,
            allowed_artifact_paths=allowed_artifacts,
        )
        if dirty_state["status"] == "blocked":
            stop_reason = "dirty_worktree_outside_allowed_artifacts"
            blocked_reason = "dirty_worktree_outside_allowed_artifacts"
            break

        if manifest_entries:
            entry = manifest_entries[cycle_index - 1]
            cycle_prompt_text = entry["generated_prompt_path"]
            cycle_effect_spec = entry["effect_spec_path"] or effect_spec_text
        else:
            cycle_prompt_text = generated_path_text
            cycle_effect_spec = effect_spec_text

        cycle_dir = output_root / f"cycle_{cycle_index}"
        live_gate = run_live_codex_gate(
            generated_prompt_path=cycle_prompt_text,
            out_dir=cycle_dir / "live_codex_gate",
            live_codex_enable_token=live_codex_enable_token,
            timeout_seconds=timeout_seconds,
            legacy_source_used=legacy_source_used,
            migrated_legacy_functions=AUTONOMOUS_LIVE_LOOP_MIGRATED_LEGACY_FUNCTIONS,
            sandbox_mode=sandbox_text,
            effect_spec_path=cycle_effect_spec or None,
        )
        if live_gate.get("codex_invoked"):
            codex_invoked_count += 1
        per_cycle_effect_statuses.append(
            _normalize_text(live_gate.get("effect_verification_status"), default="not_run")
        )
        per_cycle_prompt_paths.append(cycle_prompt_text)

        classification = run_autonomous_cycle_metadata(
            generated_prompt_path=cycle_prompt_text,
            codex_result_path=live_gate.get("codex_result_path"),
            previous_cycle_state_path=per_cycle_state_paths[-1] if per_cycle_state_paths else None,
            output_dir=cycle_dir / "classification",
            cycle_index=cycle_index,
            max_cycles=effective_max_cycles,
            max_seconds=bounded_max_seconds,
            autonomous_enable_token=autonomous_enable_token,
            legacy_source_used=legacy_source_used,
            migrated_legacy_functions=AUTONOMOUS_LIVE_LOOP_MIGRATED_LEGACY_FUNCTIONS,
        )
        cycle_count = cycle_index
        if _normalize_text(classification.get("next_action")) == "commit_tag_gate":
            commit_tag_gate_observed_cycles.append(cycle_index)
        result_path = _normalize_text(live_gate.get("codex_result_path"))
        state_artifacts = classification.get("artifact_paths") if isinstance(classification, Mapping) else []
        state_path_text = _normalize_text(state_artifacts[0] if state_artifacts else "")
        if result_path:
            per_cycle_result_paths.append(result_path)
        if state_path_text:
            per_cycle_state_paths.append(state_path_text)

        stop_state = _cycle_stop_state(
            classification=classification,
            cycle_index=cycle_index,
            max_cycles=effective_max_cycles,
            elapsed_seconds=time.monotonic() - started_monotonic,
            max_seconds=bounded_max_seconds,
            previous_failure=previous_failure,
            previous_progress=previous_progress,
            verification_continue=verification_continue,
        )
        final_status = stop_state["final_status"]
        stop_reason = stop_state["stop_reason"]
        blocked_reason = stop_state["blocked_reason"]
        next_action = stop_state["next_action"]
        previous_failure = stop_state["failure"]
        previous_progress = stop_state["progress"]
        if stop_state["stop"]:
            break

    # Prompt638B strict effect-verification success gate (defense in depth):
    # the loop must NEVER end as success if any cycle's effect verification did
    # not strictly pass. effect_expected is true whenever an effect spec was
    # provided (directly or per manifest entry); legacy no-effect-spec runs are
    # unaffected unless a hard failure status appears.
    effect_expected = bool(effect_spec_text) or any(
        bool(entry.get("effect_spec_path")) for entry in manifest_entries
    )
    effect_gate = evaluate_strict_effect_gate(
        per_cycle_effect_statuses, effect_expected=effect_expected
    )
    if not effect_gate["passed"]:
        final_status = "blocked"
        stop_reason = "effect_verification_failed"
        blocked_reason = "effect_verification_failed"
        next_action = "inspect_missing_expected_effects"

    payload = {
        "status": "success" if final_status == "success" else "blocked",
        "enabled": True,
        "explicit_autonomous_enable_required": True,
        "explicit_live_enable_required": True,
        "autonomous_enable_token_valid": True,
        "live_codex_enable_token_valid": True,
        "max_cycles": bounded_max_cycles,
        "max_seconds": bounded_max_seconds,
        "live_loop_timeout_seconds": timeout_seconds,
        "generated_prompt_path": generated_path_text,
        "generated_prompt_exists": bool(generated_path_text and Path(generated_path_text).is_file()),
        "cycle_count": cycle_count,
        "final_status": final_status,
        "stop_reason": stop_reason,
        "blocked_reason": blocked_reason,
        "next_action": next_action,
        "codex_invoked_count": codex_invoked_count,
        "per_cycle_result_paths": per_cycle_result_paths,
        "per_cycle_state_paths": per_cycle_state_paths,
        "dirty_paths_outside_allowed_artifacts": list(
            dirty_state.get("dirty_paths_outside_allowed_artifacts", [])
        ),
        "verification_only": bool(verification_continue),
        "verification_continue_after_commit_gate": bool(verification_continue),
        "commit_tag_gate_observed_count": len(commit_tag_gate_observed_cycles),
        "commit_tag_gate_observed_cycles": list(commit_tag_gate_observed_cycles),
        "sandbox_mode": sandbox_text,
        "effect_spec_path": effect_spec_text,
        "generated_prompt_manifest_path": manifest_text,
        "manifest_cycle_count": len(manifest_entries),
        "manifest_errors": list(manifest_errors),
        "effective_max_cycles": effective_max_cycles,
        "per_cycle_effect_verification_statuses": list(per_cycle_effect_statuses),
        "effect_verification_expected": effect_expected,
        "effect_gate_passed": bool(effect_gate["passed"]),
        "effect_gate_reason": effect_gate["reason"],
        "per_cycle_generated_prompt_paths": list(per_cycle_prompt_paths),
        "commit_performed": False,
        "tag_performed": False,
        "local_only": True,
        "legacy_source_used": bool(legacy_source_used),
        "migrated_legacy_functions": list(AUTONOMOUS_LIVE_LOOP_MIGRATED_LEGACY_FUNCTIONS),
        "artifact_paths": [state_path.as_posix(), summary_path.as_posix()],
        "started_at": started_at,
        "finished_at": _utc_now(),
    }
    _attach_failure_digest(payload, output_root)
    _write_json(state_path, payload)
    _write_summary(summary_path, payload)
    return payload


__all__ = [
    "AUTONOMOUS_LIVE_LOOP_MIGRATED_LEGACY_FUNCTIONS",
    "run_autonomous_live_loop",
]
