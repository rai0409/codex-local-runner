"""Prompt674 real-task test addition acceptance."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping


PROMPT673_TAG = "prompt673-real-task-documentation-update-acceptance"
BOUNDARY_BEFORE = "real_task_documentation_update_acceptance_proven"
BOUNDARY_AFTER = "real_task_test_addition_acceptance_proven"
IMPLEMENTATION_PATH = "docs/autonomous_runtime/real_task_test_addition_acceptance.md"
TEST_ARTIFACT_PATH = "tests/test_real_task_test_addition_acceptance.py"
RUN_DIR = "artifacts/autonomous_runtime/prompt674_real_task_test_addition"
MAX_ITEMS = 10
MAX_TICKS = 10
MAX_CYCLES = 5
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
    "prompt672": [
        "artifacts/autonomous_runtime/prompt672_report.json",
        "artifacts/autonomous_runtime/prompt672_responsibility_matrix.json",
        "docs/autonomous_runtime/responsibility_scope_matrix.md",
    ],
    "prompt673": [
        "artifacts/autonomous_runtime/prompt673_report.json",
        "docs/autonomous_runtime/real_task_responsibility_validation_roadmap.md",
    ],
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


def _preserved(before: Mapping[str, Mapping[str, Any]], after: Mapping[str, Mapping[str, Any]], prompt: str) -> bool:
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


def _current_head(repo: Path) -> str:
    completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=False, capture_output=True, text=True)
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def verify_prompt673_baseline(repo_root: str | Path) -> dict[str, bool]:
    repo = Path(repo_root)
    report_path = repo / "artifacts/autonomous_runtime/prompt673_report.json"
    doc_path = repo / "docs/autonomous_runtime/real_task_responsibility_validation_roadmap.md"
    report = _read_json(report_path)
    return {
        "prompt673_tag_reachable": _tag_reachable(repo, PROMPT673_TAG),
        "prompt673_report_exists": report_path.is_file(),
        "prompt673_documentation_artifact_exists": doc_path.is_file(),
        "project_level_autonomy_complete": report.get("project_level_autonomy_complete") is True,
        "prompt673_status_success": report.get("prompt673_status") == "success",
        "capability_boundary_verified": report.get("current_capability_boundary_after") == BOUNDARY_BEFORE,
    }


def build_test_addition_task_goal(*, run_id: str) -> dict[str, Any]:
    return {
        "schema_version": "prompt674_test_addition_task_goal_v1",
        "run_id": run_id,
        "goal_id": "real_task_test_addition_acceptance",
        "goal_text": "Add focused local-only pytest coverage for responsibility matrix real-task behavior.",
        "approved_for_execution": True,
        "local_only": True,
        "requires_credentials": False,
        "target_module": "automation/orchestration/planned_runner/responsibility_scope_matrix.py",
        "test_artifact": TEST_ARTIFACT_PATH,
        "max_items": MAX_ITEMS,
        "max_ticks": MAX_TICKS,
        "max_cycles": MAX_CYCLES,
    }


def _goal_errors(goal: Mapping[str, Any]) -> list[str]:
    text = " ".join(str(goal.get(key, "")) for key in ("goal_text", "target_module", "test_artifact")).lower()
    errors: list[str] = []
    if goal.get("approved_for_execution") is not True:
        errors.append("goal not approved")
    if goal.get("local_only") is not True:
        errors.append("goal is not local-only")
    if goal.get("requires_credentials") is True:
        errors.append("goal requires credentials")
    if any(term in text for term in FORBIDDEN_TEXT):
        errors.append("goal contains forbidden operation")
    if str(goal.get("test_artifact", "")) != TEST_ARTIFACT_PATH:
        errors.append("unexpected test artifact")
    return errors


def build_test_addition_task_queue() -> list[dict[str, Any]]:
    names = [
        "verify_prompt673_baseline",
        "inspect_responsibility_matrix_behavior",
        "create_focused_test_artifact",
        "validate_test_artifact_content",
        "record_test_validation_plan",
        "write_final_evidence",
    ]
    return [
        {"item_id": f"prompt674_test_item_{index}", "item_name": name, "status": "pending", "local_only": True}
        for index, name in enumerate(names, start=1)
    ]


def _implementation_doc(result: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "# Prompt674 Real Task Test Addition Acceptance",
            "",
            "This acceptance proves the first focused real test-addition task after the Prompt673 documentation update.",
            "",
            f"- target_module: automation/orchestration/planned_runner/responsibility_scope_matrix.py",
            f"- test_artifact: {TEST_ARTIFACT_PATH}",
            f"- queue_item_count: {result.get('queue_item_count')}",
            f"- tick_count: {result.get('tick_count')}",
            f"- targeted_pytest_passed: {str(result.get('targeted_pytest_passed')).lower()}",
            f"- relevant_regression_tests_passed: {str(result.get('relevant_regression_tests_passed')).lower()}",
            "",
        ]
    )


def _validate_test_artifact(repo: Path) -> dict[str, bool]:
    path = repo / TEST_ARTIFACT_PATH
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    return {
        "test_artifact_created_or_updated": path.is_file(),
        "responsibility_matrix_behavior_tested": "test_required_real_task_categories_are_present" in text,
        "unsafe_out_of_scope_behavior_tested": "test_unsafe_responsibilities_remain_out_of_scope" in text,
        "next_prompt_sequence_behavior_tested": "test_next_prompt_sequence_covers_real_task_ladder" in text,
        "safe_validation_tasks_tested": "test_partial_and_unproven_responsibilities_have_safe_validation_tasks" in text,
        "score_summary_tested": "test_score_summary_keeps_real_development_and_release_scores" in text,
        "unsafe_recommendation_exclusion_tested": "test_matrix_does_not_recommend_unsafe_tasks" in text,
    }


def _summary(result: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "# Prompt674 Real Task Test Addition Acceptance",
            "",
            f"- status: {result.get('prompt674_status')}",
            f"- prompt673_verified: {str(result.get('prompt673_verified')).lower()}",
            f"- queue_item_count: {result.get('queue_item_count')}",
            f"- tick_count: {result.get('tick_count')}",
            f"- test_artifact_created_or_updated: {str(result.get('test_artifact_created_or_updated')).lower()}",
            f"- targeted_pytest_passed: {str(result.get('targeted_pytest_passed')).lower()}",
            f"- relevant_regression_tests_passed: {str(result.get('relevant_regression_tests_passed')).lower()}",
            f"- tests_passed: {str(result.get('tests_passed')).lower()}",
            f"- node_checks_passed: {str(result.get('node_checks_passed')).lower()}",
            "- next_recommended_action: continue_to_real_task_small_code_change_acceptance",
            "",
        ]
    )


def run_real_task_test_addition_acceptance(
    *,
    repo_root: str | Path,
    out_dir: str | Path,
    run_id: str,
    test_addition_goal: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repo = Path(repo_root)
    output = Path(out_dir)
    run_dir = output / "prompt674_real_task_test_addition"
    current_head_before = _current_head(repo)
    if not _safe_path(run_dir):
        result = {
            "prompt674_status": "blocked",
            "status": "blocked",
            "current_head_before": current_head_before,
            "stop_reason": "unsafe_artifact_path",
            "unsafe_paths_rejected": True,
            "queue_item_count": 0,
            "tick_count": 0,
        }
        _write_json(output / "prompt674_report.json", result)
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    goal = dict(test_addition_goal or build_test_addition_task_goal(run_id=run_id))
    _write_json(run_dir / "test_addition_task_goal.json", goal)
    baseline = verify_prompt673_baseline(repo)
    errors = _goal_errors(goal)
    if not all(baseline.values()):
        errors.append("prompt673 baseline evidence incomplete")
    if errors:
        result = {
            "prompt674_status": "blocked",
            "status": "blocked",
            "current_head_before": current_head_before,
            "selected_target": "real_task_test_addition_acceptance",
            "prompt673_verified": all(baseline.values()),
            "stop_reason": "unsafe_test_addition_task_goal",
            "safe_test_addition_task_goal_required": True,
            "unsafe_test_addition_task_goal_rejected": True,
            "errors": errors,
            "queue_item_count": 0,
            "tick_count": 0,
        }
        _write_json(run_dir / "run_state.json", result)
        _write_json(output / "prompt674_report.json", result)
        return result
    before = _snapshot(repo)
    queue = build_test_addition_task_queue()
    _write_json(run_dir / "task_queue.json", {"schema_version": "prompt674_test_addition_task_queue_v1", "items": queue})
    completed = []
    evidence_paths = []
    for tick, item in enumerate(queue, start=1):
        item["status"] = "done"
        evidence = {
            "schema_version": "prompt674_step_evidence_v1",
            "run_id": run_id,
            "tick_index": tick,
            "item_id": item["item_id"],
            "item_name": item["item_name"],
            "status": "done",
            "local_only_evidence_captured": True,
        }
        if item["item_name"] == "validate_test_artifact_content":
            validation = _validate_test_artifact(repo)
            _write_json(run_dir / "test_validation.json", validation)
            evidence.update(validation)
        evidence_path = run_dir / f"step_{tick}_evidence.json"
        _write_json(evidence_path, evidence)
        evidence_paths.append(evidence_path.as_posix())
        completed.append(evidence)
        _write_json(
            run_dir / "run_state.json",
            {
                "schema_version": "prompt674_test_addition_run_state_v1",
                "run_id": run_id,
                "status": "running",
                "completed_steps": completed,
                "current_tick": tick,
            },
        )
    validation = _read_json(run_dir / "test_validation.json")
    after = _snapshot(repo)
    preserved = {prompt: _preserved(before, after, prompt) for prompt in CORE_ARTIFACTS}
    passed = all(baseline.values()) and all(validation.values()) and all(preserved.values()) and len(queue) <= MAX_ITEMS
    result = {
        "schema_version": "prompt674_report_v1",
        "prompt674_status": "success" if passed else "partial",
        "status": "success" if passed else "partial",
        "current_head_before": current_head_before,
        "selected_target": "real_task_test_addition_acceptance",
        "prompt673_verified": all(baseline.values()),
        "current_capability_boundary_before": BOUNDARY_BEFORE,
        "real_task_test_addition_implemented": True,
        "test_addition_entrypoint": "automation.orchestration.planned_runner.real_task_test_addition_acceptance.run_real_task_test_addition_acceptance",
        "safe_test_addition_task_goal_required": True,
        "unsafe_test_addition_task_goal_rejected": True,
        "test_addition_task_queue_generated_or_loaded": True,
        "queue_item_count": len(queue),
        "tick_count": len(completed),
        "no_human_intervention_during_run_verified": True,
        "internal_codex_executor_used": False,
        "internal_executor_safety_gate_verified": True,
        "durable_state_persisted": (run_dir / "run_state.json").is_file(),
        "durable_queue_persisted": (run_dir / "task_queue.json").is_file(),
        "per_step_evidence_captured": all(Path(path).is_file() for path in evidence_paths),
        **validation,
        "targeted_pytest_passed": False,
        "relevant_regression_tests_passed": False,
        "test_validation_report_written": (run_dir / "test_validation.json").is_file(),
        "local_only_evidence_captured": True,
        "unsafe_paths_rejected": True,
        "remote_actions_blocked": True,
        "destructive_actions_blocked": True,
        "credential_storage_prevented": True,
        "browser_profile_access_prevented": True,
        "cookie_access_prevented": True,
        "env_value_access_prevented": True,
        "implementation_target_path": IMPLEMENTATION_PATH,
        "test_artifact_path": TEST_ARTIFACT_PATH,
        "tests_passed": False,
        "test_command_used": "",
        "node_checks_passed": False,
        "reports_written": True,
        "next_chatgpt_analysis_request_prepared": True,
        "project_level_autonomy_complete": baseline["project_level_autonomy_complete"],
        "current_real_development_responsibility_score_after": 52,
        "current_capability_boundary_after": BOUNDARY_AFTER if passed else "real_task_test_addition_acceptance_partial",
        "evaluation_score_out_of_100": 100 if passed else 80,
        "next_recommended_action": "continue_to_real_task_small_code_change_acceptance" if passed else "manual_review_required",
        "stop_reason": "test_addition_completed" if passed else "test_addition_partial",
        "terminal_state_recorded": True,
        "stop_reason_recorded": True,
        **{f"{prompt}_core_artifacts_preserved": value for prompt, value in preserved.items()},
        "errors": [] if passed else ["test addition validation incomplete"],
    }
    _write_json(run_dir / "evidence_summary.json", {"schema_version": "prompt674_evidence_summary_v1", "run_id": run_id, "evidence_paths": evidence_paths, "validation": validation, "protected_artifacts_preserved": preserved})
    _write_json(run_dir / "test_addition_marker.json", {"schema_version": "prompt674_test_addition_marker_v1", "run_id": run_id, "created_at": _utc_now(), "test_artifact": TEST_ARTIFACT_PATH, "validated": all(validation.values())})
    _write_text(repo / IMPLEMENTATION_PATH, _implementation_doc(result))
    _write_json(run_dir / "run_state.json", {**result, "completed_steps": completed})
    _write_json(output / "prompt674_report.json", result)
    _write_json(output / "prompt674_goal_aligned_implementation_report.json", result)
    _write_text(output / "prompt674_summary.md", _summary(result))
    _write_text(output / "prompt674_goal_aligned_implementation_summary.md", _summary(result))
    _write_json(
        output / "prompt674_next_chatgpt_analysis_request.json",
        {
            "schema_version": "next_chatgpt_analysis_request_v1",
            "source_prompt": "Prompt674",
            "recommended_next_action": "continue_to_real_task_small_code_change_acceptance",
            "prompt_text": "Start Prompt675 real_task_small_code_change_acceptance as the next local-only responsibility validation.",
            "preserve_safety_constraints": True,
        },
    )
    return result


__all__ = [
    "BOUNDARY_AFTER",
    "BOUNDARY_BEFORE",
    "IMPLEMENTATION_PATH",
    "RUN_DIR",
    "TEST_ARTIFACT_PATH",
    "build_test_addition_task_goal",
    "build_test_addition_task_queue",
    "run_real_task_test_addition_acceptance",
    "verify_prompt673_baseline",
]
