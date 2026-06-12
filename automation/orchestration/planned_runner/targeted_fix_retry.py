from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

from automation.orchestration.planned_runner.fix_prompt_builder import write_fix_prompt
from automation.orchestration.planned_runner.live_codex_gate import run_live_codex_gate

MAX_FIX_ATTEMPTS_CAP = 2
RETRYABLE_FAILURE_CLASSES = {
    "effect_verification_failed",
    "codex_execution_failed",
    "codex_timeout",
    "targeted_fix_required",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _read_digest(state: Mapping[str, Any]) -> dict[str, Any]:
    digest_path = str(state.get("failure_digest_path") or "")
    if not digest_path:
        return {}
    try:
        payload = json.loads(Path(digest_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def run_targeted_fix_retry(
    *,
    generated_prompt_path: str | Path,
    effect_spec_path: str | Path,
    out_dir: str | Path,
    live_codex_enable_token: str = "",
    sandbox_mode: str = "workspace-write",
    timeout_seconds: int = 90,
    max_fix_attempts: int = 1,
    legacy_source_used: bool = True,
) -> dict[str, Any]:
    """Run one effect-verified gate attempt; on retryable failure, build a fix prompt
    from the failure digest and re-run, bounded by max_fix_attempts (hard cap 2).

    Never commits, tags, or touches anything outside the gate's own behavior.
    """
    output_root = Path(out_dir)
    state_path = output_root / "targeted_fix_retry_state.json"
    bounded_fix_attempts = max(0, min(int(max_fix_attempts), MAX_FIX_ATTEMPTS_CAP))
    started_at = _utc_now()

    attempts: list[dict[str, Any]] = []
    fix_prompt_paths: list[str] = []
    codex_invoked_count = 0
    converged = False
    final_failure_class = ""
    stop_reason = "first_attempt_succeeded"

    current_prompt = Path(generated_prompt_path)
    for attempt_index in range(0, bounded_fix_attempts + 1):
        attempt_dir = output_root / f"attempt_{attempt_index}"
        gate_state = run_live_codex_gate(
            generated_prompt_path=current_prompt,
            out_dir=attempt_dir,
            live_codex_enable_token=live_codex_enable_token,
            timeout_seconds=timeout_seconds,
            sandbox_mode=sandbox_mode,
            effect_spec_path=effect_spec_path,
            legacy_source_used=legacy_source_used,
        )
        if gate_state.get("codex_invoked"):
            codex_invoked_count += 1
        attempts.append(
            {
                "attempt_index": attempt_index,
                "is_fix_attempt": attempt_index > 0,
                "prompt_path": Path(current_prompt).as_posix(),
                "status": gate_state.get("status"),
                "stop_reason": gate_state.get("stop_reason"),
                "effect_verification_status": gate_state.get("effect_verification_status"),
                "state_path": (attempt_dir / "live_codex_gate_state.json").as_posix(),
                "failure_digest_path": str(gate_state.get("failure_digest_path") or ""),
            }
        )

        if gate_state.get("status") == "success":
            converged = True
            stop_reason = (
                "first_attempt_succeeded" if attempt_index == 0 else "fix_attempt_succeeded"
            )
            break

        digest = _read_digest(gate_state)
        final_failure_class = str(digest.get("failure_class") or "unknown")
        if final_failure_class not in RETRYABLE_FAILURE_CLASSES:
            stop_reason = f"non_retryable_failure:{final_failure_class}"
            break
        if attempt_index >= bounded_fix_attempts:
            stop_reason = "max_fix_attempts_reached"
            break

        fix_prompt_path = output_root / f"fix_prompt_attempt_{attempt_index + 1}.md"
        builder_result = write_fix_prompt(
            digest_path=attempts[-1]["failure_digest_path"],
            effect_spec_path=effect_spec_path,
            original_prompt_path=generated_prompt_path,
            out_path=fix_prompt_path,
        )
        if builder_result.get("status") != "success":
            stop_reason = "fix_prompt_build_failed"
            break
        fix_prompt_paths.append(fix_prompt_path.as_posix())
        current_prompt = fix_prompt_path

    payload: dict[str, Any] = {
        "status": "success" if converged else "blocked",
        "converged": converged,
        "stop_reason": stop_reason,
        "next_action": "commit_tag_gate" if converged else "manual_review_required",
        "final_failure_class": "" if converged else final_failure_class,
        "max_fix_attempts": bounded_fix_attempts,
        "fix_attempts_used": max(0, len(attempts) - 1),
        "codex_invoked_count": codex_invoked_count,
        "attempts": attempts,
        "fix_prompt_paths": fix_prompt_paths,
        "generated_prompt_path": Path(generated_prompt_path).as_posix(),
        "effect_spec_path": Path(effect_spec_path).as_posix(),
        "sandbox_mode": sandbox_mode,
        "commit_performed": False,
        "tag_performed": False,
        "local_only": True,
        "started_at": started_at,
        "finished_at": _utc_now(),
        "artifact_paths": [state_path.as_posix()],
    }
    _write_json(state_path, payload)
    return payload


__all__ = [
    "MAX_FIX_ATTEMPTS_CAP",
    "RETRYABLE_FAILURE_CLASSES",
    "run_targeted_fix_retry",
]
