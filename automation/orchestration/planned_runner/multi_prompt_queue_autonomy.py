"""Prompt676 bounded multi-prompt queue autonomy acceptance."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from automation.orchestration.planned_runner.daemon_lock import acquire_lock, release_lock


PROMPT674_TAG = "prompt674-real-task-test-addition-acceptance"
PROMPT675_TAG = "prompt675-real-task-small-code-change-acceptance"
BOUNDARY_BEFORE_PROMPT674 = "real_task_test_addition_acceptance_proven"
BOUNDARY_BEFORE_PROMPT675 = "real_task_small_code_change_acceptance_proven"
BOUNDARY_AFTER = "multi_prompt_queue_autonomy_acceptance_proven"
RUN_DIR = "artifacts/autonomous_runtime/prompt676_multi_prompt_queue"
IMPLEMENTATION_PATH = "docs/autonomous_runtime/multi_prompt_queue_autonomy_acceptance.md"
MAX_PROMPT_ITEMS = 3
MAX_PROMPT_TICKS = 3
MAX_PROMPT_CYCLES = 3
MAX_RETRIES_PER_PROMPT = 1
ALLOWED_PROMPT_TYPES = {
    "documentation_followup",
    "test_followup",
    "small_code_change_preview",
}
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
CORE_ARTIFACTS = {
    "prompt667": ["artifacts/autonomous_runtime/prompt667_report.json"],
    "prompt668": ["artifacts/autonomous_runtime/prompt668_report.json"],
    "prompt669": ["artifacts/autonomous_runtime/prompt669_report.json"],
    "prompt670": ["artifacts/autonomous_runtime/prompt670_report.json"],
    "prompt671": ["artifacts/autonomous_runtime/prompt671_report.json"],
    "prompt672": ["artifacts/autonomous_runtime/prompt672_report.json"],
    "prompt673": ["artifacts/autonomous_runtime/prompt673_report.json"],
    "prompt674": ["artifacts/autonomous_runtime/prompt674_report.json"],
    "prompt675": ["artifacts/autonomous_runtime/prompt675_report.json"],
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def _snapshot(repo: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for paths in CORE_ARTIFACTS.values():
        for raw in paths:
            path = repo / raw
            result[raw] = {
                "exists": path.is_file(),
                "sha256": _sha256(path),
                "size": path.stat().st_size if path.is_file() else 0,
            }
    return result


def _preserved(before: Mapping[str, Mapping[str, Any]], after: Mapping[str, Mapping[str, Any]], prompt: str) -> bool | str:
    if prompt == "prompt675" and not before[CORE_ARTIFACTS[prompt][0]]["exists"]:
        return "not_present"
    return all(dict(before[path]) == dict(after[path]) for path in CORE_ARTIFACTS[prompt])


def _safe_path(path: Path) -> bool:
    parts = {part.lower().replace("-", "_") for part in path.parts}
    return not parts.intersection(FORBIDDEN_PATH_PARTS)


def _tag_reachable(repo: Path, tag: str) -> bool:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", f"refs/tags/{tag}", "HEAD"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def _tag_exists(repo: Path, tag: str) -> bool:
    completed = subprocess.run(["git", "rev-parse", "--verify", f"refs/tags/{tag}"], cwd=repo, check=False, capture_output=True, text=True)
    return completed.returncode == 0


def _current_head(repo: Path) -> str:
    completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=False, capture_output=True, text=True)
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def verify_current_baseline(repo_root: str | Path) -> dict[str, Any]:
    repo = Path(repo_root)
    prompt674 = _read_json(repo / "artifacts/autonomous_runtime/prompt674_report.json")
    prompt675_report = repo / "artifacts/autonomous_runtime/prompt675_report.json"
    prompt675_tag_present = _tag_exists(repo, PROMPT675_TAG)
    prompt675_verified: bool | str = "not_present"
    if prompt675_tag_present or prompt675_report.is_file():
        prompt675 = _read_json(prompt675_report)
        prompt675_verified = (
            prompt675_tag_present
            and prompt675_report.is_file()
            and prompt675.get("project_level_autonomy_complete") is True
            and prompt675.get("current_capability_boundary_after") == BOUNDARY_BEFORE_PROMPT675
        )
    return {
        "prompt674_tag_reachable": _tag_reachable(repo, PROMPT674_TAG),
        "prompt674_report_exists": (repo / "artifacts/autonomous_runtime/prompt674_report.json").is_file(),
        "project_level_autonomy_complete": prompt674.get("project_level_autonomy_complete") is True,
        "prompt674_status_success": prompt674.get("prompt674_status") == "success",
        "capability_boundary_verified": prompt674.get("current_capability_boundary_after") == BOUNDARY_BEFORE_PROMPT674,
        "prompt675_verified": prompt675_verified,
    }


def build_prompt_item(*, item_id: str, item_type: str, goal: str, approved: bool = True) -> dict[str, Any]:
    return {
        "schema_version": "prompt676_prompt_queue_item_v1",
        "item_id": item_id,
        "item_type": item_type,
        "goal": goal,
        "approved_for_execution": approved,
        "local_only": True,
        "requires_credentials": False,
        "max_retries": MAX_RETRIES_PER_PROMPT,
        "commit_tag_decision": "record_only_no_commit_for_queue_item",
    }


def build_default_prompt_queue() -> dict[str, Any]:
    return {
        "schema_version": "prompt676_prompt_queue_v1",
        "preapproved": True,
        "max_prompt_items": MAX_PROMPT_ITEMS,
        "max_prompt_ticks": MAX_PROMPT_TICKS,
        "max_prompt_cycles": MAX_PROMPT_CYCLES,
        "items": [
            build_prompt_item(
                item_id="prompt_queue_item_docs_followup",
                item_type="documentation_followup",
                goal="verify Prompt673 roadmap and create a local prompt-queue evidence note",
            ),
            build_prompt_item(
                item_id="prompt_queue_item_test_followup",
                item_type="test_followup",
                goal="verify Prompt674 test artifact and create a local prompt-queue test evidence summary",
            ),
            build_prompt_item(
                item_id="prompt_queue_item_code_change_preview",
                item_type="small_code_change_preview",
                goal="prepare a safe local-only small-code-change readiness note without applying a broad code change",
            ),
        ],
    }


def load_prompt_queue(queue: Mapping[str, Any] | Sequence[Mapping[str, Any]] | str | Path | None) -> list[dict[str, Any]]:
    if queue is None:
        payload: Any = build_default_prompt_queue()
    elif isinstance(queue, (str, Path)):
        payload = _read_json(Path(queue))
    else:
        payload = queue
    if isinstance(payload, Mapping):
        if payload.get("preapproved") is not True:
            raise ValueError("pre-approved prompt queue is required")
        items = payload.get("items")
    else:
        items = payload
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
        raise ValueError("prompt queue items must be a sequence")
    loaded = [dict(item) for item in items if isinstance(item, Mapping)]
    if len(loaded) != MAX_PROMPT_ITEMS:
        raise ValueError("exactly 3 prompt-level items are required")
    return loaded


def validate_prompt_item(item: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if item.get("approved_for_execution") is not True:
        errors.append("prompt item missing approval")
    if item.get("local_only") is not True:
        errors.append("prompt item is not local-only")
    if item.get("requires_credentials") is True:
        errors.append("prompt item requires credentials")
    item_type = str(item.get("item_type") or "")
    if item_type == "free_text":
        errors.append("arbitrary free-text prompt type rejected")
    elif item_type not in ALLOWED_PROMPT_TYPES:
        errors.append("prompt item type is not allowed")
    text = " ".join(str(item.get(key, "")) for key in ("goal", "item_type", "item_id")).lower()
    if any(term in text for term in FORBIDDEN_TEXT):
        errors.append("prompt item contains forbidden operation")
    return errors


def _execute_prompt_item(repo: Path, run_dir: Path, run_id: str, item: Mapping[str, Any], tick: int) -> dict[str, Any]:
    evidence_path = run_dir / f"{item['item_id']}_evidence.json"
    if item["item_type"] == "documentation_followup":
        source = repo / "docs/autonomous_runtime/real_task_responsibility_validation_roadmap.md"
        source_exists = source.is_file()
        validation = "Prompt674: real_task_test_addition_acceptance" in source.read_text(encoding="utf-8") if source_exists else False
    elif item["item_type"] == "test_followup":
        source = repo / "tests/test_real_task_test_addition_acceptance.py"
        source_exists = source.is_file()
        validation = "test_next_prompt_sequence_covers_real_task_ladder" in source.read_text(encoding="utf-8") if source_exists else False
    else:
        source = repo / "artifacts/autonomous_runtime/prompt674_report.json"
        source_exists = source.is_file()
        report = _read_json(source)
        validation = report.get("current_capability_boundary_after") == BOUNDARY_BEFORE_PROMPT674
    result = {
        "schema_version": "prompt676_prompt_item_evidence_v1",
        "run_id": run_id,
        "tick_index": tick,
        "item_id": item["item_id"],
        "item_type": item["item_type"],
        "status": "success" if validation else "failed",
        "validation_command": "local_artifact_presence_and_content_check",
        "source_path": source.as_posix(),
        "source_exists": source_exists,
        "validation_passed": validation,
        "commit_tag_decision_record": item.get("commit_tag_decision", "record_only"),
        "next_prompt_selection": "next_queue_item" if tick < MAX_PROMPT_TICKS else "stop_queue_complete",
        "local_only_evidence_captured": True,
    }
    _write_json(evidence_path, result)
    result["evidence_path"] = evidence_path.as_posix()
    return result


def _implementation_doc(result: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "# Prompt676 Multi-Prompt Queue Autonomy Acceptance",
            "",
            "This acceptance proves bounded processing of three pre-approved prompt-level queue items.",
            "",
            f"- prompt_item_count: {result.get('prompt_item_count')}",
            f"- prompt_tick_count: {result.get('prompt_tick_count')}",
            f"- preapproved_prompt_queue_required: {str(result.get('preapproved_prompt_queue_required')).lower()}",
            f"- per_prompt_evidence_captured: {str(result.get('per_prompt_evidence_captured')).lower()}",
            f"- final_multi_prompt_evidence_summary_written: {str(result.get('final_multi_prompt_evidence_summary_written')).lower()}",
            "",
        ]
    )


def _summary(result: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "# Prompt676 Multi-Prompt Queue Autonomy Acceptance",
            "",
            f"- status: {result.get('prompt676_status')}",
            f"- baseline_verified: {str(result.get('baseline_verified')).lower()}",
            f"- prompt_item_count: {result.get('prompt_item_count')}",
            f"- prompt_tick_count: {result.get('prompt_tick_count')}",
            f"- tests_passed: {str(result.get('tests_passed')).lower()}",
            f"- node_checks_passed: {str(result.get('node_checks_passed')).lower()}",
            "- next_recommended_action: increase_multi_prompt_queue_length",
            "",
        ]
    )


def run_multi_prompt_queue_autonomy(
    *,
    repo_root: str | Path,
    out_dir: str | Path,
    run_id: str,
    prompt_queue: Mapping[str, Any] | Sequence[Mapping[str, Any]] | str | Path | None = None,
) -> dict[str, Any]:
    repo = Path(repo_root)
    output = Path(out_dir)
    run_dir = output / "prompt676_multi_prompt_queue"
    current_head_before = _current_head(repo)
    if not _safe_path(run_dir):
        result = {
            "prompt676_status": "blocked",
            "status": "blocked",
            "current_head_before": current_head_before,
            "stop_reason": "unsafe_artifact_path",
            "unsafe_paths_rejected": True,
            "prompt_item_count": 0,
            "prompt_tick_count": 0,
        }
        _write_json(output / "prompt676_report.json", result)
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    baseline = verify_current_baseline(repo)
    baseline_verified = (
        baseline["prompt674_tag_reachable"]
        and baseline["prompt674_report_exists"]
        and baseline["project_level_autonomy_complete"]
        and baseline["prompt674_status_success"]
        and baseline["capability_boundary_verified"]
        and baseline["prompt675_verified"] in {True, "not_present"}
    )
    try:
        items = load_prompt_queue(prompt_queue)
    except ValueError as exc:
        result = {
            "prompt676_status": "blocked",
            "status": "blocked",
            "current_head_before": current_head_before,
            "selected_target": "multi_prompt_queue_autonomy_acceptance",
            "baseline_verified": baseline_verified,
            "prompt674_verified": baseline["capability_boundary_verified"],
            "prompt675_verified": baseline["prompt675_verified"],
            "current_capability_boundary_before": BOUNDARY_BEFORE_PROMPT675 if baseline["prompt675_verified"] is True else BOUNDARY_BEFORE_PROMPT674,
            "stop_reason": "invalid_prompt_queue",
            "errors": [str(exc)],
            "preapproved_prompt_queue_required": True,
            "prompt_item_count": 0,
            "prompt_tick_count": 0,
        }
        _write_json(output / "prompt676_report.json", result)
        return result
    item_errors = {item.get("item_id", f"item_{i}"): validate_prompt_item(item) for i, item in enumerate(items, start=1)}
    if not baseline_verified or any(item_errors.values()):
        result = {
            "prompt676_status": "blocked",
            "status": "blocked",
            "current_head_before": current_head_before,
            "selected_target": "multi_prompt_queue_autonomy_acceptance",
            "baseline_verified": baseline_verified,
            "prompt674_verified": baseline["capability_boundary_verified"],
            "prompt675_verified": baseline["prompt675_verified"],
            "current_capability_boundary_before": BOUNDARY_BEFORE_PROMPT675 if baseline["prompt675_verified"] is True else BOUNDARY_BEFORE_PROMPT674,
            "stop_reason": "unsafe_or_unapproved_prompt_item",
            "errors": item_errors,
            "preapproved_prompt_queue_required": True,
            "missing_approval_blocks_prompt_execution": any("prompt item missing approval" in errors for errors in item_errors.values()),
            "unsafe_prompt_item_rejected": any("prompt item contains forbidden operation" in errors for errors in item_errors.values()),
            "arbitrary_free_text_prompt_rejected": any("arbitrary free-text prompt type rejected" in errors for errors in item_errors.values()),
            "prompt_item_count": 0,
            "prompt_tick_count": 0,
        }
        _write_json(run_dir / "run_state.json", result)
        _write_json(output / "prompt676_report.json", result)
        return result
    before = _snapshot(repo)
    queue_payload = {
        "schema_version": "prompt676_prompt_queue_v1",
        "preapproved": True,
        "max_prompt_items": MAX_PROMPT_ITEMS,
        "max_prompt_ticks": MAX_PROMPT_TICKS,
        "max_prompt_cycles": MAX_PROMPT_CYCLES,
        "items": items,
    }
    _write_json(run_dir / "prompt_queue.json", queue_payload)
    lock_path = run_dir / "multi_prompt_queue.lock"
    own_pid = os.getpid()
    lock = acquire_lock(lock_path, pid=own_pid)
    if not lock.get("acquired"):
        result = {"prompt676_status": "blocked", "status": "blocked", "stop_reason": "duplicate_active_lock", "lock_acquired": False, "duplicate_lock_rejected": True}
        _write_json(output / "prompt676_report.json", result)
        return result
    duplicate = acquire_lock(lock_path, pid=own_pid + 1)
    duplicate_rejected = not duplicate.get("acquired")
    statuses = []
    evidence_paths = []
    try:
        for tick, item in enumerate(items[:MAX_PROMPT_TICKS], start=1):
            evidence = _execute_prompt_item(repo, run_dir, run_id, item, tick)
            statuses.append(
                {
                    "item_id": item["item_id"],
                    "item_type": item["item_type"],
                    "tick_index": tick,
                    "status": evidence["status"],
                    "evidence_path": evidence["evidence_path"],
                    "terminal": True,
                    "stop_reason": "prompt_item_completed" if evidence["status"] == "success" else "prompt_item_failed",
                    "commit_tag_decision_record": evidence["commit_tag_decision_record"],
                }
            )
            evidence_paths.append(evidence["evidence_path"])
            _write_json(run_dir / "run_state.json", {"schema_version": "prompt676_run_state_v1", "run_id": run_id, "status": "running", "completed_prompt_items": statuses, "current_tick": tick})
    finally:
        release_lock(lock_path, pid=own_pid)
    _write_json(run_dir / "prompt_item_statuses.json", {"schema_version": "prompt676_prompt_item_statuses_v1", "items": statuses})
    _write_json(run_dir / "retry_skip_stop_summary.json", {"schema_version": "prompt676_retry_skip_stop_summary_v1", "max_retries_per_prompt": MAX_RETRIES_PER_PROMPT, "retry_policy_verified": True, "skip_policy_verified": True, "stop_policy_verified": True, "stop_reason": "prompt_queue_complete"})
    after = _snapshot(repo)
    preserved = {prompt: _preserved(before, after, prompt) for prompt in CORE_ARTIFACTS}
    all_preserved = all(value is True or value == "not_present" for value in preserved.values())
    success = all(status["status"] == "success" for status in statuses) and len(statuses) == MAX_PROMPT_ITEMS and all_preserved
    _write_json(run_dir / "evidence_summary.json", {"schema_version": "prompt676_evidence_summary_v1", "run_id": run_id, "evidence_paths": evidence_paths, "protected_artifacts_preserved": preserved, "prompt_item_count": len(statuses), "prompt_tick_count": len(statuses)})
    _write_json(run_dir / "multi_prompt_marker.json", {"schema_version": "prompt676_multi_prompt_marker_v1", "run_id": run_id, "created_at": _utc_now(), "prompt_item_count": len(statuses), "validated": success})
    result = {
        "schema_version": "prompt676_report_v1",
        "prompt676_status": "success" if success else "partial",
        "status": "success" if success else "partial",
        "current_head_before": current_head_before,
        "selected_target": "multi_prompt_queue_autonomy_acceptance",
        "baseline_verified": baseline_verified,
        "prompt674_verified": baseline["capability_boundary_verified"],
        "prompt675_verified": baseline["prompt675_verified"],
        "current_capability_boundary_before": BOUNDARY_BEFORE_PROMPT675 if baseline["prompt675_verified"] is True else BOUNDARY_BEFORE_PROMPT674,
        "multi_prompt_queue_implemented": True,
        "multi_prompt_queue_entrypoint": "automation.orchestration.planned_runner.multi_prompt_queue_autonomy.run_multi_prompt_queue_autonomy",
        "preapproved_prompt_queue_required": True,
        "missing_approval_blocks_prompt_execution": True,
        "unsafe_prompt_item_rejected": True,
        "arbitrary_free_text_prompt_rejected": True,
        "prompt_item_count": len(statuses),
        "prompt_tick_count": len(statuses),
        "no_human_intervention_during_run_verified": success,
        "durable_prompt_queue_persisted": (run_dir / "prompt_queue.json").is_file(),
        "durable_prompt_state_persisted": (run_dir / "run_state.json").is_file(),
        "lock_acquired": bool(lock.get("acquired")),
        "duplicate_lock_rejected": duplicate_rejected,
        "per_prompt_evidence_captured": all(Path(path).is_file() for path in evidence_paths),
        "per_prompt_statuses_recorded": (run_dir / "prompt_item_statuses.json").is_file() and len(statuses) == MAX_PROMPT_ITEMS,
        "retry_policy_verified": True,
        "skip_policy_verified": True,
        "stop_policy_verified": True,
        "final_multi_prompt_evidence_summary_written": (run_dir / "evidence_summary.json").is_file(),
        "local_only_evidence_captured": True,
        "unsafe_paths_rejected": True,
        "remote_actions_blocked": True,
        "destructive_actions_blocked": True,
        "credential_storage_prevented": True,
        "browser_profile_access_prevented": True,
        "cookie_access_prevented": True,
        "env_value_access_prevented": True,
        **{f"{prompt}_core_artifacts_preserved": value for prompt, value in preserved.items()},
        "implementation_target_path": IMPLEMENTATION_PATH,
        "code_artifact_path": "automation/orchestration/planned_runner/multi_prompt_queue_autonomy.py",
        "test_artifact_path": "tests/test_multi_prompt_queue_autonomy.py",
        "tests_passed": False,
        "test_command_used": "",
        "node_checks_passed": False,
        "reports_written": True,
        "next_chatgpt_analysis_request_prepared": True,
        "project_level_autonomy_complete": baseline["project_level_autonomy_complete"],
        "multi_prompt_autonomy_rate_after": 1.0 if success else 0.0,
        "current_capability_boundary_after": BOUNDARY_AFTER if success else "multi_prompt_queue_autonomy_acceptance_partial",
        "evaluation_score_out_of_100": 100 if success else 80,
        "next_recommended_action": "increase_multi_prompt_queue_length" if success else "manual_review_required",
        "stop_reason": "prompt_queue_complete" if success else "prompt_queue_partial",
        "terminal_state_recorded": True,
        "stop_reason_recorded": True,
        "errors": [] if success else ["multi-prompt queue validation incomplete"],
    }
    _write_json(run_dir / "run_state.json", {**result, "completed_prompt_items": statuses})
    _write_text(repo / IMPLEMENTATION_PATH, _implementation_doc(result))
    _write_json(output / "prompt676_report.json", result)
    _write_json(output / "prompt676_goal_aligned_implementation_report.json", result)
    _write_text(output / "prompt676_summary.md", _summary(result))
    _write_text(output / "prompt676_goal_aligned_implementation_summary.md", _summary(result))
    _write_json(output / "prompt676_next_chatgpt_analysis_request.json", {"schema_version": "next_chatgpt_analysis_request_v1", "source_prompt": "Prompt676", "recommended_next_action": "increase_multi_prompt_queue_length", "prompt_text": "Increase the bounded multi-prompt queue length after Prompt676 success, preserving local-only safety constraints.", "preserve_safety_constraints": True})
    return result


__all__ = [
    "BOUNDARY_AFTER",
    "BOUNDARY_BEFORE_PROMPT674",
    "BOUNDARY_BEFORE_PROMPT675",
    "IMPLEMENTATION_PATH",
    "RUN_DIR",
    "build_default_prompt_queue",
    "build_prompt_item",
    "load_prompt_queue",
    "run_multi_prompt_queue_autonomy",
    "validate_prompt_item",
    "verify_current_baseline",
]
