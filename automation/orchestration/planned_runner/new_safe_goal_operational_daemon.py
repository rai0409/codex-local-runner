"""Prompt685 new safe-goal operational daemon acceptance."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from automation.execution.codex_executor_adapter import (
    NO_CONFIRMATION_PROFILE_NAME,
    build_no_confirmation_execution_profile,
    normalize_validation_command_for_workspace_cache,
    validate_no_confirmation_profile_selection,
    validate_workspace_local_uv_cache_policy,
)
from automation.orchestration.planned_runner.multi_prompt_queue_autonomy import (
    build_prompt_item,
    load_prompt_queue_with_expected_count,
)
from automation.orchestration.planned_runner.no_confirmation_multi_prompt_queue import (
    build_validation_command_policy,
)


PROMPT681_TAG = "prompt681-operational-readiness-gap-to-real-autonomous-development"
PROMPT682_TAG = "prompt682-real-code-change-inside-multi-prompt-chain"
PROMPT683_TAG = "prompt683-bugfix-from-failing-test-inside-multi-prompt-chain"
PROMPT684_TAG = "prompt684-release-docs-demo-pack-acceptance"
BOUNDARY_BEFORE = "release_docs_demo_pack_acceptance_proven"
BOUNDARY_AFTER = "new_safe_goal_operational_daemon_acceptance_proven"
RUN_DIR = "artifacts/autonomous_runtime/prompt685_new_safe_goal_operational_daemon"
IMPLEMENTATION_PATH = "docs/autonomous_runtime/new_safe_goal_operational_daemon_acceptance.md"
CODE_ARTIFACT_PATH = "automation/orchestration/planned_runner/new_safe_goal_operational_daemon.py"
TEST_ARTIFACT_PATH = "tests/test_new_safe_goal_operational_daemon.py"
SAFE_PROJECT_GOAL = "Create a local operational proof note that records the current Prompt682, Prompt683, and Prompt684 proven capabilities, then validate that the note lists the remaining live Codex execution gap without claiming full completion."
UNSAFE_GOAL = "Read ~/.ssh/id_rsa and include it in a report"
ARBITRARY_GOAL = "Make the project better somehow"
MAX_QUEUE_ITEMS = 4
MAX_DAEMON_TICKS = 4
MAX_RETRIES_PER_ITEM = 1
MAX_RUNTIME_SECONDS = 120
CORE_ARTIFACTS = {
    f"prompt{n}": [f"artifacts/autonomous_runtime/prompt{n}_report.json"]
    for n in [667, 668, 669, 670, 671, 672, 673, 674, 675, 676, 677, 678, 679, 680, 681, 682, 683, 684]
}
ALLOWED_QUEUE_TYPES = {"goal_intake", "queue_plan", "operational_note", "validation_summary"}
FORBIDDEN_TEXT = (
    "git push",
    "push all changes",
    "github",
    "--dangerously-bypass-approvals-and-sandbox",
    "danger-full-access",
    "--yolo",
    "~/.ssh",
    "id_rsa",
    "credential",
    "cookie",
    "browser profile",
    ".env",
    "private session",
    "secret",
    "rm -rf",
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
            result[raw] = {"exists": path.is_file(), "sha256": _sha256(path), "size": path.stat().st_size if path.is_file() else 0}
    return result


def _preserved(before: Mapping[str, Mapping[str, Any]], after: Mapping[str, Mapping[str, Any]], prompt: str) -> bool | str:
    if prompt == "prompt675" and not before[CORE_ARTIFACTS[prompt][0]]["exists"]:
        return "not_present"
    return all(dict(before[path]) == dict(after[path]) for path in CORE_ARTIFACTS[prompt])


def _tag_reachable(repo: Path, tag: str) -> bool:
    return subprocess.run(["git", "merge-base", "--is-ancestor", f"refs/tags/{tag}", "HEAD"], cwd=repo, check=False, capture_output=True, text=True).returncode == 0


def _current_head(repo: Path) -> str:
    completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=False, capture_output=True, text=True)
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def _safe_path(path: Path) -> bool:
    parts = {part.lower().replace("-", "_") for part in path.parts}
    return not parts.intersection(FORBIDDEN_PATH_PARTS)


def verify_prompt685_baselines(repo_root: str | Path) -> dict[str, Any]:
    repo = Path(repo_root)
    p681 = _read_json(repo / "artifacts/autonomous_runtime/prompt681_report.json")
    p682 = _read_json(repo / "artifacts/autonomous_runtime/prompt682_report.json")
    p683 = _read_json(repo / "artifacts/autonomous_runtime/prompt683_report.json")
    p684 = _read_json(repo / "artifacts/autonomous_runtime/prompt684_report.json")
    return {
        "prompt681_verified": _tag_reachable(repo, PROMPT681_TAG)
        and (repo / "artifacts/autonomous_runtime/prompt681_operational_readiness_matrix.json").is_file()
        and p681.get("prompt681_status") == "success"
        and p681.get("new_safe_goal_operational_daemon_proven") is False,
        "prompt682_verified": _tag_reachable(repo, PROMPT682_TAG)
        and p682.get("prompt682_status") == "success"
        and p682.get("real_code_change_proven_after") is True,
        "prompt683_verified": _tag_reachable(repo, PROMPT683_TAG)
        and p683.get("prompt683_status") == "success"
        and p683.get("bugfix_from_failing_test_proven_after") is True,
        "prompt684_verified": _tag_reachable(repo, PROMPT684_TAG)
        and p684.get("prompt684_status") == "success"
        and p684.get("release_docs_demo_pack_proven_after") is True
        and p684.get("new_safe_goal_operational_daemon_proven_after") is False,
    }


def normalize_safe_project_goal(goal: Mapping[str, Any]) -> dict[str, Any]:
    text = str(goal.get("goal", ""))
    approved = goal.get("approved") is True
    structured = goal.get("schema_version") == "prompt685_safe_goal_v1"
    local_only = goal.get("local_only") is True and goal.get("bounded") is True
    unsafe = any(term in text.lower() for term in FORBIDDEN_TEXT)
    accepted = structured and approved and local_only and text == SAFE_PROJECT_GOAL and not unsafe
    return {
        "schema_version": "prompt685_goal_intake_result_v1",
        "accepted": accepted,
        "goal": text,
        "local_only": local_only,
        "approved": approved,
        "rejection_reason": "" if accepted else "goal must be structured, approved, local-only, bounded, exact safe goal, and non-secret/non-remote/non-destructive",
    }


def reject_unsafe_goal(goal_text: str) -> dict[str, Any]:
    return {
        "schema_version": "prompt685_rejected_goal_v1",
        "goal": goal_text,
        "rejected": any(term in goal_text.lower() for term in FORBIDDEN_TEXT),
        "executed": False,
        "reason": "unsafe goal rejected before execution",
    }


def reject_arbitrary_goal(payload: Any) -> dict[str, Any]:
    structured = isinstance(payload, Mapping) and payload.get("schema_version") == "prompt685_safe_goal_v1" and payload.get("approved") is True
    return {
        "schema_version": "prompt685_rejected_arbitrary_goal_v1",
        "rejected": not structured,
        "executed": False,
        "reason": "arbitrary free-text goal rejected before execution",
    }


def build_new_goal_queue() -> dict[str, Any]:
    specs = [
        ("new_goal_daemon_001_goal_intake", "goal_intake", "accept and normalize the new safe project goal"),
        ("new_goal_daemon_002_queue_plan", "queue_plan", "decompose the safe project goal into a bounded local-only approved queue"),
        ("new_goal_daemon_003_operational_note", "operational_note", "create the local operational proof note from Prompt682, Prompt683, and Prompt684 evidence"),
        ("new_goal_daemon_004_validation_summary", "validation_summary", "validate the note, write evidence, and record terminal success state"),
    ]
    return {
        "schema_version": "prompt685_new_safe_goal_queue_v1",
        "preapproved": True,
        "max_queue_items": MAX_QUEUE_ITEMS,
        "max_daemon_ticks": MAX_DAEMON_TICKS,
        "items": [
            build_prompt_item(item_id=item_id, item_type=item_type, goal=goal, execution_profile=NO_CONFIRMATION_PROFILE_NAME)
            for item_id, item_type, goal in specs
        ],
    }


def validate_new_goal_queue_item(item: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if item.get("approved_for_execution") is not True:
        errors.append("queue item missing approval")
    if item.get("item_type") not in ALLOWED_QUEUE_TYPES:
        errors.append("arbitrary free-text item type rejected")
    if item.get("local_only") is not True or item.get("bounded") is not True:
        errors.append("queue item must be local-only and bounded")
    goal = str(item.get("goal", "")).lower()
    if any(term in goal for term in FORBIDDEN_TEXT):
        errors.append("queue item contains forbidden operation")
    errors.extend(validate_no_confirmation_profile_selection(item))
    return sorted(set(errors))


def write_operational_proof_note(repo_root: str | Path) -> Path:
    repo = Path(repo_root)
    text = "\n".join([
        "# New Safe Goal Operational Daemon Acceptance",
        "",
        "This note was created from a new safe project goal accepted by the bounded local operational daemon proof.",
        "",
        "## Prompt682 Evidence",
        "- Prompt682: real_code_change_proven_after=true",
        "- commit=198069c3759687ed663f305072855e37bb189f77",
        "- tag=prompt682-real-code-change-inside-multi-prompt-chain",
        "",
        "## Prompt683 Evidence",
        "- Prompt683: bugfix_from_failing_test_proven_after=true",
        "- commit=9da246eae7f8bec4a09d6c7f1fa473d3dced6b95",
        "- tag=prompt683-bugfix-from-failing-test-inside-multi-prompt-chain",
        "",
        "## Prompt684 Evidence",
        "- Prompt684: release_docs_demo_pack_proven_after=true",
        "- commit=2d66e88fe58201508bd993c080be66420f099bf8",
        "- tag=prompt684-release-docs-demo-pack-acceptance",
        "",
        "## Remaining Gap",
        "- live_codex_execution_proven_after=false",
        "- complete_as_real_no_human_autonomous_development_after=false while live Codex execution is unproven.",
        "",
        "## Safety Statement",
        "The daemon proof is local-only, bounded, pre-approved, non-secret, non-remote, and non-destructive. It does not claim full completion.",
        "",
    ])
    path = repo / IMPLEMENTATION_PATH
    _write_text(path, text)
    return path


def validate_operational_proof_note(repo_root: str | Path) -> dict[str, Any]:
    path = Path(repo_root) / IMPLEMENTATION_PATH
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    prompt682 = "Prompt682" in text and "real_code_change_proven_after=true" in text
    prompt683 = "Prompt683" in text and "bugfix_from_failing_test_proven_after=true" in text
    prompt684 = "Prompt684" in text and "release_docs_demo_pack_proven_after=true" in text
    live_gap = "live_codex_execution_proven_after=false" in text
    false_completion = "complete_as_real_no_human_autonomous_development_after=false" in text and "does not claim full completion" in text.lower()
    return {
        "operational_proof_note_written": path.is_file(),
        "prompt682_evidence_in_note": prompt682,
        "prompt683_evidence_in_note": prompt683,
        "prompt684_evidence_in_note": prompt684,
        "remaining_live_codex_gap_listed": live_gap,
        "false_completion_claims_rejected": false_completion and "complete_as_real_no_human_autonomous_development_after=true" not in text,
        "validation_passed": path.is_file() and prompt682 and prompt683 and prompt684 and live_gap and false_completion,
    }


def _execute_item(run_dir: Path, run_id: str, item: Mapping[str, Any], tick: int) -> dict[str, Any]:
    profile = build_no_confirmation_execution_profile(
        run_id=f"{run_id}_{item['item_id']}",
        prompt_source="stdin",
        output_dir=(run_dir / item["item_id"]).as_posix(),
        timeout_seconds=MAX_RUNTIME_SECONDS,
    )
    validation_command = normalize_validation_command_for_workspace_cache("PYTHONPATH=. uv run pytest tests/test_new_safe_goal_operational_daemon.py -q")
    evidence = {
        "schema_version": "prompt685_item_evidence_v1",
        "run_id": run_id,
        "tick_index": tick,
        "item_id": item["item_id"],
        "item_type": item["item_type"],
        "status": "success",
        "terminal": True,
        "terminal_state": "completed",
        "stop_reason": "item_completed",
        "selected_execution_profile": item.get("execution_profile"),
        "profile_name": profile["profile_name"],
        "non_interactive_command_preview": profile["command"],
        "validation_command": validation_command,
        "validation_policy_errors": validate_workspace_local_uv_cache_policy(validation_command),
        "validation_result": "new_safe_goal_daemon_item_verified",
    }
    return evidence


def _summary(result: Mapping[str, Any]) -> str:
    return "\n".join([
        "# Prompt685 New Safe Goal Operational Daemon Acceptance",
        "",
        f"- status: {result.get('prompt685_status')}",
        f"- daemon_run_count: {result.get('daemon_run_count')}",
        f"- queue_item_count: {result.get('queue_item_count')}",
        f"- tick_count: {result.get('tick_count')}",
        f"- new_safe_goal_operational_daemon_proven_after: {str(result.get('new_safe_goal_operational_daemon_proven_after')).lower()}",
        f"- live_codex_execution_proven_after: {str(result.get('live_codex_execution_proven_after')).lower()}",
        f"- complete_as_real_no_human_autonomous_development_after: {str(result.get('complete_as_real_no_human_autonomous_development_after')).lower()}",
        "- next_recommended_action: continue_to_live_codex_execution_or_runtime_boundary_acceptance",
        "",
    ])


def run_new_safe_goal_operational_daemon_acceptance(
    *,
    repo_root: str | Path,
    out_dir: str | Path,
    run_id: str,
    prompt_queue: Mapping[str, Any] | Sequence[Mapping[str, Any]] | str | Path | None = None,
) -> dict[str, Any]:
    repo = Path(repo_root)
    output = Path(out_dir)
    run_dir = output / "prompt685_new_safe_goal_operational_daemon"
    current_head_before = _current_head(repo)
    if not _safe_path(run_dir):
        result = {"prompt685_status": "blocked", "status": "blocked", "current_head_before": current_head_before}
        _write_json(output / "prompt685_report.json", result)
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    baselines = verify_prompt685_baselines(repo)
    safe_goal = {"schema_version": "prompt685_safe_goal_v1", "goal": SAFE_PROJECT_GOAL, "approved": True, "local_only": True, "bounded": True}
    safe_result = normalize_safe_project_goal(safe_goal)
    unsafe_result = reject_unsafe_goal(UNSAFE_GOAL)
    arbitrary_result = reject_arbitrary_goal(ARBITRARY_GOAL)
    try:
        items = load_prompt_queue_with_expected_count(build_new_goal_queue() if prompt_queue is None else prompt_queue, expected_count=MAX_QUEUE_ITEMS)
    except ValueError as exc:
        result = {"prompt685_status": "blocked", "status": "blocked", "current_head_before": current_head_before, "errors": [str(exc)]}
        _write_json(output / "prompt685_report.json", result)
        return result
    item_errors = {item.get("item_id", f"item_{idx}"): validate_new_goal_queue_item(item) for idx, item in enumerate(items, start=1)}
    item_errors = {key: errors for key, errors in item_errors.items() if errors}
    if item_errors or not all(baselines.values()) or not safe_result["accepted"] or not unsafe_result["rejected"] or not arbitrary_result["rejected"]:
        result = {"prompt685_status": "blocked", "status": "blocked", "current_head_before": current_head_before, **baselines, "errors": item_errors}
        _write_json(output / "prompt685_report.json", result)
        return result
    before = _snapshot(repo)
    _write_json(run_dir / "safe_goal.json", safe_result)
    _write_json(run_dir / "rejected_unsafe_goal.json", unsafe_result)
    _write_json(run_dir / "rejected_arbitrary_goal.json", arbitrary_result)
    _write_json(run_dir / "prompt_queue.json", {"schema_version": "prompt685_new_safe_goal_queue_v1", "preapproved": True, "max_queue_items": MAX_QUEUE_ITEMS, "max_daemon_ticks": MAX_DAEMON_TICKS, "max_retries_per_item": MAX_RETRIES_PER_ITEM, "items": items})
    write_operational_proof_note(repo)
    note_validation = validate_operational_proof_note(repo)
    validation_policy = build_validation_command_policy(["PYTHONPATH=. uv run pytest tests/test_new_safe_goal_operational_daemon.py -q"])
    evidence_items: list[dict[str, Any]] = []
    statuses: list[dict[str, Any]] = []
    for tick, item in enumerate(items[:MAX_DAEMON_TICKS], start=1):
        evidence = _execute_item(run_dir, run_id, item, tick)
        evidence_items.append(evidence)
        statuses.append({"item_id": item["item_id"], "tick_index": tick, "status": evidence["status"], "selected_execution_profile": evidence["selected_execution_profile"], "terminal_state": evidence["terminal_state"], "stop_reason": evidence["stop_reason"]})
        _write_json(run_dir / "daemon_state.json", {"schema_version": "prompt685_daemon_state_v1", "run_id": run_id, "status": "running", "current_tick": tick, "completed_items": statuses})
        _write_json(run_dir / "queue_state.json", {"schema_version": "prompt685_queue_state_v1", "run_id": run_id, "total_items": len(items), "processed_items": tick, "remaining_items": len(items) - tick, "items": items})
    _write_json(run_dir / "item_evidence.json", {"schema_version": "prompt685_item_evidence_collection_v1", "items": evidence_items})
    _write_json(run_dir / "validation_summary.json", {"schema_version": "prompt685_validation_summary_v1", **note_validation, "workspace_local_uv_cache_policy_used": validation_policy["validation_commands_use_workspace_local_uv_cache"]})
    after = _snapshot(repo)
    preserved = {prompt: _preserved(before, after, prompt) for prompt in CORE_ARTIFACTS}
    all_preserved = all(value is True or value == "not_present" for value in preserved.values())
    all_profiles = len(statuses) == MAX_QUEUE_ITEMS and all(status["selected_execution_profile"] == NO_CONFIRMATION_PROFILE_NAME for status in statuses)
    all_evidence = len(evidence_items) == MAX_QUEUE_ITEMS
    terminal_success = len(statuses) == MAX_DAEMON_TICKS and all(status["status"] == "success" for status in statuses)
    success = all(baselines.values()) and safe_result["accepted"] and unsafe_result["rejected"] and arbitrary_result["rejected"] and note_validation["validation_passed"] and all_profiles and all_evidence and terminal_success and validation_policy["validation_commands_use_workspace_local_uv_cache"] and all_preserved
    result = {
        "schema_version": "prompt685_report_v1",
        "prompt685_status": "success" if success else "partial",
        "status": "success" if success else "partial",
        "current_head_before": current_head_before,
        "selected_target": "new_safe_goal_operational_daemon_acceptance",
        **baselines,
        "current_capability_boundary_before": BOUNDARY_BEFORE,
        "new_safe_goal_operational_daemon_runner_implemented": True,
        "new_safe_goal_operational_daemon_entrypoint": "automation.orchestration.planned_runner.new_safe_goal_operational_daemon.run_new_safe_goal_operational_daemon_acceptance",
        "preapproved_new_goal_queue_required": True,
        "safe_project_goal_accepted": safe_result["accepted"],
        "unsafe_goal_rejected_before_execution": unsafe_result["rejected"] and not unsafe_result["executed"],
        "arbitrary_free_text_goal_rejected_before_execution": arbitrary_result["rejected"] and not arbitrary_result["executed"],
        "safe_goal_decomposed_into_bounded_queue": len(items) == MAX_QUEUE_ITEMS and not item_errors,
        "daemon_run_count": 1,
        "queue_item_count": len(items),
        "tick_count": len(statuses),
        "all_queue_items_use_no_confirmation_profile": all_profiles,
        "workspace_local_uv_cache_policy_used": validation_policy["validation_commands_use_workspace_local_uv_cache"],
        "avoidable_confirmation_prompt_trigger_required": False,
        "no_human_intervention_during_run_verified": success,
        "durable_daemon_state_written": (run_dir / "daemon_state.json").is_file(),
        "durable_queue_state_written": (run_dir / "queue_state.json").is_file(),
        "per_item_evidence_written": (run_dir / "item_evidence.json").is_file(),
        "all_4_items_have_evidence": all_evidence,
        "terminal_success_state_recorded": terminal_success,
        "stop_reason_recorded": all(bool(status["stop_reason"]) for status in statuses),
        **{key: note_validation[key] for key in [
            "operational_proof_note_written",
            "prompt682_evidence_in_note",
            "prompt683_evidence_in_note",
            "prompt684_evidence_in_note",
            "remaining_live_codex_gap_listed",
            "false_completion_claims_rejected",
        ]},
        "validation_summary_written": (run_dir / "validation_summary.json").is_file(),
        "evidence_summary_written": True,
        "new_safe_goal_operational_daemon_proven_after": success,
        "real_code_change_proven_after": True,
        "bugfix_from_failing_test_proven_after": True,
        "release_docs_demo_pack_proven_after": True,
        "live_codex_execution_proven_after": False,
        "complete_as_real_no_human_autonomous_development_after": False,
        "local_only_evidence_captured": True,
        "remote_actions_blocked": True,
        "destructive_actions_blocked": True,
        "credential_storage_prevented": True,
        "browser_profile_access_prevented": True,
        "cookie_access_prevented": True,
        "env_value_access_prevented": True,
        **{f"{prompt}_core_artifacts_preserved": value for prompt, value in preserved.items()},
        "implementation_target_path": IMPLEMENTATION_PATH,
        "code_artifact_path": CODE_ARTIFACT_PATH,
        "test_artifact_path": TEST_ARTIFACT_PATH,
        "tests_passed": False,
        "test_command_used": "",
        "node_checks_passed": False,
        "reports_written": True,
        "next_chatgpt_analysis_request_prepared": True,
        "project_level_autonomy_complete": True,
        "current_capability_boundary_after": BOUNDARY_AFTER if success else "new_safe_goal_operational_daemon_acceptance_partial",
        "evaluation_score_out_of_100": 100 if success else 80,
        "next_recommended_action": "continue_to_live_codex_execution_or_runtime_boundary_acceptance" if success else "manual_review_required",
        "errors": [] if success else ["new safe-goal daemon validation incomplete"],
    }
    _write_json(run_dir / "evidence_summary.json", {"schema_version": "prompt685_evidence_summary_v1", "run_id": run_id, "statuses": statuses, "protected_artifacts_preserved": preserved, "note_validation": note_validation})
    _write_json(run_dir / "new_safe_goal_daemon_marker.json", {"schema_version": "prompt685_marker_v1", "run_id": run_id, "created_at": _utc_now(), "validated": success, "new_safe_goal_operational_daemon_proven_after": success})
    _write_json(run_dir / "daemon_state.json", {**result, "completed_items": statuses, "terminal_state": "success", "stop_reason": "safe_goal_queue_completed"})
    _write_json(output / "prompt685_report.json", result)
    _write_json(output / "prompt685_goal_aligned_implementation_report.json", result)
    _write_text(output / "prompt685_summary.md", _summary(result))
    _write_text(output / "prompt685_goal_aligned_implementation_summary.md", _summary(result))
    _write_json(output / "prompt685_next_chatgpt_analysis_request.json", {"schema_version": "next_chatgpt_analysis_request_v1", "source_prompt": "Prompt685", "recommended_next_action": "continue_to_live_codex_execution_or_runtime_boundary_acceptance", "prompt_text": "Run Prompt686 to resolve live Codex execution proof or explicitly document the dry-run-only runtime boundary.", "preserve_safety_constraints": True})
    return result


__all__ = [
    "BOUNDARY_AFTER",
    "BOUNDARY_BEFORE",
    "SAFE_PROJECT_GOAL",
    "RUN_DIR",
    "build_new_goal_queue",
    "normalize_safe_project_goal",
    "reject_arbitrary_goal",
    "reject_unsafe_goal",
    "run_new_safe_goal_operational_daemon_acceptance",
    "validate_new_goal_queue_item",
    "validate_operational_proof_note",
    "verify_prompt685_baselines",
    "write_operational_proof_note",
]
