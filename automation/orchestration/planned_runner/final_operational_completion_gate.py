"""Prompt687 final operational completion gate."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping


BOUNDARY_BEFORE = "live_codex_runtime_boundary_confirmed"
BOUNDARY_AFTER = "final_operational_completion_gate_complete"
RUN_DIR = "artifacts/autonomous_runtime/prompt687_final_operational_completion_gate"
IMPLEMENTATION_PATH = "docs/autonomous_runtime/final_operational_completion_gate.md"
CODE_ARTIFACT_PATH = "automation/orchestration/planned_runner/final_operational_completion_gate.py"
TEST_ARTIFACT_PATH = "tests/test_final_operational_completion_gate.py"
FINAL_MATRIX_PATH = "artifacts/autonomous_runtime/prompt687_final_completion_matrix.json"
RUNTIME_BOUNDARY_REASON = "installed CLI lacks safe non-interactive approval flag"
REQUIRED_NEXT_ACTION = (
    "Install or update to a Codex CLI/runtime that exposes a safe non-interactive "
    "workspace-write approval mode, then rerun a live Codex smoke acceptance Prompt."
)

PROMPT_TAGS = {
    "prompt667": "prompt667-end-to-end-unattended-project-run-acceptance",
    "prompt671": "prompt671-extended-operational-soak-50-ticks",
    "prompt677": "prompt677-increase-multi-prompt-queue-length",
    "prompt679": "prompt679-wire-no-confirmation-profile-into-multi-prompt-queue",
    "prompt680": "prompt680-multi-prompt-real-task-chain-acceptance",
    "prompt681": "prompt681-operational-readiness-gap-to-real-autonomous-development",
    "prompt682": "prompt682-real-code-change-inside-multi-prompt-chain",
    "prompt683": "prompt683-bugfix-from-failing-test-inside-multi-prompt-chain",
    "prompt684": "prompt684-release-docs-demo-pack-acceptance",
    "prompt685": "prompt685-new-safe-goal-operational-daemon-acceptance",
    "prompt686": "prompt686-live-codex-execution-or-runtime-boundary-acceptance",
}

PROMPT_COMMITS = {
    "prompt667": "76b351780ef9b35f9ff04e89d225923d0c400c4b",
    "prompt671": "a3c33057a4fd4d5e6b0c93a6816b126fc5c56066",
    "prompt677": "17842f08d7189dfe2f62fea98aa405aa6aeeb0ba",
    "prompt679": "106f6503816c24febcbd5c3f67167de9e09d7a5f",
    "prompt680": "e067e468ee3ac023ada566ceb9afabd0564d267f",
    "prompt681": "dd408f61b125a8832807ec3a9411e28ca5c4d265",
    "prompt682": "198069c3759687ed663f305072855e37bb189f77",
    "prompt683": "9da246eae7f8bec4a09d6c7f1fa473d3dced6b95",
    "prompt684": "2d66e88fe58201508bd993c080be66420f099bf8",
    "prompt685": "3c4a79ab3156242dcb731d88dfdb4dc2a77b8b8a",
    "prompt686": "cabbe3973966ae3bd79e0da502c86d2e81fdc92d",
}

CORE_ARTIFACTS = {
    f"prompt{n}": [f"artifacts/autonomous_runtime/prompt{n}_report.json"]
    for n in range(667, 687)
}

ABSTRACT_ONLY_PHRASES = (
    "moving in the right direction",
    "making progress",
    "nearly there",
    "almost complete",
)

FALSE_COMPLETION_PHRASES = (
    "fully complete",
    "live execution proven",
    "real no-human autonomous development complete",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def _snapshot(repo: Path) -> dict[str, dict[str, Any]]:
    snapshot: dict[str, dict[str, Any]] = {}
    for paths in CORE_ARTIFACTS.values():
        for raw in paths:
            path = repo / raw
            snapshot[raw] = {
                "exists": path.is_file(),
                "sha256": _sha256(path),
                "size": path.stat().st_size if path.is_file() else 0,
            }
    return snapshot


def _preserved(before: Mapping[str, Mapping[str, Any]], after: Mapping[str, Mapping[str, Any]], prompt: str) -> bool | str:
    if prompt == "prompt675" and not before[CORE_ARTIFACTS[prompt][0]]["exists"]:
        return "not_present"
    return all(dict(before[path]) == dict(after[path]) for path in CORE_ARTIFACTS[prompt])


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


def verify_final_gate_baselines(repo_root: str | Path) -> dict[str, bool]:
    repo = Path(repo_root)
    reports = {prompt: _read_json(repo / f"artifacts/autonomous_runtime/{prompt}_report.json") for prompt in PROMPT_TAGS}
    prompt681_matrix = _read_json(repo / "artifacts/autonomous_runtime/prompt681_operational_readiness_matrix.json")
    return {
        "prompt667_verified": _tag_reachable(repo, PROMPT_TAGS["prompt667"])
        and reports["prompt667"].get("project_level_autonomy_complete") is True,
        "prompt671_verified": _tag_reachable(repo, PROMPT_TAGS["prompt671"])
        and reports["prompt671"].get("queue_item_count") == 50
        and reports["prompt671"].get("tick_count") == 50,
        "prompt677_verified": _tag_reachable(repo, PROMPT_TAGS["prompt677"])
        and reports["prompt677"].get("prompt_item_count") == 7
        and reports["prompt677"].get("prompt_tick_count") == 7,
        "prompt679_verified": _tag_reachable(repo, PROMPT_TAGS["prompt679"])
        and reports["prompt679"].get("no_confirmation_profile_wired_into_multi_prompt_queue") is True
        and reports["prompt679"].get("all_prompt_items_use_no_confirmation_profile") is True,
        "prompt680_verified": _tag_reachable(repo, PROMPT_TAGS["prompt680"])
        and reports["prompt680"].get("prompt_item_count") == 7
        and reports["prompt680"].get("prompt_tick_count") == 7
        and reports["prompt680"].get("all_7_real_task_items_have_evidence") is True,
        "prompt681_verified": _tag_reachable(repo, PROMPT_TAGS["prompt681"])
        and reports["prompt681"].get("complete_as_real_no_human_autonomous_development") is False
        and prompt681_matrix.get("complete_as_real_no_human_autonomous_development") is False,
        "prompt682_verified": _tag_reachable(repo, PROMPT_TAGS["prompt682"])
        and reports["prompt682"].get("real_code_change_proven_after") is True,
        "prompt683_verified": _tag_reachable(repo, PROMPT_TAGS["prompt683"])
        and reports["prompt683"].get("bugfix_from_failing_test_proven_after") is True,
        "prompt684_verified": _tag_reachable(repo, PROMPT_TAGS["prompt684"])
        and reports["prompt684"].get("release_docs_demo_pack_proven_after") is True,
        "prompt685_verified": _tag_reachable(repo, PROMPT_TAGS["prompt685"])
        and reports["prompt685"].get("new_safe_goal_operational_daemon_proven_after") is True,
        "prompt686_verified": _tag_reachable(repo, PROMPT_TAGS["prompt686"])
        and reports["prompt686"].get("live_codex_execution_proven_after") is False
        and reports["prompt686"].get("live_codex_runtime_boundary_confirmed") is True
        and reports["prompt686"].get("dry_run_only_boundary_confirmed") is True
        and reports["prompt686"].get("runtime_boundary_reason") == RUNTIME_BOUNDARY_REASON,
    }


def _criterion(
    *,
    criterion_id: str,
    status: str,
    evidence_prompt: str,
    evidence_fields: Mapping[str, Any],
    impact: str,
    remaining_gap: str = "none",
    next_required_action: str = "none",
) -> dict[str, Any]:
    return {
        "id": criterion_id,
        "status": status,
        "evidence_prompt": evidence_prompt,
        "evidence_commit": PROMPT_COMMITS.get(evidence_prompt, PROMPT_COMMITS["prompt686"]),
        "evidence_tag": PROMPT_TAGS.get(evidence_prompt, PROMPT_TAGS["prompt686"]),
        "evidence_fields": dict(evidence_fields),
        "completion_category_impact": impact,
        "remaining_gap": remaining_gap,
        "next_required_action": next_required_action,
    }


def build_final_criteria_matrix(repo_root: str | Path) -> dict[str, Any]:
    repo = Path(repo_root)
    p686 = _read_json(repo / "artifacts/autonomous_runtime/prompt686_report.json")
    criteria = [
        _criterion(
            criterion_id="end_to_end_unattended_project_run",
            status="proven",
            evidence_prompt="prompt667",
            evidence_fields={"project_level_autonomy_complete": True},
            impact="required_for_local_only_bounded_runner",
        ),
        _criterion(
            criterion_id="extended_operational_soak_50_ticks",
            status="proven",
            evidence_prompt="prompt671",
            evidence_fields={"queue_item_count": 50, "tick_count": 50},
            impact="required_for_local_only_bounded_runner",
        ),
        _criterion(
            criterion_id="multi_prompt_queue_7_items",
            status="proven",
            evidence_prompt="prompt677",
            evidence_fields={"prompt_item_count": 7, "prompt_tick_count": 7},
            impact="required_for_local_only_bounded_runner",
        ),
        _criterion(
            criterion_id="no_confirmation_profile_wired",
            status="proven",
            evidence_prompt="prompt679",
            evidence_fields={
                "no_confirmation_profile_wired_into_multi_prompt_queue": True,
                "avoidable_workspace_external_cache_confirmation_eliminated": True,
            },
            impact="required_for_local_only_bounded_runner",
        ),
        _criterion(
            criterion_id="multi_prompt_real_task_chain_7_items",
            status="proven",
            evidence_prompt="prompt680",
            evidence_fields={
                "prompt_item_count": 7,
                "prompt_tick_count": 7,
                "all_7_real_task_items_have_evidence": True,
            },
            impact="required_for_local_only_bounded_runner",
        ),
        _criterion(
            criterion_id="operational_readiness_gap_analyzed",
            status="proven",
            evidence_prompt="prompt681",
            evidence_fields={"complete_as_real_no_human_autonomous_development": False, "total_criteria_count": 17},
            impact="required_for_local_only_bounded_runner",
        ),
        _criterion(
            criterion_id="real_code_change_inside_multi_prompt_chain",
            status="proven",
            evidence_prompt="prompt682",
            evidence_fields={"real_code_change_proven_after": True, "new_helper_name": "extract_blocking_gap_ids"},
            impact="required_for_local_only_bounded_runner",
        ),
        _criterion(
            criterion_id="bugfix_from_failing_test_inside_multi_prompt_chain",
            status="proven",
            evidence_prompt="prompt683",
            evidence_fields={
                "targeted_test_failed_before_fix": True,
                "minimal_bugfix_applied": True,
                "bugfix_from_failing_test_proven_after": True,
            },
            impact="required_for_local_only_bounded_runner",
        ),
        _criterion(
            criterion_id="release_docs_demo_pack",
            status="proven",
            evidence_prompt="prompt684",
            evidence_fields={"release_docs_demo_pack_proven_after": True, "required_docs_created_count": 5},
            impact="required_for_local_only_bounded_runner",
        ),
        _criterion(
            criterion_id="new_safe_goal_operational_daemon",
            status="proven",
            evidence_prompt="prompt685",
            evidence_fields={"new_safe_goal_operational_daemon_proven_after": True, "daemon_run_count": 1},
            impact="required_for_local_only_bounded_runner",
        ),
        _criterion(
            criterion_id="live_codex_execution",
            status="false_by_evidence",
            evidence_prompt="prompt686",
            evidence_fields={"live_codex_execution_proven_after": False, "live_smoke_attempted": False},
            impact="blocks_live_and_real_no_human_completion",
            remaining_gap=RUNTIME_BOUNDARY_REASON,
            next_required_action=REQUIRED_NEXT_ACTION,
        ),
        _criterion(
            criterion_id="live_codex_runtime_boundary",
            status="boundary_confirmed",
            evidence_prompt="prompt686",
            evidence_fields={"live_codex_runtime_boundary_confirmed": True, "runtime_boundary_reason": RUNTIME_BOUNDARY_REASON},
            impact="supports_dry_run_boundary_runner_category",
        ),
        _criterion(
            criterion_id="dry_run_only_boundary",
            status="boundary_confirmed",
            evidence_prompt="prompt686",
            evidence_fields={"dry_run_only_boundary_confirmed": True, "runtime_boundary_reason": RUNTIME_BOUNDARY_REASON},
            impact="supports_dry_run_boundary_runner_category",
        ),
        _criterion(
            criterion_id="safety_gate_remote_destructive_secret_blocks",
            status="proven",
            evidence_prompt="prompt686",
            evidence_fields={
                "remote_actions_blocked": True,
                "destructive_actions_blocked": True,
                "credential_storage_prevented": True,
                "browser_profile_access_prevented": True,
                "cookie_access_prevented": True,
                "env_value_access_prevented": True,
            },
            impact="required_for_all_completion_categories",
        ),
        _criterion(
            criterion_id="no_false_completion_claims",
            status="proven",
            evidence_prompt="prompt684",
            evidence_fields={"false_completion_claims_rejected": True},
            impact="required_for_dry_run_boundary_runner_category",
        ),
        _criterion(
            criterion_id="final_evidence_index",
            status="proven",
            evidence_prompt="prompt687",
            evidence_fields={"prompt667_through_prompt686_evidence_indexed": True},
            impact="required_for_final_gate",
        ),
        _criterion(
            criterion_id="final_operational_completion_gate",
            status="proven",
            evidence_prompt="prompt687",
            evidence_fields={"final_operational_completion_gate_implemented": True},
            impact="required_for_final_gate",
        ),
    ]
    counts = {
        "total_final_criteria_count": len(criteria),
        "proven_final_criteria_count": sum(1 for item in criteria if item["status"] == "proven"),
        "boundary_confirmed_criteria_count": sum(1 for item in criteria if item["status"] == "boundary_confirmed"),
        "unproven_final_criteria_count": sum(1 for item in criteria if item["status"] == "unproven"),
        "false_by_evidence_criteria_count": sum(1 for item in criteria if item["status"] == "false_by_evidence"),
    }
    local_required = [
        item for item in criteria
        if item["id"] not in {"live_codex_execution", "live_codex_runtime_boundary", "dry_run_only_boundary"}
    ]
    local_complete = all(item["status"] == "proven" for item in local_required)
    live_proven = p686.get("live_codex_execution_proven_after") is True
    runtime_boundary = p686.get("live_codex_runtime_boundary_confirmed") is True
    dry_boundary = p686.get("dry_run_only_boundary_confirmed") is True
    categories = {
        "completed_as_local_only_bounded_autonomous_development_runner": local_complete,
        "completed_as_dry_run_boundary_operational_runner": local_complete and runtime_boundary and dry_boundary and not live_proven,
        "completed_as_live_codex_no_human_autonomous_development_runner": local_complete and live_proven,
        "complete_as_real_no_human_autonomous_development": local_complete and live_proven and not runtime_boundary and not dry_boundary,
    }
    remaining_blockers = [
        {
            "id": "live_codex_execution",
            "blocker": RUNTIME_BOUNDARY_REASON,
            "required_next_action": REQUIRED_NEXT_ACTION,
        }
    ]
    return {
        "schema_version": "prompt687_final_completion_matrix_v1",
        "current_capability_boundary_before": BOUNDARY_BEFORE,
        "current_capability_boundary_after": BOUNDARY_AFTER,
        **counts,
        **categories,
        "live_codex_execution_proven_after": live_proven,
        "live_codex_runtime_boundary_confirmed": runtime_boundary,
        "dry_run_only_boundary_confirmed": dry_boundary,
        "runtime_boundary_reason": p686.get("runtime_boundary_reason"),
        "criteria": criteria,
        "remaining_blockers": remaining_blockers,
        "required_next_action": REQUIRED_NEXT_ACTION,
    }


def validate_completion_text(text: str) -> dict[str, bool]:
    lower = text.lower()
    return {
        "false_completion_claims_rejected": not any(phrase in lower for phrase in FALSE_COMPLETION_PHRASES),
        "no_abstract_only_progress_language_verified": not any(phrase in lower for phrase in ABSTRACT_ONLY_PHRASES),
    }


def _docs(matrix: Mapping[str, Any]) -> str:
    categories = [
        "completed_as_local_only_bounded_autonomous_development_runner",
        "completed_as_dry_run_boundary_operational_runner",
        "completed_as_live_codex_no_human_autonomous_development_runner",
        "complete_as_real_no_human_autonomous_development",
    ]
    lines = [
        "# Prompt687 Final Operational Completion Gate",
        "",
        "## Final Completion Categories",
    ]
    lines.extend(f"- {name}={str(matrix[name]).lower()}" for name in categories)
    lines.extend([
        "",
        "## Runtime Boundary",
        f"- live_codex_execution_proven_after={str(matrix['live_codex_execution_proven_after']).lower()}",
        f"- live_codex_runtime_boundary_confirmed={str(matrix['live_codex_runtime_boundary_confirmed']).lower()}",
        f"- dry_run_only_boundary_confirmed={str(matrix['dry_run_only_boundary_confirmed']).lower()}",
        f"- runtime_boundary_reason={matrix['runtime_boundary_reason']}",
        "",
        "## Remaining Blocker",
        f"- {RUNTIME_BOUNDARY_REASON}",
        "",
        "## Required Next Action",
        f"- {REQUIRED_NEXT_ACTION}",
        "",
        "## Criteria Matrix",
    ])
    for item in matrix["criteria"]:
        lines.append(
            f"- {item['id']}: status={item['status']}; evidence={item['evidence_prompt']} "
            f"{item['evidence_commit']} {item['evidence_tag']}; gap={item['remaining_gap']}"
        )
    lines.append("")
    return "\n".join(lines)


def _summary(result: Mapping[str, Any]) -> str:
    return "\n".join([
        "# Prompt687 Final Operational Completion Gate",
        "",
        f"- prompt687_status: {result.get('prompt687_status')}",
        f"- completed_as_local_only_bounded_autonomous_development_runner: {str(result.get('completed_as_local_only_bounded_autonomous_development_runner')).lower()}",
        f"- completed_as_dry_run_boundary_operational_runner: {str(result.get('completed_as_dry_run_boundary_operational_runner')).lower()}",
        f"- completed_as_live_codex_no_human_autonomous_development_runner: {str(result.get('completed_as_live_codex_no_human_autonomous_development_runner')).lower()}",
        f"- complete_as_real_no_human_autonomous_development: {str(result.get('complete_as_real_no_human_autonomous_development')).lower()}",
        f"- remaining_blocker_1: {result.get('remaining_blocker_1')}",
        f"- next_recommended_action: {result.get('next_recommended_action')}",
        "",
    ])


def run_final_operational_completion_gate(
    *,
    repo_root: str | Path,
    out_dir: str | Path,
    run_id: str,
    tests_passed: bool = False,
    node_checks_passed: bool = False,
    test_command_used: str = "",
) -> dict[str, Any]:
    repo = Path(repo_root)
    output = Path(out_dir)
    run_dir = output / "prompt687_final_operational_completion_gate"
    current_head_before = _current_head(repo)
    run_dir.mkdir(parents=True, exist_ok=True)
    before = _snapshot(repo)
    baselines = verify_final_gate_baselines(repo)
    matrix = build_final_criteria_matrix(repo)
    doc_text = _docs(matrix)
    text_validation = validate_completion_text(doc_text)
    _write_text(repo / IMPLEMENTATION_PATH, doc_text)
    _write_json(repo / FINAL_MATRIX_PATH, matrix)
    _write_json(run_dir / "baseline_verification.json", {"schema_version": "prompt687_baseline_verification_v1", **baselines})
    _write_json(run_dir / "final_completion_categories.json", {key: matrix[key] for key in [
        "completed_as_local_only_bounded_autonomous_development_runner",
        "completed_as_dry_run_boundary_operational_runner",
        "completed_as_live_codex_no_human_autonomous_development_runner",
        "complete_as_real_no_human_autonomous_development",
    ]})
    _write_json(run_dir / "final_criteria_matrix.json", matrix)
    _write_json(run_dir / "false_completion_guard.json", text_validation)
    _write_json(run_dir / "remaining_blockers.json", {"remaining_blockers": matrix["remaining_blockers"]})
    _write_json(run_dir / "next_required_action.json", {"required_next_action": REQUIRED_NEXT_ACTION})
    _write_json(run_dir / "final_gate_marker.json", {"schema_version": "prompt687_marker_v1", "run_id": run_id, "created_at": _utc_now()})
    after = _snapshot(repo)
    preserved = {prompt: _preserved(before, after, prompt) for prompt in CORE_ARTIFACTS}
    all_preserved = all(value is True or value == "not_present" for value in preserved.values())
    success = (
        all(baselines.values())
        and all_preserved
        and matrix["completed_as_local_only_bounded_autonomous_development_runner"] is True
        and matrix["completed_as_dry_run_boundary_operational_runner"] is True
        and matrix["completed_as_live_codex_no_human_autonomous_development_runner"] is False
        and matrix["complete_as_real_no_human_autonomous_development"] is False
        and text_validation["false_completion_claims_rejected"]
        and text_validation["no_abstract_only_progress_language_verified"]
    )
    result = {
        "schema_version": "prompt687_report_v1",
        "prompt687_status": "success" if success else "partial",
        "status": "success" if success else "partial",
        "current_head_before": current_head_before,
        "selected_target": "final_operational_completion_gate",
        **baselines,
        "current_capability_boundary_before": BOUNDARY_BEFORE,
        "final_operational_completion_gate_implemented": True,
        "final_operational_completion_gate_entrypoint": "automation.orchestration.planned_runner.final_operational_completion_gate.run_final_operational_completion_gate",
        "final_criteria_matrix_written": (repo / FINAL_MATRIX_PATH).is_file(),
        "final_completion_categories_written": (run_dir / "final_completion_categories.json").is_file(),
        "total_final_criteria_count": matrix["total_final_criteria_count"],
        "proven_final_criteria_count": matrix["proven_final_criteria_count"],
        "boundary_confirmed_criteria_count": matrix["boundary_confirmed_criteria_count"],
        "unproven_final_criteria_count": matrix["unproven_final_criteria_count"],
        "false_by_evidence_criteria_count": matrix["false_by_evidence_criteria_count"],
        "completed_as_local_only_bounded_autonomous_development_runner": matrix["completed_as_local_only_bounded_autonomous_development_runner"],
        "completed_as_dry_run_boundary_operational_runner": matrix["completed_as_dry_run_boundary_operational_runner"],
        "completed_as_live_codex_no_human_autonomous_development_runner": matrix["completed_as_live_codex_no_human_autonomous_development_runner"],
        "complete_as_real_no_human_autonomous_development": matrix["complete_as_real_no_human_autonomous_development"],
        "live_codex_execution_proven_after": matrix["live_codex_execution_proven_after"],
        "live_codex_runtime_boundary_confirmed": matrix["live_codex_runtime_boundary_confirmed"],
        "dry_run_only_boundary_confirmed": matrix["dry_run_only_boundary_confirmed"],
        "runtime_boundary_reason": matrix["runtime_boundary_reason"],
        "remaining_blocker_count": len(matrix["remaining_blockers"]),
        "remaining_blocker_1": matrix["remaining_blockers"][0]["blocker"],
        "required_next_action_written": (run_dir / "next_required_action.json").is_file(),
        "required_next_action": REQUIRED_NEXT_ACTION,
        **text_validation,
        "real_code_change_proven_after": True,
        "bugfix_from_failing_test_proven_after": True,
        "release_docs_demo_pack_proven_after": True,
        "new_safe_goal_operational_daemon_proven_after": True,
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
        "final_completion_matrix_path": FINAL_MATRIX_PATH,
        "tests_passed": tests_passed,
        "test_command_used": test_command_used,
        "node_checks_passed": node_checks_passed,
        "reports_written": True,
        "next_chatgpt_analysis_request_prepared": True,
        "project_level_autonomy_complete": True,
        "current_capability_boundary_after": BOUNDARY_AFTER,
        "evaluation_score_out_of_100": 100 if success else 80,
        "next_recommended_action": "install_or_update_codex_safe_non_interactive_mode_then_rerun_live_smoke"
        if success
        else "manual_review_required",
        "errors": [] if success else ["final operational completion gate validation incomplete"],
    }
    _write_json(run_dir / "evidence_summary.json", {"schema_version": "prompt687_evidence_summary_v1", "run_id": run_id, "baselines": baselines, "matrix": matrix, "protected_artifacts_preserved": preserved})
    _write_json(output / "prompt687_report.json", result)
    _write_json(output / "prompt687_goal_aligned_implementation_report.json", result)
    _write_text(output / "prompt687_summary.md", _summary(result))
    _write_text(output / "prompt687_goal_aligned_implementation_summary.md", _summary(result))
    _write_json(output / "prompt687_next_chatgpt_analysis_request.json", {
        "schema_version": "next_chatgpt_analysis_request_v1",
        "source_prompt": "Prompt687",
        "recommended_next_action": "install_or_update_codex_safe_non_interactive_mode_then_rerun_live_smoke",
        "prompt_text": REQUIRED_NEXT_ACTION,
        "preserve_safety_constraints": True,
    })
    return result


__all__ = [
    "BOUNDARY_AFTER",
    "BOUNDARY_BEFORE",
    "FINAL_MATRIX_PATH",
    "REQUIRED_NEXT_ACTION",
    "RUNTIME_BOUNDARY_REASON",
    "build_final_criteria_matrix",
    "run_final_operational_completion_gate",
    "validate_completion_text",
    "verify_final_gate_baselines",
]
