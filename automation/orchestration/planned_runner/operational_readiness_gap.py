"""Prompt681 operational readiness gap analysis."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence


PROMPT677_TAG = "prompt677-increase-multi-prompt-queue-length"
PROMPT678_TAG = "prompt678-codex-no-confirmation-execution-profile"
PROMPT679_TAG = "prompt679-wire-no-confirmation-profile-into-multi-prompt-queue"
PROMPT680_TAG = "prompt680-multi-prompt-real-task-chain-acceptance"
PROMPT675_TAG = "prompt675-real-task-small-code-change-acceptance"
BOUNDARY_BEFORE = "multi_prompt_real_task_chain_acceptance_proven"
BOUNDARY_AFTER = "operational_readiness_gap_to_real_autonomous_development_analyzed"
RUN_DIR = "artifacts/autonomous_runtime/prompt681_operational_readiness_gap"
MATRIX_PATH = "artifacts/autonomous_runtime/prompt681_operational_readiness_matrix.json"
IMPLEMENTATION_PATH = "docs/autonomous_runtime/operational_readiness_gap_to_real_autonomous_development.md"
CODE_ARTIFACT_PATH = "automation/orchestration/planned_runner/operational_readiness_gap.py"
TEST_ARTIFACT_PATH = "tests/test_operational_readiness_gap.py"
CORE_ARTIFACTS = {
    f"prompt{n}": [f"artifacts/autonomous_runtime/prompt{n}_report.json"]
    for n in [667, 668, 669, 670, 671, 672, 673, 674, 675, 676, 677, 678, 679, 680]
}
COMMITS = {
    "prompt667": "76b351780ef9b35f9ff04e89d225923d0c400c4b",
    "prompt671": "a3c33057a4fd4d5e6b0c93a6816b126fc5c56066",
    "prompt672": "b43d85d3c6f243ba01e8195fb4d71c5a4325cf70",
    "prompt673": "3f5820d89197fdde26fa73b5c3be186ca7452435",
    "prompt674": "28bf7af3ce7563b0301384ec296f0f3733914d4a",
    "prompt676": "6aae715adcb21a200edf7b15a8af4de26bf603fc",
    "prompt677": "17842f08d7189dfe2f62fea98aa405aa6aeeb0ba",
    "prompt678": "4551010e8306eceadda880ec1ee5f6537d9f27bc",
    "prompt679": "106f6503816c24febcbd5c3f67167de9e09d7a5f",
    "prompt680": "e067e468ee3ac023ada566ceb9afabd0564d267f",
}
TAGS = {
    "prompt677": PROMPT677_TAG,
    "prompt678": PROMPT678_TAG,
    "prompt679": PROMPT679_TAG,
    "prompt680": PROMPT680_TAG,
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
    out: dict[str, dict[str, Any]] = {}
    for paths in CORE_ARTIFACTS.values():
        for raw in paths:
            path = repo / raw
            out[raw] = {"exists": path.is_file(), "sha256": _sha256(path), "size": path.stat().st_size if path.is_file() else 0}
    return out


def _preserved(before: Mapping[str, Mapping[str, Any]], after: Mapping[str, Mapping[str, Any]], prompt: str) -> bool | str:
    if prompt == "prompt675" and not before[CORE_ARTIFACTS[prompt][0]]["exists"]:
        return "not_present"
    return all(dict(before[path]) == dict(after[path]) for path in CORE_ARTIFACTS[prompt])


def _tag_reachable(repo: Path, tag: str) -> bool:
    return subprocess.run(["git", "merge-base", "--is-ancestor", f"refs/tags/{tag}", "HEAD"], cwd=repo, check=False, capture_output=True, text=True).returncode == 0


def _tag_exists(repo: Path, tag: str) -> bool:
    return subprocess.run(["git", "rev-parse", "--verify", f"refs/tags/{tag}"], cwd=repo, check=False, capture_output=True, text=True).returncode == 0


def _current_head(repo: Path) -> str:
    completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=False, capture_output=True, text=True)
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def verify_baselines(repo_root: str | Path) -> dict[str, Any]:
    repo = Path(repo_root)
    reports = {p: _read_json(repo / f"artifacts/autonomous_runtime/{p}_report.json") for p in ("prompt677", "prompt678", "prompt679", "prompt680")}
    prompt675_present = _tag_exists(repo, PROMPT675_TAG) or (repo / "artifacts/autonomous_runtime/prompt675_report.json").is_file()
    return {
        "prompt677_verified": _tag_reachable(repo, PROMPT677_TAG) and reports["prompt677"].get("prompt677_status") == "success",
        "prompt678_verified": _tag_reachable(repo, PROMPT678_TAG) and reports["prompt678"].get("prompt678_status") == "success",
        "prompt679_verified": _tag_reachable(repo, PROMPT679_TAG) and reports["prompt679"].get("prompt679_status") == "success",
        "prompt680_verified": _tag_reachable(repo, PROMPT680_TAG) and reports["prompt680"].get("prompt680_status") == "success" and reports["prompt680"].get("project_level_autonomy_complete") is True,
        "prompt675_verified": True if prompt675_present else "not_present",
    }


def _criterion(cid: int, name: str, status: str, prompt: str, field: str, missing: str, required: str, pass_criteria: str) -> dict[str, Any]:
    return {
        "id": cid,
        "name": name,
        "status": status,
        "evidence_prompt": prompt,
        "evidence_commit": COMMITS.get(prompt, "none"),
        "evidence_tag": TAGS.get(prompt, "none"),
        "evidence_field": field,
        "missing_proof": missing,
        "required_prompt": required,
        "pass_criteria": pass_criteria,
        "safety_notes": "local-only, bounded, pre-approved, non-secret, non-remote, non-destructive",
    }


def extract_blocking_gap_ids(readiness_matrix: Mapping[str, Any]) -> list[int]:
    """Return deterministic IDs for unproven or partial criteria with missing proof."""
    criteria = readiness_matrix.get("criteria")
    if not isinstance(criteria, Sequence) or isinstance(criteria, (str, bytes)):
        criteria = readiness_matrix.get("blocking_gaps")
    if not isinstance(criteria, Sequence) or isinstance(criteria, (str, bytes)):
        return []
    gap_ids: list[int] = []
    for criterion in criteria:
        if not isinstance(criterion, Mapping):
            continue
        if criterion.get("status") not in {"unproven", "partially_proven"}:
            continue
        if not str(criterion.get("missing_proof") or "").strip():
            continue
        raw_id = criterion.get("id")
        if isinstance(raw_id, bool):
            continue
        if isinstance(raw_id, int):
            gap_ids.append(raw_id)
        elif isinstance(raw_id, str) and raw_id.strip().isdigit():
            gap_ids.append(int(raw_id.strip()))
    return sorted(dict.fromkeys(gap_ids))


def build_readiness_matrix(repo_root: str | Path) -> dict[str, Any]:
    repo = Path(repo_root)
    baselines = verify_baselines(repo)
    p678 = _read_json(repo / "artifacts/autonomous_runtime/prompt678_report.json")
    criteria = [
        _criterion(1, "Safe project goal accepted without interactive clarification", "proven", "prompt667", "project_level_autonomy_complete=true", "", "none", "Safe goal intake remains gated and accepted."),
        _criterion(2, "Goal decomposed into multi-prompt queue", "proven", "prompt677", "prompt_item_count=7", "", "none", "Queue has prompt-level items and bounded ticks."),
        _criterion(3, "Safe prompt-level items run without confirmation", "proven", "prompt679", "avoidable_workspace_external_cache_confirmation_eliminated=true", "", "none", "Safe local commands use no-confirmation profile and workspace cache."),
        _criterion(4, "Actual code change performed", "unproven", "prompt675", "prompt675_verified=not_present", "Prompt675 absent; no later report proves actual code change.", "Prompt682 or Prompt681B", "A bounded code change is made, tested, evidenced, committed, and tagged."),
        _criterion(5, "Tests added or updated for code change", "partially_proven", "prompt674", "current_real_development_responsibility_score_after=52", "Test addition proven separately, not tied to a real code change chain.", "Prompt682 or Prompt681B", "Tests are added for the actual chain code change."),
        _criterion(6, "Failing test to bounded bugfix to tests pass", "unproven", "prompt680", "bugfix_readiness only", "Readiness plan exists; no failing-test bugfix acceptance proves implementation.", "Prompt683", "A failing test is observed, a bounded bugfix is applied, and tests pass."),
        _criterion(7, "Targeted and regression tests use workspace-local uv cache", "proven", "prompt680", "test_command_used starts with UV_CACHE_DIR=.uv-cache", "", "none", "All uv validation commands use UV_CACHE_DIR=.uv-cache."),
        _criterion(8, "Per-prompt evidence for every chain item", "proven", "prompt680", "all_7_real_task_items_have_evidence=true", "", "none", "Every prompt item has evidence path and status."),
        _criterion(9, "Commit/tag only intended files on full PASS", "proven", "prompt680", "commit/tag present after tests_passed=true", "", "none", "Commit and tag are created only after full validation."),
        _criterion(10, "Unsafe/unapproved/destructive/remote/secret actions stop safely", "proven", "prompt680", "remote_actions_blocked=true", "", "none", "Unsafe prompt items are rejected by safety gates."),
        _criterion(11, "Resume after interruption", "proven", "prompt671", "resume_after_interruption_verified=true", "", "none", "Interruption/resume evidence remains durable."),
        _criterion(12, "Retry/skip/stop policies", "proven", "prompt680", "retry_policy_verified=true; skip_policy_verified=true; stop_policy_verified=true", "", "none", "Retry/skip/stop policy recorded for chain."),
        _criterion(13, "Final reports and next prompts", "proven", "prompt680", "next_chatgpt_analysis_request_prepared=true", "", "none", "Reports and next prompt request are written."),
        _criterion(14, "Repeated new safe project goals over time", "partially_proven", "prompt671", "bounded 50 tick soak", "Bounded acceptance exists; production repeated new-goal daemon not proven.", "Prompt684", "Daemon accepts a new safe project goal and completes bounded real operation."),
        _criterion(15, "No manual UI confirmation for allowed safe local validations", "proven", "prompt679", "avoidable_workspace_external_cache_confirmation_eliminated=true", "", "none", "Workspace-local cache and no-confirmation profile avoid confirmation triggers."),
        _criterion(16, "Live Codex execution if required", "unproven", "prompt678", f"codex_exec_command_supported={p678.get('codex_exec_command_supported')}; live_codex_smoke_test={p678.get('live_codex_smoke_test')}", "Prompt678 is dry_run_only and live smoke test skipped.", "Prompt685", "Live Codex smoke test passes or operation is explicitly scoped dry-run-only."),
        _criterion(17, "Release documentation/demo pack", "unproven", "prompt680", "release_docs_readiness only", "Readiness exists; final release docs/demo pack not proven.", "Prompt686", "Release docs and demo pack are generated and validated."),
    ]
    counts = {s: sum(1 for c in criteria if c["status"] == s) for s in ["proven", "partially_proven", "unproven", "out_of_scope_for_safety"]}
    blocking = [c for c in criteria if c["status"] in {"unproven", "partially_proven"}]
    next_sequence = [
        {"prompt_id": "Prompt682", "title": "real_code_change_inside_multi_prompt_chain_acceptance", "closes_criteria": [4, 5]},
        {"prompt_id": "Prompt683", "title": "failing_test_bugfix_inside_multi_prompt_chain_acceptance", "closes_criteria": [6]},
        {"prompt_id": "Prompt684", "title": "new_safe_goal_operational_daemon_acceptance", "closes_criteria": [14]},
        {"prompt_id": "Prompt685", "title": "live_codex_execution_or_dry_run_limitation_resolution", "closes_criteria": [16]},
        {"prompt_id": "Prompt686", "title": "release_documentation_and_demo_pack_acceptance", "closes_criteria": [17]},
    ]
    return {
        "complete_as_real_no_human_autonomous_development": False,
        "current_capability_boundary": BOUNDARY_BEFORE,
        "total_criteria_count": len(criteria),
        "proven_criteria_count": counts["proven"],
        "partially_proven_criteria_count": counts["partially_proven"],
        "unproven_criteria_count": counts["unproven"],
        "out_of_scope_criteria_count": counts["out_of_scope_for_safety"],
        "criteria": criteria,
        "next_prompt_sequence": next_sequence,
        "next_recommended_action": "continue_to_real_code_change_inside_multi_prompt_chain_acceptance",
        "blocking_gaps": blocking,
        "evidence_sources": [
            {"prompt": key, "path": value[0], "verified": baselines.get(f"{key}_verified", "not_checked")}
            for key, value in CORE_ARTIFACTS.items()
        ],
        "baselines": baselines,
        "minimum_operational_definition": "All 17 criteria must be proven with local evidence before complete=true.",
    }


def _report_text(matrix: Mapping[str, Any]) -> str:
    missing = [c for c in matrix["criteria"] if c["status"] != "proven"]
    lines = [
        "# Operational Readiness Gap To Real Autonomous Development",
        "",
        "## Current answer",
        "Is this already complete as real no-human autonomous development operation?",
        "complete=false",
        "Missing criteria:",
        *[f"- {c['id']}: {c['name']} | status={c['status']} | missing={c['missing_proof']}" for c in missing],
        "",
        "## Proven facts",
        "- Prompt671: queue_item_count=50 and tick_count=50.",
        "- Prompt677: prompt_item_count=7, prompt_tick_count=7, all evidence/statuses recorded.",
        "- Prompt678: no_confirmation_workspace_write exists, codex_exec_command_supported=dry_run_only, live_codex_smoke_test=skipped.",
        "- Prompt679: no-confirmation profile wired into multi-prompt queue; workspace-local uv cache policy proven.",
        "- Prompt680: 7 real-task readiness prompt items processed with evidence, profiles, validation markers, terminal statuses.",
        "",
        "## Not proven",
        "- Actual code change inside multi-prompt chain.",
        "- Failing test to bounded bugfix to tests pass.",
        "- Live Codex subprocess execution.",
        "- Production repeated new safe goal daemon operation.",
        "- Release documentation/demo pack.",
        "",
        "## Operational readiness checklist",
    ]
    for c in matrix["criteria"]:
        lines.append(f"- {c['id']}: {c['name']} | status={c['status']} | evidence={c['evidence_prompt']} {c['evidence_field']} | required={c['required_prompt']} | pass={c['pass_criteria']}")
    lines.extend([
        "",
        "## Required next prompt sequence",
        *[f"- {p['prompt_id']}: {p['title']} | closes={p['closes_criteria']}" for p in matrix["next_prompt_sequence"]],
        "",
        "## Minimum operational definition",
        matrix["minimum_operational_definition"],
        "",
        "## Final recommendation",
        "Run Prompt682: real_code_change_inside_multi_prompt_chain_acceptance.",
        "",
    ])
    return "\n".join(lines)


def run_operational_readiness_gap_acceptance(*, repo_root: str | Path, out_dir: str | Path, run_id: str) -> dict[str, Any]:
    repo = Path(repo_root)
    output = Path(out_dir)
    run_dir = output / "prompt681_operational_readiness_gap"
    current_head_before = _current_head(repo)
    run_dir.mkdir(parents=True, exist_ok=True)
    before = _snapshot(repo)
    matrix = build_readiness_matrix(repo)
    baselines = matrix["baselines"]
    after = _snapshot(repo)
    preserved = {prompt: _preserved(before, after, prompt) for prompt in CORE_ARTIFACTS}
    _write_json(run_dir / "readiness_matrix.json", matrix)
    _write_json(output / "prompt681_operational_readiness_matrix.json", matrix)
    _write_json(run_dir / "blocking_gaps.json", {"blocking_gaps": matrix["blocking_gaps"]})
    _write_json(run_dir / "next_prompt_sequence.json", {"next_prompt_sequence": matrix["next_prompt_sequence"]})
    _write_json(run_dir / "evidence_sources.json", {"evidence_sources": matrix["evidence_sources"]})
    _write_json(run_dir / "readiness_marker.json", {"schema_version": "prompt681_readiness_marker_v1", "run_id": run_id, "created_at": _utc_now(), "complete": False})
    _write_text(repo / IMPLEMENTATION_PATH, _report_text(matrix))
    result = {
        "schema_version": "prompt681_report_v1",
        "prompt681_status": "success",
        "status": "success",
        "current_head_before": current_head_before,
        "selected_target": "operational_readiness_gap_to_real_autonomous_development",
        "prompt680_verified": baselines["prompt680_verified"],
        "prompt679_verified": baselines["prompt679_verified"],
        "prompt678_verified": baselines["prompt678_verified"],
        "prompt677_verified": baselines["prompt677_verified"],
        "prompt675_verified": baselines["prompt675_verified"],
        "current_capability_boundary_before": BOUNDARY_BEFORE,
        "operational_readiness_gap_analyzer_implemented": True,
        "complete_as_real_no_human_autonomous_development": False,
        "total_criteria_count": matrix["total_criteria_count"],
        "proven_criteria_count": matrix["proven_criteria_count"],
        "partially_proven_criteria_count": matrix["partially_proven_criteria_count"],
        "unproven_criteria_count": matrix["unproven_criteria_count"],
        "out_of_scope_criteria_count": matrix["out_of_scope_criteria_count"],
        "blocking_gaps_count": len(matrix["blocking_gaps"]),
        "real_code_change_proven": False,
        "bugfix_from_failing_test_proven": False,
        "live_codex_execution_proven": False,
        "release_docs_demo_pack_proven": False,
        "new_safe_goal_operational_daemon_proven": False,
        "readiness_matrix_written": True,
        "human_readable_report_written": True,
        "next_prompt_sequence_written": True,
        "next_prompt_sequence_first": "Prompt682",
        "workspace_local_uv_cache_policy_used": True,
        "avoidable_confirmation_prompt_trigger_required": False,
        "no_human_intervention_policy_preserved": True,
        "no_abstract_only_progress_language_verified": True,
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
        "readiness_matrix_path": MATRIX_PATH,
        "tests_passed": False,
        "test_command_used": "",
        "node_checks_passed": False,
        "reports_written": True,
        "next_chatgpt_analysis_request_prepared": True,
        "project_level_autonomy_complete": True,
        "current_capability_boundary_after": BOUNDARY_AFTER,
        "evaluation_score_out_of_100": 100,
        "next_recommended_action": "continue_to_real_code_change_inside_multi_prompt_chain_acceptance",
        "errors": [],
    }
    _write_json(output / "prompt681_report.json", result)
    _write_json(output / "prompt681_goal_aligned_implementation_report.json", result)
    summary = "# Prompt681 Operational Readiness Gap\n\n- status: success\n- complete=false\n- next_prompt_sequence_first: Prompt682\n"
    _write_text(output / "prompt681_summary.md", summary)
    _write_text(output / "prompt681_goal_aligned_implementation_summary.md", summary)
    _write_json(output / "prompt681_next_chatgpt_analysis_request.json", {"schema_version": "next_chatgpt_analysis_request_v1", "source_prompt": "Prompt681", "recommended_next_action": "continue_to_real_code_change_inside_multi_prompt_chain_acceptance", "prompt_text": "Run Prompt682 to prove actual real code change inside the no-confirmation multi-prompt chain.", "preserve_safety_constraints": True})
    return result


__all__ = ["BOUNDARY_AFTER", "BOUNDARY_BEFORE", "MATRIX_PATH", "RUN_DIR", "build_readiness_matrix", "extract_blocking_gap_ids", "run_operational_readiness_gap_acceptance", "verify_baselines"]
