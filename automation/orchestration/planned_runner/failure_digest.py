from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping


FAILURE_DIGEST_FILENAME = "failure_digest.json"

_STOP_REASON_CLASSES = {
    "disabled_missing_enable_token": "enable_token_missing",
    "missing_autonomous_enable_token": "enable_token_missing",
    "missing_live_codex_enable_token": "enable_token_missing",
    "missing_generated_prompt": "missing_input",
    "effect_spec_invalid": "invalid_input",
    "invalid_prompt_manifest": "invalid_input",
    "codex_cli_unavailable": "environment_unavailable",
    "codex_timeout": "codex_timeout",
    "codex_failed": "codex_execution_failed",
    "effect_verification_failed": "effect_verification_failed",
    "dirty_worktree_outside_allowed_artifacts": "dirty_worktree",
    "targeted_fix_required": "targeted_fix_required",
    "no_progress": "no_progress",
    "repeated_same_failure": "no_progress",
    "max_cycles_reached": "budget_exhausted",
    "max_seconds_reached": "budget_exhausted",
    "verification_max_cycles_reached": "budget_exhausted",
    "terminal_blocked": "terminal_blocked",
    "codex_result_missing": "missing_codex_result",
    "interrupted": "interrupted",
}

_RETRYABLE_CLASSES = {
    "codex_timeout",
    "codex_execution_failed",
    "effect_verification_failed",
    "targeted_fix_required",
}

_RECOMMENDED_ACTIONS = {
    "enable_token_missing": "provide_explicit_enable_tokens",
    "missing_input": "provide_generated_prompt",
    "invalid_input": "fix_effect_spec_or_manifest",
    "environment_unavailable": "install_or_authenticate_codex_cli",
    "codex_timeout": "build_targeted_fix_prompt",
    "codex_execution_failed": "build_targeted_fix_prompt",
    "effect_verification_failed": "build_targeted_fix_prompt",
    "targeted_fix_required": "build_targeted_fix_prompt",
    "dirty_worktree": "clean_worktree_or_isolate_artifacts",
    "no_progress": "manual_review_required",
    "budget_exhausted": "increase_bounds_or_manual_review",
    "terminal_blocked": "manual_review_required",
    "missing_codex_result": "manual_review_required",
    "interrupted": "resume_or_requeue_task",
    "unknown": "manual_review_required",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def classify_failure(state: Mapping[str, Any]) -> str:
    status = _normalize_text(state.get("status")).lower()
    if status == "success":
        return "none"
    stop_reason = _normalize_text(state.get("stop_reason")).lower()
    if stop_reason in _STOP_REASON_CLASSES:
        return _STOP_REASON_CLASSES[stop_reason]
    blocked_reason = _normalize_text(state.get("blocked_reason")).lower()
    if blocked_reason in _STOP_REASON_CLASSES:
        return _STOP_REASON_CLASSES[blocked_reason]
    return "unknown"


def _collect_evidence_paths(state: Mapping[str, Any]) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    for key in (
        "stdout_path",
        "stderr_path",
        "codex_result_path",
        "autonomous_cycle_state_path",
        "failure_digest_path",
    ):
        text = _normalize_text(state.get(key))
        if text and text not in seen:
            seen.add(text)
            paths.append(text)
    for key in ("artifact_paths", "per_cycle_result_paths", "per_cycle_state_paths"):
        value = state.get(key)
        if isinstance(value, (list, tuple)):
            for item in value:
                text = _normalize_text(item)
                if text and text not in seen:
                    seen.add(text)
                    paths.append(text)
    return paths


def build_failure_digest(
    *,
    state: Mapping[str, Any],
    out_dir: str | Path,
    run_kind: str = "live_codex_gate",
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a structured operator-handoff digest for a failed run and write it to disk."""
    output_root = Path(out_dir)
    digest_path = output_root / FAILURE_DIGEST_FILENAME
    failure_class = classify_failure(state)
    digest: dict[str, Any] = {
        "digest_path": digest_path.as_posix(),
        "run_kind": _normalize_text(run_kind, default="unknown"),
        "failure_class": failure_class,
        "retryable": failure_class in _RETRYABLE_CLASSES,
        "recommended_next_action": _RECOMMENDED_ACTIONS.get(failure_class, "manual_review_required"),
        "status": _normalize_text(state.get("status")),
        "stop_reason": _normalize_text(state.get("stop_reason")),
        "blocked_reason": _normalize_text(state.get("blocked_reason")),
        "next_action": _normalize_text(state.get("next_action")),
        "failed_cycle": int(state.get("cycle_count", 0) or 0),
        "returncode": state.get("returncode"),
        "generated_prompt_path": _normalize_text(state.get("generated_prompt_path")),
        "effect_spec_path": _normalize_text(state.get("effect_spec_path")),
        "effect_verification_status": _normalize_text(
            state.get("effect_verification_status"), default="not_run"
        ),
        "effect_verification_errors": list(state.get("effect_verification_errors", []) or []),
        "dirty_paths_outside_allowed_artifacts": list(
            state.get("dirty_paths_outside_allowed_artifacts", []) or []
        ),
        "evidence_paths": _collect_evidence_paths(state),
        "local_only": True,
        "generated_at": _utc_now(),
    }
    if extra:
        digest.update(dict(extra))
    digest_path.parent.mkdir(parents=True, exist_ok=True)
    digest_path.write_text(
        json.dumps(digest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return digest


__all__ = [
    "FAILURE_DIGEST_FILENAME",
    "build_failure_digest",
    "classify_failure",
]
