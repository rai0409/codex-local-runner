"""Project-level autonomy completion gate.

The gate audits durable evidence from Prompt660C through Prompt665. It can mark
readiness for the final Prompt667 end-to-end acceptance, but it deliberately
keeps project_level_autonomy_complete false until that final evidence exists.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping


PROMPT_EVIDENCE = {
    "prompt660c": {
        "tag": "prompt660c-browser-to-codex-full-cycle-acceptance",
        "report": "artifacts/autonomous_runtime/prompt660c_report.json",
    },
    "prompt661a": {
        "tag": "prompt661a-browser-to-codex-second-cycle-acceptance",
        "report": "artifacts/autonomous_runtime/prompt661a_report.json",
    },
    "prompt662": {
        "tag": "prompt662-bounded-multi-cycle-internal-executor-gate",
        "report": "artifacts/autonomous_runtime/prompt662_report.json",
    },
    "prompt663": {
        "tag": "prompt663-daemon-hardening-bounded-autonomy",
        "report": "artifacts/autonomous_runtime/prompt663_report.json",
    },
    "prompt664": {
        "tag": "prompt664-long-running-daemon-acceptance",
        "report": "artifacts/autonomous_runtime/prompt664_report.json",
    },
    "prompt665": {
        "tag": "prompt665-bounded-unattended-acceptance",
        "report": "artifacts/autonomous_runtime/prompt665_report.json",
    },
}

REQUIRED_SURFACES = [
    "automation/execution/codex_executor_adapter.py",
    "automation/orchestration/planned_runner/runtime_internal_execution_adapter.py",
    "automation/orchestration/planned_runner/bounded_unattended_acceptance.py",
    "automation/orchestration/planned_runner/long_running_daemon_acceptance.py",
    "automation/orchestration/planned_runner/daemon.py",
    "automation/orchestration/planned_runner/daemon_queue.py",
    "automation/orchestration/planned_runner/daemon_state.py",
    "automation/orchestration/planned_runner/daemon_lock.py",
    "scripts/run_task_queue_daemon.py",
]


@dataclass(frozen=True)
class Criterion:
    id: str
    prompt: str
    field: str
    expected: Any = True


PRE_FINAL_CRITERIA = [
    Criterion("browser_to_codex_handoff_works", "prompt660c", "real_browser_chatgpt_artifact_used"),
    Criterion("response_envelope_validation_works", "prompt660c", "response_envelope_validated"),
    Criterion("analysis_artifact_normalization_works", "prompt660c", "analysis_artifact_normalized"),
    Criterion("prompt657_validation_compatibility_works", "prompt660c", "prompt657_validation_compatibility_verified"),
    Criterion("prompt655_batch_conversion_works", "prompt660c", "prompt655_batch_conversion_compatibility_verified"),
    Criterion("next_prompt_selection_works", "prompt661a", "next_prompt_selection_verified"),
    Criterion("internal_codex_executor_used", "prompt662", "internal_codex_executor_used"),
    Criterion("bounded_multi_cycle_internal_executor_works", "prompt662", "bounded_runner_implemented"),
    Criterion("daemon_hardening_works", "prompt663", "bounded_runner_daemon_wrapped"),
    Criterion("durable_run_id_state_queue_lock_evidence_works", "prompt663", "durable_state_supported"),
    Criterion("stale_lock_handling_works", "prompt663", "stale_lock_handling_verified"),
    Criterion("resume_after_interruption_works", "prompt663", "resume_after_interruption_verified"),
    Criterion("long_running_daemon_acceptance_works", "prompt664", "long_running_daemon_acceptance_implemented"),
    Criterion("bounded_unattended_acceptance_works", "prompt665", "unattended_acceptance_implemented"),
    Criterion("preapproved_local_safe_queue_required", "prompt665", "preapproved_queue_required"),
    Criterion("missing_approval_blocks_execution", "prompt665", "missing_approval_blocks_execution"),
    Criterion("no_human_intervention_during_bounded_run", "prompt665", "no_human_intervention_during_run_verified"),
    Criterion("internal_executor_safety_gate_verified", "prompt665", "internal_executor_safety_gate_verified"),
    Criterion("unsafe_queue_items_rejected", "prompt665", "unsafe_queue_item_rejected"),
    Criterion("operator_stop_honored", "prompt665", "operator_stop_verified"),
    Criterion("failure_threshold_enforced", "prompt665", "failure_threshold_stop_verified"),
    Criterion("max_item_tick_cycle_bounds_enforced", "prompt665", "max_items_or_ticks_or_cycles_enforced"),
    Criterion("terminal_state_recorded", "prompt665", "terminal_state_recorded"),
    Criterion("stop_reason_recorded", "prompt665", "stop_reason_recorded"),
    Criterion("final_evidence_summary_written", "prompt665", "final_evidence_summary_written"),
    Criterion("local_only_restrictions_preserved", "prompt665", "local_only_evidence_captured"),
    Criterion("remote_actions_blocked", "prompt665", "remote_actions_blocked"),
    Criterion("destructive_actions_blocked", "prompt665", "destructive_actions_blocked"),
    Criterion("credential_access_storage_prevented", "prompt665", "credential_storage_prevented"),
    Criterion("cookie_access_prevented", "prompt665", "cookie_access_prevented"),
    Criterion("browser_profile_access_prevented", "prompt665", "browser_profile_access_prevented"),
    Criterion("env_value_access_prevented", "prompt665", "env_value_access_prevented"),
    Criterion("tests_passed", "prompt665", "tests_passed"),
    Criterion("node_checks_passed", "prompt665", "node_checks_passed"),
    Criterion("final_project_level_audit_report_can_be_produced", "prompt665", "reports_written"),
]

FINAL_E2E_CRITERION = "final_end_to_end_unattended_project_run_not_yet_proven"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_json(path: Path) -> tuple[dict[str, Any], str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return {}, f"unreadable: {exc}"
    except json.JSONDecodeError as exc:
        return {}, f"invalid_json: {exc}"
    return (payload if isinstance(payload, dict) else {}), ""


def _tag_exists(repo_root: Path, tag: str) -> bool:
    completed = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def _value_matches(value: Any, expected: Any) -> bool:
    if expected is True:
        return value is True
    return value == expected


def _all_true(payload: Mapping[str, Any], fields: list[str]) -> bool:
    return all(payload.get(field) is True for field in fields)


def _summary(payload: Mapping[str, Any]) -> str:
    lines = [
        "# Prompt666 Project-Level Autonomy Completion Gate",
        "",
        f"- status: {payload.get('status')}",
        f"- readiness_for_prompt667: {payload.get('readiness_for_prompt667')}",
        f"- project_level_autonomy_complete: {payload.get('project_level_autonomy_complete')}",
        f"- missing_completion_criteria_count: {payload.get('missing_completion_criteria_count')}",
        f"- current_capability_boundary_after: {payload.get('current_capability_boundary_after')}",
        "",
        "## Missing Completion Criteria",
    ]
    missing = list(payload.get("missing_completion_criteria", []) or [])
    if missing:
        for item in missing:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines.extend(["", "## Evidence Files Checked"])
    for item in payload.get("evidence_files_checked", []) or []:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def run_project_level_completion_gate(
    *,
    repo_root: str | Path,
    out_dir: str | Path,
    write_reports: bool = True,
) -> dict[str, Any]:
    repo = Path(repo_root)
    output = Path(out_dir)
    reports: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    evidence_files_checked: list[str] = []
    tags_checked: list[str] = []

    for prompt_id, spec in PROMPT_EVIDENCE.items():
        report_path = repo / spec["report"]
        evidence_files_checked.append(spec["report"])
        report, error = _read_json(report_path)
        if error:
            missing.append(f"{prompt_id}:report:{error}")
        reports[prompt_id] = report
        tag = spec["tag"]
        tags_checked.append(tag)
        if not _tag_exists(repo, tag):
            missing.append(f"{prompt_id}:tag_missing:{tag}")

    for surface in REQUIRED_SURFACES:
        if not (repo / surface).is_file():
            missing.append(f"implementation_surface_missing:{surface}")

    criteria_results: dict[str, bool] = {}
    for criterion in PRE_FINAL_CRITERIA:
        actual = reports.get(criterion.prompt, {}).get(criterion.field)
        passed = _value_matches(actual, criterion.expected)
        criteria_results[criterion.id] = passed
        if not passed:
            missing.append(
                f"{criterion.id}:expected_{criterion.field}={criterion.expected!r}:actual={actual!r}"
            )

    prompt665 = reports.get("prompt665", {})
    if prompt665.get("project_level_autonomy_complete") is True:
        missing.append("fake_project_level_autonomy_complete_true_without_final_e2e_evidence")
        fake_completion_rejected = True
    else:
        fake_completion_rejected = True

    if FINAL_E2E_CRITERION not in missing:
        missing.append(FINAL_E2E_CRITERION)

    browser_to_codex = all(
        criteria_results.get(item, False)
        for item in [
            "browser_to_codex_handoff_works",
            "response_envelope_validation_works",
            "analysis_artifact_normalization_works",
            "prompt657_validation_compatibility_works",
            "prompt655_batch_conversion_works",
            "next_prompt_selection_works",
        ]
    )
    internal_executor = all(
        criteria_results.get(item, False)
        for item in [
            "internal_codex_executor_used",
            "bounded_multi_cycle_internal_executor_works",
            "internal_executor_safety_gate_verified",
        ]
    )
    daemon = all(
        criteria_results.get(item, False)
        for item in [
            "daemon_hardening_works",
            "durable_run_id_state_queue_lock_evidence_works",
            "stale_lock_handling_works",
            "resume_after_interruption_works",
            "long_running_daemon_acceptance_works",
        ]
    )
    unattended = all(
        criteria_results.get(item, False)
        for item in [
            "bounded_unattended_acceptance_works",
            "preapproved_local_safe_queue_required",
            "missing_approval_blocks_execution",
            "no_human_intervention_during_bounded_run",
            "unsafe_queue_items_rejected",
            "operator_stop_honored",
            "failure_threshold_enforced",
            "max_item_tick_cycle_bounds_enforced",
            "terminal_state_recorded",
            "stop_reason_recorded",
            "final_evidence_summary_written",
        ]
    )
    safety = all(
        criteria_results.get(item, False)
        for item in [
            "local_only_restrictions_preserved",
            "remote_actions_blocked",
            "destructive_actions_blocked",
            "credential_access_storage_prevented",
            "cookie_access_prevented",
            "browser_profile_access_prevented",
            "env_value_access_prevented",
        ]
    )

    pre_final_missing = [item for item in missing if item != FINAL_E2E_CRITERION]
    readiness_for_prompt667 = not pre_final_missing
    project_level_autonomy_complete = False
    result = {
        "schema_version": "project_level_completion_gate_v1",
        "status": "success" if readiness_for_prompt667 else "blocked",
        "generated_at": _utc_now(),
        "readiness_for_prompt667": readiness_for_prompt667,
        "project_level_autonomy_complete": project_level_autonomy_complete,
        "missing_completion_criteria": missing,
        "missing_completion_criteria_count": len(missing),
        "pre_final_missing_criteria": pre_final_missing,
        "evidence_files_checked": evidence_files_checked,
        "tags_checked": tags_checked,
        "implementation_surfaces_checked": REQUIRED_SURFACES,
        "criteria_results": criteria_results,
        "safety_invariants_verified": safety,
        "unattended_invariants_verified": unattended,
        "daemon_invariants_verified": daemon,
        "internal_executor_invariants_verified": internal_executor,
        "browser_to_codex_invariants_verified": browser_to_codex,
        "fake_completion_rejected": fake_completion_rejected,
        "current_capability_boundary_after": "project_level_autonomy_completion_gate_proven",
        "next_recommended_action": (
            "continue_to_end_to_end_unattended_project_run_acceptance"
            if readiness_for_prompt667
            else "manual_review_required"
        ),
    }
    if write_reports:
        _write_json(output / "project_level_completion_gate_report.json", result)
        _write_text(output / "project_level_completion_gate_summary.md", _summary(result))
    return result


__all__ = [
    "FINAL_E2E_CRITERION",
    "PRE_FINAL_CRITERIA",
    "PROMPT_EVIDENCE",
    "run_project_level_completion_gate",
]
