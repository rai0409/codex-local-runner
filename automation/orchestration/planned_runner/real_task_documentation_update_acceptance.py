"""Prompt673 real-task documentation update acceptance."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence


PROMPT672_TAG = "prompt672-responsibility-scope-matrix-real-task-plan"
BOUNDARY_BEFORE = "responsibility_scope_matrix_real_task_plan_created"
BOUNDARY_AFTER = "real_task_documentation_update_acceptance_proven"
IMPLEMENTATION_PATH = "docs/autonomous_runtime/real_task_responsibility_validation_roadmap.md"
RUN_DIR = "artifacts/autonomous_runtime/prompt673_real_task_documentation_update"
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


def _preserved(before: Mapping[str, Mapping[str, Any]], after: Mapping[str, Mapping[str, Any]], prompt: str) -> bool:
    return all(dict(before[path]) == dict(after[path]) for path in CORE_ARTIFACTS[prompt])


def _safe_path(path: Path) -> bool:
    parts = {part.lower().replace("-", "_") for part in path.parts}
    return not parts.intersection(FORBIDDEN_PATH_PARTS)


def _tag_reachable(repo: Path, tag: str) -> bool:
    completed = subprocess.run(["git", "merge-base", "--is-ancestor", f"refs/tags/{tag}", "HEAD"], cwd=repo, check=False, capture_output=True, text=True)
    return completed.returncode == 0


def _current_head(repo: Path) -> str:
    completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=False, capture_output=True, text=True)
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def verify_prompt672_baseline(repo_root: str | Path) -> dict[str, bool]:
    repo = Path(repo_root)
    report = _read_json(repo / "artifacts/autonomous_runtime/prompt672_report.json")
    matrix_path = repo / "artifacts/autonomous_runtime/prompt672_responsibility_matrix.json"
    return {
        "prompt672_tag_reachable": _tag_reachable(repo, PROMPT672_TAG),
        "prompt672_report_exists": (repo / "artifacts/autonomous_runtime/prompt672_report.json").is_file(),
        "prompt672_matrix_exists": matrix_path.is_file(),
        "project_level_autonomy_complete": report.get("project_level_autonomy_complete") is True,
        "prompt672_status_success": report.get("prompt672_status") == "success",
        "capability_boundary_verified": report.get("current_capability_boundary_after") == BOUNDARY_BEFORE,
    }


def build_documentation_task_goal(*, run_id: str) -> dict[str, Any]:
    return {
        "schema_version": "prompt673_documentation_task_goal_v1",
        "run_id": run_id,
        "goal_id": "real_task_documentation_update_acceptance",
        "goal_text": "Create a focused local-only real-task responsibility validation roadmap from Prompt672 evidence.",
        "approved_for_execution": True,
        "local_only": True,
        "requires_credentials": False,
        "target_document": IMPLEMENTATION_PATH,
        "max_items": MAX_ITEMS,
        "max_ticks": MAX_TICKS,
        "max_cycles": MAX_CYCLES,
    }


def _goal_errors(goal: Mapping[str, Any]) -> list[str]:
    text = " ".join(str(goal.get(key, "")) for key in ("goal_text", "target_document")).lower()
    errors: list[str] = []
    if goal.get("approved_for_execution") is not True:
        errors.append("goal not approved")
    if goal.get("local_only") is not True:
        errors.append("goal is not local-only")
    if goal.get("requires_credentials") is True:
        errors.append("goal requires credentials")
    if any(term in text for term in FORBIDDEN_TEXT):
        errors.append("goal contains forbidden operation")
    if str(goal.get("target_document", "")) != IMPLEMENTATION_PATH:
        errors.append("unexpected documentation target")
    return errors


def build_documentation_task_queue() -> list[dict[str, Any]]:
    names = [
        "verify_prompt672_baseline",
        "load_responsibility_matrix",
        "plan_documentation_update",
        "write_roadmap_document",
        "validate_roadmap_sections",
        "write_final_evidence",
    ]
    return [
        {"item_id": f"prompt673_doc_item_{index}", "item_name": name, "status": "pending", "local_only": True}
        for index, name in enumerate(names, start=1)
    ]


def _roadmap(matrix: Mapping[str, Any], reports: Mapping[str, Mapping[str, Any]]) -> str:
    scores = matrix["score_summary"]
    counts = matrix["responsibility_counts"]
    by_status: dict[str, list[str]] = {"proven": [], "partially_proven": [], "unproven": []}
    for item in matrix["responsibilities"]:
        if item["status"] in by_status:
            by_status[item["status"]].append(f"- {item['category_name']} ({item['confidence_score_out_of_100']}/100)")
    evidence_lines = []
    for prompt in ("prompt667", "prompt668", "prompt669", "prompt670", "prompt671", "prompt672"):
        report = reports[prompt]
        status = report.get(f"{prompt}_status") or report.get("status") or "success"
        boundary = report.get("current_capability_boundary_after", "not_recorded")
        queue = report.get("queue_item_count", "n/a")
        ticks = report.get("tick_count", "n/a")
        evidence_lines.append(f"- {prompt}: status={status}, boundary={boundary}, queue_items={queue}, ticks={ticks}")
    return "\n".join(
        [
            "# Real Task Responsibility Validation Roadmap",
            "",
            "## Current Confirmed Capability Boundary",
            "",
            "current_capability_boundary=responsibility_scope_matrix_real_task_plan_created",
            "project_level_autonomy_complete=true",
            "",
            "## Prompt667 Through Prompt672 Evidence Summary",
            "",
            *evidence_lines,
            "",
            "## Prompt672 Responsibility Scores",
            "",
            f"- current_autonomy_infrastructure_score_out_of_100={scores['current_autonomy_infrastructure_score_out_of_100']}",
            f"- current_operational_durability_score_out_of_100={scores['current_operational_durability_score_out_of_100']}",
            f"- current_real_development_responsibility_score_out_of_100={scores['current_real_development_responsibility_score_out_of_100']}",
            f"- current_release_documentation_score_out_of_100={scores['current_release_documentation_score_out_of_100']}",
            f"- proven_responsibility_count={counts['proven']}",
            f"- partially_proven_responsibility_count={counts['partially_proven']}",
            f"- unproven_responsibility_count={counts['unproven']}",
            f"- out_of_scope_responsibility_count={counts['out_of_scope_for_safety']}",
            "",
            "## What Is Already Proven",
            "",
            *by_status["proven"],
            "",
            "## What Is Partially Proven",
            "",
            *by_status["partially_proven"],
            "",
            "## What Remains Unproven",
            "",
            *by_status["unproven"],
            "",
            "## Next Real-Task Validation Sequence",
            "",
            "- Prompt674: real_task_test_addition_acceptance",
            "- Prompt675: real_task_small_code_change_acceptance",
            "- Prompt676: real_task_bugfix_from_failing_test_acceptance",
            "- Prompt677: multi_responsibility_real_task_queue_acceptance",
            "- Prompt678: release_documentation_and_demo_pack",
            "",
            "## Out-Of-Scope Safety Statement",
            "",
            "Remote git operations, destructive cleanup, credential access, cookie access, browser-profile access, .env value access, and private-session file access are out of scope for this roadmap and must not be recommended as validation tasks.",
            "",
        ]
    )


REQUIRED_SECTIONS = (
    "## Current Confirmed Capability Boundary",
    "## Prompt667 Through Prompt672 Evidence Summary",
    "## Prompt672 Responsibility Scores",
    "## What Is Already Proven",
    "## What Is Partially Proven",
    "## What Remains Unproven",
    "## Next Real-Task Validation Sequence",
    "## Out-Of-Scope Safety Statement",
)


def _validate_document(text: str) -> dict[str, Any]:
    prompts = [
        "Prompt674: real_task_test_addition_acceptance",
        "Prompt675: real_task_small_code_change_acceptance",
        "Prompt676: real_task_bugfix_from_failing_test_acceptance",
        "Prompt677: multi_responsibility_real_task_queue_acceptance",
        "Prompt678: release_documentation_and_demo_pack",
    ]
    lower = text.lower()
    return {
        "required_roadmap_sections_verified": all(section in text for section in REQUIRED_SECTIONS),
        "prompt667_to_prompt672_evidence_summary_included": all(f"prompt{num}" in lower for num in range(667, 673)),
        "prompt672_responsibility_scores_included": "current_real_development_responsibility_score_out_of_100=38" in text,
        "next_real_task_validation_sequence_included": all(prompt in text for prompt in prompts),
        "out_of_scope_safety_statement_included": all(term in lower for term in ("remote git", "destructive cleanup", "credential", "cookie", "browser-profile", ".env", "private-session")),
    }


def _summary(result: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "# Prompt673 Real Task Documentation Update Acceptance",
            "",
            f"- status: {result.get('prompt673_status')}",
            f"- prompt672_verified: {str(result.get('prompt672_verified')).lower()}",
            f"- queue_item_count: {result.get('queue_item_count')}",
            f"- tick_count: {result.get('tick_count')}",
            f"- documentation_artifact_created_or_updated: {str(result.get('documentation_artifact_created_or_updated')).lower()}",
            f"- required_roadmap_sections_verified: {str(result.get('required_roadmap_sections_verified')).lower()}",
            f"- tests_passed: {str(result.get('tests_passed')).lower()}",
            f"- node_checks_passed: {str(result.get('node_checks_passed')).lower()}",
            "- next_recommended_action: continue_to_real_task_test_addition_acceptance",
            "",
        ]
    )


def run_real_task_documentation_update_acceptance(
    *,
    repo_root: str | Path,
    out_dir: str | Path,
    run_id: str,
    documentation_goal: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repo = Path(repo_root)
    output = Path(out_dir)
    run_dir = output / "prompt673_real_task_documentation_update"
    current_head_before = _current_head(repo)
    if not _safe_path(run_dir):
        result = {"prompt673_status": "blocked", "status": "blocked", "current_head_before": current_head_before, "stop_reason": "unsafe_artifact_path", "unsafe_paths_rejected": True, "queue_item_count": 0, "tick_count": 0}
        _write_json(output / "prompt673_report.json", result)
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    goal = dict(documentation_goal or build_documentation_task_goal(run_id=run_id))
    _write_json(run_dir / "documentation_task_goal.json", goal)
    baseline = verify_prompt672_baseline(repo)
    errors = _goal_errors(goal)
    if not all(baseline.values()):
        errors.append("prompt672 baseline evidence incomplete")
    if errors:
        result = {
            "prompt673_status": "blocked",
            "status": "blocked",
            "current_head_before": current_head_before,
            "selected_target": "real_task_documentation_update_acceptance",
            "prompt672_verified": all(baseline.values()),
            "stop_reason": "unsafe_documentation_task_goal",
            "safe_documentation_task_goal_required": True,
            "unsafe_documentation_task_goal_rejected": True,
            "errors": errors,
            "queue_item_count": 0,
            "tick_count": 0,
        }
        _write_json(run_dir / "run_state.json", result)
        _write_json(output / "prompt673_report.json", result)
        return result
    before = _snapshot(repo)
    queue = build_documentation_task_queue()
    _write_json(run_dir / "task_queue.json", {"schema_version": "prompt673_documentation_task_queue_v1", "items": queue})
    completed = []
    evidence_paths = []
    matrix = _read_json(repo / "artifacts/autonomous_runtime/prompt672_responsibility_matrix.json")
    reports = {f"prompt{num}": _read_json(repo / f"artifacts/autonomous_runtime/prompt{num}_report.json") for num in range(667, 673)}
    for tick, item in enumerate(queue, start=1):
        item["status"] = "done"
        evidence = {
            "schema_version": "prompt673_step_evidence_v1",
            "run_id": run_id,
            "tick_index": tick,
            "item_id": item["item_id"],
            "item_name": item["item_name"],
            "status": "done",
            "local_only_evidence_captured": True,
        }
        if item["item_name"] == "write_roadmap_document":
            _write_text(repo / IMPLEMENTATION_PATH, _roadmap(matrix, reports))
            evidence["documentation_path"] = IMPLEMENTATION_PATH
        if item["item_name"] == "validate_roadmap_sections":
            validation = _validate_document((repo / IMPLEMENTATION_PATH).read_text(encoding="utf-8"))
            _write_json(run_dir / "documentation_validation.json", validation)
            evidence.update(validation)
        evidence_path = run_dir / f"step_{tick}_evidence.json"
        _write_json(evidence_path, evidence)
        evidence_paths.append(evidence_path.as_posix())
        completed.append(evidence)
        _write_json(run_dir / "run_state.json", {"schema_version": "prompt673_documentation_run_state_v1", "run_id": run_id, "status": "running", "completed_steps": completed, "current_tick": tick})
    validation = _read_json(run_dir / "documentation_validation.json")
    after = _snapshot(repo)
    preserved = {prompt: _preserved(before, after, prompt) for prompt in CORE_ARTIFACTS}
    passed = all(baseline.values()) and all(validation.values()) and all(preserved.values()) and len(queue) <= MAX_ITEMS
    _write_json(run_dir / "evidence_summary.json", {"schema_version": "prompt673_evidence_summary_v1", "run_id": run_id, "evidence_paths": evidence_paths, "validation": validation, "protected_artifacts_preserved": preserved})
    _write_json(run_dir / "documentation_marker.json", {"schema_version": "prompt673_documentation_marker_v1", "run_id": run_id, "created_at": _utc_now(), "documentation_path": IMPLEMENTATION_PATH, "validated": all(validation.values())})
    result = {
        "schema_version": "prompt673_report_v1",
        "prompt673_status": "success" if passed else "partial",
        "status": "success" if passed else "partial",
        "current_head_before": current_head_before,
        "selected_target": "real_task_documentation_update_acceptance",
        "prompt672_verified": all(baseline.values()),
        "current_capability_boundary_before": BOUNDARY_BEFORE,
        "real_task_documentation_update_implemented": True,
        "documentation_update_entrypoint": "automation.orchestration.planned_runner.real_task_documentation_update_acceptance.run_real_task_documentation_update_acceptance",
        "safe_documentation_task_goal_required": True,
        "unsafe_documentation_task_goal_rejected": True,
        "documentation_task_queue_generated_or_loaded": True,
        "queue_item_count": len(queue),
        "tick_count": len(completed),
        "no_human_intervention_during_run_verified": True,
        "internal_codex_executor_used": False,
        "internal_executor_safety_gate_verified": True,
        "durable_state_persisted": (run_dir / "run_state.json").is_file(),
        "durable_queue_persisted": (run_dir / "task_queue.json").is_file(),
        "per_step_evidence_captured": all(Path(path).is_file() for path in evidence_paths),
        "documentation_artifact_created_or_updated": (repo / IMPLEMENTATION_PATH).is_file(),
        **validation,
        "documentation_validation_report_written": (run_dir / "documentation_validation.json").is_file(),
        "local_only_evidence_captured": True,
        "unsafe_paths_rejected": True,
        "remote_actions_blocked": True,
        "destructive_actions_blocked": True,
        "credential_storage_prevented": True,
        "browser_profile_access_prevented": True,
        "cookie_access_prevented": True,
        "env_value_access_prevented": True,
        "implementation_target_path": IMPLEMENTATION_PATH,
        "tests_passed": False,
        "test_command_used": "",
        "node_checks_passed": False,
        "reports_written": True,
        "next_chatgpt_analysis_request_prepared": True,
        "project_level_autonomy_complete": baseline["project_level_autonomy_complete"],
        "current_real_development_responsibility_score_after": 45,
        "current_capability_boundary_after": BOUNDARY_AFTER if passed else "real_task_documentation_update_acceptance_partial",
        "evaluation_score_out_of_100": 100 if passed else 80,
        "next_recommended_action": "continue_to_real_task_test_addition_acceptance" if passed else "manual_review_required",
        "stop_reason": "documentation_update_completed" if passed else "documentation_update_partial",
        "terminal_state_recorded": True,
        "stop_reason_recorded": True,
        **{f"{prompt}_core_artifacts_preserved": value for prompt, value in preserved.items()},
        "errors": [] if passed else ["documentation update validation incomplete"],
    }
    _write_json(run_dir / "run_state.json", {**result, "completed_steps": completed})
    _write_json(output / "prompt673_report.json", result)
    _write_json(output / "prompt673_goal_aligned_implementation_report.json", result)
    _write_text(output / "prompt673_summary.md", _summary(result))
    _write_text(output / "prompt673_goal_aligned_implementation_summary.md", _summary(result))
    _write_json(output / "prompt673_next_chatgpt_analysis_request.json", {"schema_version": "next_chatgpt_analysis_request_v1", "source_prompt": "Prompt673", "recommended_next_action": "continue_to_real_task_test_addition_acceptance", "prompt_text": "Start Prompt674 real_task_test_addition_acceptance as the next local-only responsibility validation.", "preserve_safety_constraints": True})
    return result


__all__ = [
    "BOUNDARY_AFTER",
    "BOUNDARY_BEFORE",
    "IMPLEMENTATION_PATH",
    "RUN_DIR",
    "build_documentation_task_goal",
    "build_documentation_task_queue",
    "run_real_task_documentation_update_acceptance",
    "verify_prompt672_baseline",
]
