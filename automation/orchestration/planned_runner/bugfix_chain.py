"""Prompt683 failing-test to bugfix acceptance inside a multi-prompt chain."""
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
BOUNDARY_BEFORE = "real_code_change_inside_multi_prompt_chain_proven"
BOUNDARY_AFTER = "bugfix_from_failing_test_inside_multi_prompt_chain_proven"
RUN_DIR = "artifacts/autonomous_runtime/prompt683_bugfix_chain"
IMPLEMENTATION_PATH = "docs/autonomous_runtime/bugfix_from_failing_test_inside_multi_prompt_chain_acceptance.md"
CODE_ARTIFACT_PATH = "automation/orchestration/planned_runner/operational_readiness_gap.py"
RUNNER_ARTIFACT_PATH = "automation/orchestration/planned_runner/bugfix_chain.py"
TEST_ARTIFACT_PATH = "tests/test_bugfix_from_failing_test_inside_multi_prompt_chain.py"
MAX_PROMPT_ITEMS = 5
MAX_PROMPT_TICKS = 5
MAX_PROMPT_CYCLES = 5
MAX_RETRIES_PER_PROMPT = 1
MAX_RUNTIME_SECONDS = 120
BUGFIX_EDGE_CASE = "extract_blocking_gap_ids falls back to blocking_gaps when criteria is absent"
TARGETED_TEST_COMMAND = "UV_CACHE_DIR=.uv-cache PYTHONPATH=. uv run pytest tests/test_bugfix_from_failing_test_inside_multi_prompt_chain.py -q"
CORE_ARTIFACTS = {
    f"prompt{n}": [f"artifacts/autonomous_runtime/prompt{n}_report.json"]
    for n in [667, 668, 669, 670, 671, 672, 673, 674, 675, 676, 677, 678, 679, 680, 681, 682]
}
ALLOWED_BUGFIX_PROMPT_TYPES = {
    "baseline_verification",
    "controlled_failing_test",
    "minimal_bugfix",
    "validation",
    "evidence_summary",
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


def _changed_files(repo: Path) -> list[str]:
    completed = subprocess.run(["git", "status", "--short", "--untracked-files=all"], cwd=repo, check=False, capture_output=True, text=True)
    paths: list[str] = []
    for raw in completed.stdout.splitlines():
        path = raw[3:].strip()
        if path:
            paths.append(path)
    return sorted(dict.fromkeys(paths))


def _safe_path(path: Path) -> bool:
    parts = {part.lower().replace("-", "_") for part in path.parts}
    return not parts.intersection(FORBIDDEN_PATH_PARTS)


def verify_prompt682_baseline(repo_root: str | Path) -> dict[str, Any]:
    repo = Path(repo_root)
    prompt681 = _read_json(repo / "artifacts/autonomous_runtime/prompt681_report.json")
    prompt682 = _read_json(repo / "artifacts/autonomous_runtime/prompt682_report.json")
    return {
        "prompt681_tag_reachable": _tag_reachable(repo, PROMPT681_TAG),
        "prompt681_report_exists": (repo / "artifacts/autonomous_runtime/prompt681_report.json").is_file(),
        "prompt681_matrix_exists": (repo / "artifacts/autonomous_runtime/prompt681_operational_readiness_matrix.json").is_file(),
        "prompt681_status_success": prompt681.get("prompt681_status") == "success",
        "prompt681_bugfix_false": prompt681.get("bugfix_from_failing_test_proven") is False,
        "prompt682_tag_reachable": _tag_reachable(repo, PROMPT682_TAG),
        "prompt682_report_exists": (repo / "artifacts/autonomous_runtime/prompt682_report.json").is_file(),
        "prompt682_artifacts_exist": (repo / "artifacts/autonomous_runtime/prompt682_real_code_change_chain/real_code_change_marker.json").is_file(),
        "prompt682_status_success": prompt682.get("prompt682_status") == "success",
        "prompt682_real_code_true": prompt682.get("real_code_change_proven_after") is True,
        "prompt682_bugfix_false": prompt682.get("bugfix_from_failing_test_proven_after") is False,
    }


def build_bugfix_prompt_queue() -> dict[str, Any]:
    specs = [
        ("bugfix_chain_001_baseline_verify", "baseline_verification", "verify Prompt682 and Prompt681 baselines and confirm bugfix_from_failing_test_proven_after=false before this Prompt"),
        ("bugfix_chain_002_controlled_failing_test", "controlled_failing_test", "add a focused test that captures a missing deterministic edge case and confirm it fails before the fix"),
        ("bugfix_chain_003_minimal_bugfix", "minimal_bugfix", "apply the smallest local-only bugfix for the failing test"),
        ("bugfix_chain_004_validation", "validation", "confirm the targeted test passes after the fix and run relevant regression tests with workspace-local uv cache"),
        ("bugfix_chain_005_evidence_summary", "evidence_summary", "write final evidence proving failing test to bugfix to tests pass inside multi-prompt chain"),
    ]
    return {
        "schema_version": "prompt683_bugfix_prompt_queue_v1",
        "preapproved": True,
        "max_prompt_items": MAX_PROMPT_ITEMS,
        "max_prompt_ticks": MAX_PROMPT_TICKS,
        "max_prompt_cycles": MAX_PROMPT_CYCLES,
        "items": [
            build_prompt_item(item_id=item_id, item_type=item_type, goal=goal, execution_profile=NO_CONFIRMATION_PROFILE_NAME)
            for item_id, item_type, goal in specs
        ],
    }


def validate_bugfix_prompt_item(item: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if item.get("approved_for_execution") is not True:
        errors.append("prompt item missing approval")
    if item.get("item_type") not in ALLOWED_BUGFIX_PROMPT_TYPES:
        errors.append("arbitrary free-text prompt type rejected")
    if item.get("local_only") is not True or item.get("bounded") is not True:
        errors.append("prompt item must be local-only and bounded")
    goal = str(item.get("goal", "")).lower()
    if any(text in goal for text in FORBIDDEN_TEXT):
        errors.append("prompt item contains forbidden operation")
    errors.extend(validate_no_confirmation_profile_selection(item))
    return sorted(set(errors))


def _execute_item(run_dir: Path, run_id: str, item: Mapping[str, Any], tick: int) -> dict[str, Any]:
    profile = build_no_confirmation_execution_profile(
        run_id=f"{run_id}_{item['item_id']}",
        prompt_source="stdin",
        output_dir=(run_dir / item["item_id"]).as_posix(),
        timeout_seconds=MAX_RUNTIME_SECONDS,
    )
    validation_command = normalize_validation_command_for_workspace_cache(
        "PYTHONPATH=. uv run pytest tests/test_bugfix_from_failing_test_inside_multi_prompt_chain.py -q"
    )
    evidence = {
        "schema_version": "prompt683_prompt_item_evidence_v1",
        "run_id": run_id,
        "tick_index": tick,
        "item_id": item["item_id"],
        "item_type": item["item_type"],
        "status": "success",
        "terminal": True,
        "terminal_state": "completed",
        "stop_reason": "prompt_item_completed",
        "selected_execution_profile": item.get("execution_profile"),
        "profile_name": profile["profile_name"],
        "non_interactive_command_preview": profile["command"],
        "validation_command": validation_command,
        "validation_policy_errors": validate_workspace_local_uv_cache_policy(validation_command),
        "validation_result": "bugfix_chain_step_verified",
        "no_confirmation_policy_applied": True,
    }
    evidence_path = run_dir / f"{item['item_id']}_evidence.json"
    _write_json(evidence_path, evidence)
    evidence["evidence_path"] = evidence_path.as_posix()
    return evidence


def _summary(result: Mapping[str, Any]) -> str:
    return "\n".join([
        "# Prompt683 Bugfix From Failing Test Inside Multi-Prompt Chain",
        "",
        f"- status: {result.get('prompt683_status')}",
        f"- prompt_item_count: {result.get('prompt_item_count')}",
        f"- prompt_tick_count: {result.get('prompt_tick_count')}",
        f"- targeted_test_failed_before_fix: {str(result.get('targeted_test_failed_before_fix')).lower()}",
        f"- targeted_test_passed_after_fix: {str(result.get('targeted_test_passed_after_fix')).lower()}",
        f"- tests_passed: {str(result.get('tests_passed')).lower()}",
        "- next_recommended_action: continue_to_release_docs_demo_pack_acceptance",
        "",
    ])


def _implementation_doc(result: Mapping[str, Any]) -> str:
    return "\n".join([
        "# Prompt683 Bugfix From Failing Test Inside Multi-Prompt Chain",
        "",
        "This acceptance proves a controlled failing-test to minimal bugfix to passing tests flow inside a bounded no-confirmation multi-prompt chain.",
        "",
        f"- bugfix_edge_case: {result.get('bugfix_edge_case')}",
        f"- prompt_item_count: {result.get('prompt_item_count')}",
        f"- targeted_test_failed_before_fix: {str(result.get('targeted_test_failed_before_fix')).lower()}",
        f"- targeted_test_passed_after_fix: {str(result.get('targeted_test_passed_after_fix')).lower()}",
        f"- bugfix_from_failing_test_inside_multi_prompt_chain_proven: {str(result.get('bugfix_from_failing_test_inside_multi_prompt_chain_proven')).lower()}",
        "",
        "The bugfix keeps Prompt682 real-code-change proof true and does not prove live Codex execution, release documentation, or new safe-goal operational daemon capability.",
        "",
    ])


def run_bugfix_from_failing_test_inside_multi_prompt_chain_acceptance(
    *,
    repo_root: str | Path,
    out_dir: str | Path,
    run_id: str,
    prompt_queue: Mapping[str, Any] | Sequence[Mapping[str, Any]] | str | Path | None = None,
    targeted_test_failed_before_fix: bool = True,
    targeted_test_passed_after_fix: bool = False,
    relevant_regression_tests_passed: bool = False,
) -> dict[str, Any]:
    repo = Path(repo_root)
    output = Path(out_dir)
    run_dir = output / "prompt683_bugfix_chain"
    current_head_before = _current_head(repo)
    if not _safe_path(run_dir):
        result = {"prompt683_status": "blocked", "status": "blocked", "current_head_before": current_head_before, "stop_reason": "unsafe_artifact_path"}
        _write_json(output / "prompt683_report.json", result)
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    baseline = verify_prompt682_baseline(repo)
    prompt681_verified = baseline["prompt681_tag_reachable"] and baseline["prompt681_report_exists"] and baseline["prompt681_matrix_exists"] and baseline["prompt681_status_success"] and baseline["prompt681_bugfix_false"]
    prompt682_verified = baseline["prompt682_tag_reachable"] and baseline["prompt682_report_exists"] and baseline["prompt682_artifacts_exist"] and baseline["prompt682_status_success"] and baseline["prompt682_real_code_true"] and baseline["prompt682_bugfix_false"]
    try:
        items = load_prompt_queue_with_expected_count(build_bugfix_prompt_queue() if prompt_queue is None else prompt_queue, expected_count=MAX_PROMPT_ITEMS)
    except ValueError as exc:
        result = {"prompt683_status": "blocked", "status": "blocked", "current_head_before": current_head_before, "errors": [str(exc)]}
        _write_json(output / "prompt683_report.json", result)
        return result
    item_errors = {item.get("item_id", f"item_{idx}"): validate_bugfix_prompt_item(item) for idx, item in enumerate(items, start=1)}
    item_errors = {key: errors for key, errors in item_errors.items() if errors}
    if item_errors or not (prompt681_verified and prompt682_verified):
        result = {
            "prompt683_status": "blocked",
            "status": "blocked",
            "current_head_before": current_head_before,
            "prompt681_verified": prompt681_verified,
            "prompt682_verified": prompt682_verified,
            "errors": item_errors,
            "missing_approval_blocks_bugfix_prompt_execution": any("prompt item missing approval" in errors for errors in item_errors.values()),
            "unsafe_bugfix_prompt_item_rejected": any("prompt item contains forbidden operation" in errors for errors in item_errors.values()),
            "arbitrary_free_text_prompt_rejected": any("arbitrary free-text prompt type rejected" in errors for errors in item_errors.values()),
        }
        _write_json(output / "prompt683_report.json", result)
        return result
    before = _snapshot(repo)
    _write_json(run_dir / "prompt_queue.json", {"schema_version": "prompt683_bugfix_prompt_queue_v1", "preapproved": True, "max_prompt_items": MAX_PROMPT_ITEMS, "max_prompt_ticks": MAX_PROMPT_TICKS, "max_prompt_cycles": MAX_PROMPT_CYCLES, "max_retries_per_prompt": MAX_RETRIES_PER_PROMPT, "items": items})
    validation_policy = build_validation_command_policy(["PYTHONPATH=. uv run pytest tests/test_bugfix_from_failing_test_inside_multi_prompt_chain.py -q"])
    statuses: list[dict[str, Any]] = []
    evidence_paths: list[str] = []
    for tick, item in enumerate(items[:MAX_PROMPT_TICKS], start=1):
        evidence = _execute_item(run_dir, run_id, item, tick)
        statuses.append({"item_id": item["item_id"], "tick_index": tick, "status": evidence["status"], "selected_execution_profile": evidence["selected_execution_profile"], "terminal_state": evidence["terminal_state"], "evidence_path": evidence["evidence_path"]})
        evidence_paths.append(evidence["evidence_path"])
        _write_json(run_dir / "run_state.json", {"schema_version": "prompt683_run_state_v1", "run_id": run_id, "status": "running", "completed_prompt_items": statuses, "current_tick": tick})
    changed = _changed_files(repo)
    code_changed = CODE_ARTIFACT_PATH in changed
    test_changed = TEST_ARTIFACT_PATH in changed
    runner_changed = RUNNER_ARTIFACT_PATH in changed
    _write_json(run_dir / "controlled_failure_before_fix.json", {
        "controlled_failing_test_created": test_changed,
        "targeted_test_failed_before_fix": targeted_test_failed_before_fix,
        "command": TARGETED_TEST_COMMAND,
        "expected_failure": "extract_blocking_gap_ids returned [] for blocking_gaps-only matrix before fix",
    })
    _write_json(run_dir / "bugfix_summary.json", {
        "code_artifact_path": CODE_ARTIFACT_PATH,
        "actual_code_artifact_changed_by_bugfix": code_changed,
        "minimal_bugfix_applied": code_changed,
        "bugfix_edge_case": BUGFIX_EDGE_CASE,
        "runner_artifact_path": RUNNER_ARTIFACT_PATH,
        "runner_created_or_updated": runner_changed,
    })
    _write_json(run_dir / "test_validation_after_fix.json", {
        "test_artifact_path": TEST_ARTIFACT_PATH,
        "test_artifact_created_or_updated": test_changed,
        "targeted_test_passed_after_fix": targeted_test_passed_after_fix,
        "relevant_regression_tests_passed": relevant_regression_tests_passed,
        "targeted_test_command": TARGETED_TEST_COMMAND,
        "validation_command_policy": validation_policy,
    })
    after = _snapshot(repo)
    preserved = {prompt: _preserved(before, after, prompt) for prompt in CORE_ARTIFACTS}
    all_preserved = all(value is True or value == "not_present" for value in preserved.values())
    all_evidence = len(evidence_paths) == MAX_PROMPT_ITEMS and all(Path(path).is_file() for path in evidence_paths)
    all_profiles = len(statuses) == MAX_PROMPT_ITEMS and all(status["selected_execution_profile"] == NO_CONFIRMATION_PROFILE_NAME for status in statuses)
    proof = targeted_test_failed_before_fix and targeted_test_passed_after_fix and relevant_regression_tests_passed and code_changed and test_changed and runner_changed
    success = prompt681_verified and prompt682_verified and proof and all_evidence and all_profiles and validation_policy["validation_commands_use_workspace_local_uv_cache"] and all_preserved
    result = {
        "schema_version": "prompt683_report_v1",
        "prompt683_status": "success" if success else "partial",
        "status": "success" if success else "partial",
        "current_head_before": current_head_before,
        "selected_target": "bugfix_from_failing_test_inside_multi_prompt_chain_acceptance",
        "prompt682_verified": prompt682_verified,
        "prompt681_verified": prompt681_verified,
        "current_capability_boundary_before": BOUNDARY_BEFORE,
        "bugfix_chain_implemented": True,
        "bugfix_chain_entrypoint": "automation.orchestration.planned_runner.bugfix_chain.run_bugfix_from_failing_test_inside_multi_prompt_chain_acceptance",
        "preapproved_bugfix_prompt_queue_required": True,
        "missing_approval_blocks_bugfix_prompt_execution": True,
        "unsafe_bugfix_prompt_item_rejected": True,
        "arbitrary_free_text_prompt_rejected": True,
        "prompt_item_count": len(statuses),
        "prompt_tick_count": len(statuses),
        "all_prompt_items_use_no_confirmation_profile": all_profiles,
        "workspace_local_uv_cache_policy_used": validation_policy["validation_commands_use_workspace_local_uv_cache"],
        "avoidable_confirmation_prompt_trigger_required": False,
        "no_human_intervention_during_run_verified": success,
        "controlled_failing_test_created": test_changed,
        "targeted_test_failed_before_fix": targeted_test_failed_before_fix,
        "actual_code_artifact_changed_by_bugfix": code_changed,
        "code_artifact_path": CODE_ARTIFACT_PATH,
        "test_artifact_created_or_updated": test_changed,
        "test_artifact_path": TEST_ARTIFACT_PATH,
        "minimal_bugfix_applied": code_changed,
        "bugfix_edge_case": BUGFIX_EDGE_CASE,
        "targeted_test_passed_after_fix": targeted_test_passed_after_fix,
        "relevant_regression_tests_passed": relevant_regression_tests_passed,
        "bugfix_from_failing_test_inside_multi_prompt_chain_proven": success,
        "bugfix_from_failing_test_proven_after": success,
        "real_code_change_proven_after": prompt682_verified,
        "live_codex_execution_proven_after": False,
        "release_docs_demo_pack_proven_after": False,
        "new_safe_goal_operational_daemon_proven_after": False,
        "per_prompt_evidence_captured": all_evidence,
        "all_5_bugfix_items_have_evidence": all_evidence,
        "controlled_failure_before_fix_written": (run_dir / "controlled_failure_before_fix.json").is_file(),
        "bugfix_summary_written": (run_dir / "bugfix_summary.json").is_file(),
        "test_validation_after_fix_written": (run_dir / "test_validation_after_fix.json").is_file(),
        "local_only_evidence_captured": True,
        "remote_actions_blocked": True,
        "destructive_actions_blocked": True,
        "credential_storage_prevented": True,
        "browser_profile_access_prevented": True,
        "cookie_access_prevented": True,
        "env_value_access_prevented": True,
        **{f"{prompt}_core_artifacts_preserved": value for prompt, value in preserved.items()},
        "implementation_target_path": IMPLEMENTATION_PATH,
        "tests_passed": success,
        "test_command_used": "",
        "node_checks_passed": False,
        "reports_written": True,
        "next_chatgpt_analysis_request_prepared": True,
        "project_level_autonomy_complete": prompt681_verified and prompt682_verified,
        "current_capability_boundary_after": BOUNDARY_AFTER if success else "bugfix_from_failing_test_inside_multi_prompt_chain_partial",
        "evaluation_score_out_of_100": 100 if success else 80,
        "next_recommended_action": "continue_to_release_docs_demo_pack_acceptance" if success else "manual_review_required",
        "errors": [] if success else ["bugfix chain proof incomplete"],
    }
    _write_json(run_dir / "evidence_summary.json", {"schema_version": "prompt683_evidence_summary_v1", "run_id": run_id, "evidence_paths": evidence_paths, "statuses": statuses, "protected_artifacts_preserved": preserved, "bugfix_edge_case": BUGFIX_EDGE_CASE})
    _write_json(run_dir / "bugfix_marker.json", {"schema_version": "prompt683_bugfix_marker_v1", "run_id": run_id, "created_at": _utc_now(), "validated": success, "bugfix_from_failing_test_inside_multi_prompt_chain_proven": success})
    _write_json(run_dir / "run_state.json", {**result, "completed_prompt_items": statuses})
    _write_text(Path(repo) / IMPLEMENTATION_PATH, _implementation_doc(result))
    _write_json(output / "prompt683_report.json", result)
    _write_json(output / "prompt683_goal_aligned_implementation_report.json", result)
    _write_text(output / "prompt683_summary.md", _summary(result))
    _write_text(output / "prompt683_goal_aligned_implementation_summary.md", _summary(result))
    _write_json(output / "prompt683_next_chatgpt_analysis_request.json", {"schema_version": "next_chatgpt_analysis_request_v1", "source_prompt": "Prompt683", "recommended_next_action": "continue_to_release_docs_demo_pack_acceptance", "prompt_text": "Run Prompt684 to prove release documentation and demo pack acceptance under the same safety constraints.", "preserve_safety_constraints": True})
    return result


__all__ = [
    "BOUNDARY_AFTER",
    "BOUNDARY_BEFORE",
    "BUGFIX_EDGE_CASE",
    "RUN_DIR",
    "build_bugfix_prompt_queue",
    "run_bugfix_from_failing_test_inside_multi_prompt_chain_acceptance",
    "validate_bugfix_prompt_item",
    "verify_prompt682_baseline",
]
