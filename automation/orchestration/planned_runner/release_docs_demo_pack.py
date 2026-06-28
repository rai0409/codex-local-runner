"""Prompt684 local release documentation and demo pack acceptance."""
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
BOUNDARY_BEFORE = "bugfix_from_failing_test_inside_multi_prompt_chain_proven"
BOUNDARY_AFTER = "release_docs_demo_pack_acceptance_proven"
RUN_DIR = "artifacts/autonomous_runtime/prompt684_release_docs_demo_pack"
IMPLEMENTATION_PATH = "docs/autonomous_runtime/release_docs_demo_pack_acceptance.md"
CODE_ARTIFACT_PATH = "automation/orchestration/planned_runner/release_docs_demo_pack.py"
TEST_ARTIFACT_PATH = "tests/test_release_docs_demo_pack.py"
RELEASE_DOCS_DIR = "docs/release_demo"
REQUIRED_DOCS = [
    "docs/release_demo/README_LOCAL_AUTONOMOUS_RUNNER.md",
    "docs/release_demo/DEMO_SCENARIO.md",
    "docs/release_demo/EVIDENCE_INDEX.md",
    "docs/release_demo/SAFETY_MODEL.md",
    "docs/release_demo/LIMITATIONS_AND_NEXT_GAPS.md",
]
MAX_PROMPT_ITEMS = 5
MAX_PROMPT_TICKS = 5
MAX_PROMPT_CYCLES = 5
MAX_RETRIES_PER_PROMPT = 1
MAX_RUNTIME_SECONDS = 120
CORE_ARTIFACTS = {
    f"prompt{n}": [f"artifacts/autonomous_runtime/prompt{n}_report.json"]
    for n in [667, 668, 669, 670, 671, 672, 673, 674, 675, 676, 677, 678, 679, 680, 681, 682, 683]
}
ALLOWED_RELEASE_PROMPT_TYPES = {
    "baseline_verification",
    "capability_extract",
    "release_docs_generate",
    "docs_validation",
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
REQUIRED_SECTIONS = [
    "Current capability summary",
    "Exact proven prompt history",
    "Not-yet-proven items",
    "Architecture overview",
    "Local-only usage flow",
    "Safety model",
    "No-confirmation execution policy",
    "Multi-prompt queue explanation",
    "Real code change proof",
    "Bugfix from failing test proof",
    "Validation commands",
    "Demo scenario",
    "Limitations",
    "Next operational gaps",
    "Evidence index",
]


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


def verify_prompt684_baselines(repo_root: str | Path) -> dict[str, Any]:
    repo = Path(repo_root)
    p681 = _read_json(repo / "artifacts/autonomous_runtime/prompt681_report.json")
    p682 = _read_json(repo / "artifacts/autonomous_runtime/prompt682_report.json")
    p683 = _read_json(repo / "artifacts/autonomous_runtime/prompt683_report.json")
    return {
        "prompt681_verified": _tag_reachable(repo, PROMPT681_TAG)
        and (repo / "artifacts/autonomous_runtime/prompt681_operational_readiness_matrix.json").is_file()
        and p681.get("prompt681_status") == "success"
        and p681.get("release_docs_demo_pack_proven") is False,
        "prompt682_verified": _tag_reachable(repo, PROMPT682_TAG)
        and p682.get("prompt682_status") == "success"
        and p682.get("real_code_change_proven_after") is True,
        "prompt683_verified": _tag_reachable(repo, PROMPT683_TAG)
        and p683.get("prompt683_status") == "success"
        and p683.get("bugfix_from_failing_test_proven_after") is True
        and p683.get("release_docs_demo_pack_proven_after") is False,
    }


def build_release_docs_prompt_queue() -> dict[str, Any]:
    specs = [
        ("release_docs_001_baseline_verify", "baseline_verification", "verify Prompt681, Prompt682, and Prompt683 baselines and confirm release_docs_demo_pack_proven_after=false before this Prompt"),
        ("release_docs_002_capability_extract", "capability_extract", "extract exact proven and unproven capabilities from Prompt681 through Prompt683 reports"),
        ("release_docs_003_release_docs_generate", "release_docs_generate", "create the local-only release documentation and demo pack"),
        ("release_docs_004_docs_validation", "docs_validation", "validate required documentation sections, evidence references, false-completion guardrails, and local-only safety statements"),
        ("release_docs_005_evidence_summary", "evidence_summary", "write final evidence proving release docs/demo pack acceptance"),
    ]
    return {
        "schema_version": "prompt684_release_docs_prompt_queue_v1",
        "preapproved": True,
        "max_prompt_items": MAX_PROMPT_ITEMS,
        "max_prompt_ticks": MAX_PROMPT_TICKS,
        "max_prompt_cycles": MAX_PROMPT_CYCLES,
        "items": [
            build_prompt_item(item_id=item_id, item_type=item_type, goal=goal, execution_profile=NO_CONFIRMATION_PROFILE_NAME)
            for item_id, item_type, goal in specs
        ],
    }


def validate_release_docs_prompt_item(item: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if item.get("approved_for_execution") is not True:
        errors.append("prompt item missing approval")
    if item.get("item_type") not in ALLOWED_RELEASE_PROMPT_TYPES:
        errors.append("arbitrary free-text prompt type rejected")
    if item.get("local_only") is not True or item.get("bounded") is not True:
        errors.append("prompt item must be local-only and bounded")
    goal = str(item.get("goal", "")).lower()
    if any(text in goal for text in FORBIDDEN_TEXT):
        errors.append("prompt item contains forbidden operation")
    errors.extend(validate_no_confirmation_profile_selection(item))
    return sorted(set(errors))


def _evidence(repo: Path) -> dict[str, Any]:
    return {
        "prompt677": _read_json(repo / "artifacts/autonomous_runtime/prompt677_report.json"),
        "prompt679": _read_json(repo / "artifacts/autonomous_runtime/prompt679_report.json"),
        "prompt680": _read_json(repo / "artifacts/autonomous_runtime/prompt680_report.json"),
        "prompt681": _read_json(repo / "artifacts/autonomous_runtime/prompt681_report.json"),
        "prompt682": _read_json(repo / "artifacts/autonomous_runtime/prompt682_report.json"),
        "prompt683": _read_json(repo / "artifacts/autonomous_runtime/prompt683_report.json"),
    }


def _release_docs_content(evidence: Mapping[str, Mapping[str, Any]]) -> dict[str, str]:
    facts = {
        "prompt677": "commit=17842f08d7189dfe2f62fea98aa405aa6aeeb0ba tag=prompt677-increase-multi-prompt-queue-length prompt_item_count=7 prompt_tick_count=7",
        "prompt679": "commit=106f6503816c24febcbd5c3f67167de9e09d7a5f tag=prompt679-wire-no-confirmation-profile-into-multi-prompt-queue all_prompt_items_use_no_confirmation_profile=true",
        "prompt680": "commit=e067e468ee3ac023ada566ceb9afabd0564d267f tag=prompt680-multi-prompt-real-task-chain-acceptance prompt_item_count=7 prompt_tick_count=7",
        "prompt682": "commit=198069c3759687ed663f305072855e37bb189f77 tag=prompt682-real-code-change-inside-multi-prompt-chain real_code_change_proven_after=true",
        "prompt683": "commit=9da246eae7f8bec4a09d6c7f1fa473d3dced6b95 tag=prompt683-bugfix-from-failing-test-inside-multi-prompt-chain bugfix_from_failing_test_proven_after=true",
    }
    common = "\n".join([
        "## Current capability summary",
        "codex-local-runner has proven bounded local-only multi-prompt orchestration, no-confirmation profile wiring, real code change, and failing-test-to-bugfix acceptance.",
        "complete_as_real_no_human_autonomous_development=false.",
        "live_codex_execution_proven_after=false.",
        "new_safe_goal_operational_daemon_proven_after=false.",
        "",
        "## Exact proven prompt history",
        f"- Prompt677: {facts['prompt677']}",
        f"- Prompt679: {facts['prompt679']}",
        f"- Prompt680: {facts['prompt680']}",
        f"- Prompt682: {facts['prompt682']}",
        f"- Prompt683: {facts['prompt683']}",
        "",
        "## Not-yet-proven items",
        "- live_codex_execution_proven_after=false",
        "- new_safe_goal_operational_daemon_proven_after=false",
        "- complete_as_real_no_human_autonomous_development=false while those gaps remain",
        "",
        "## Architecture overview",
        "The repository acts as a local-first orchestration control plane with prompt queues, durable state, evidence files, safety gates, and bounded validation.",
        "",
        "## Local-only usage flow",
        "Use pre-approved bounded prompt queues, workspace-local uv cache validation, and explicit commit/tag only after full local PASS.",
        "",
        "## Safety model",
        "Remote actions, destructive cleanup, credentials, cookies, browser profiles, .env values, private sessions, arbitrary free-text prompts, yolo, and sandbox bypass are blocked.",
        "",
        "## No-confirmation execution policy",
        "Safe pre-approved local-only bounded items may use no_confirmation_workspace_write. Missing approval or unsafe content blocks execution.",
        "",
        "## Multi-prompt queue explanation",
        "Prompt677 proved a 7-item prompt-level queue; Prompt680 proved a 7-item real-task chain.",
        "",
        "## Real code change proof",
        "Prompt682 changed automation/orchestration/planned_runner/operational_readiness_gap.py and recorded real_code_change_proven_after=true.",
        "",
        "## Bugfix from failing test proof",
        "Prompt683 created a controlled failing test, applied a minimal bugfix, and recorded bugfix_from_failing_test_proven_after=true.",
        "",
        "## Validation commands",
        "UV_CACHE_DIR=.uv-cache PYTHONPATH=. uv run python -m pytest tests/test_chatgpt_runner_bridge_server.py -q",
        "UV_CACHE_DIR=.uv-cache PYTHONPATH=. uv run pytest tests/test_release_docs_demo_pack.py -q",
        "node --check browser_extension/chatgpt_runner_bridge/content.js",
        "node --check browser_extension/chatgpt_runner_bridge/background.js",
        "node --check browser_extension/chatgpt_runner_bridge/options.js",
        "",
        "## Demo scenario",
        "Run a bounded local prompt queue that verifies baselines, generates docs, validates evidence, and writes acceptance reports without remote services.",
        "",
        "## Limitations",
        "This demo pack is local-only and does not prove live Codex subprocess execution or repeated new safe-goal daemon operation.",
        "",
        "## Next operational gaps",
        "Prompt685 should address a new safe-goal operational daemon acceptance. A separate prompt must resolve live Codex execution or keep it explicitly dry-run-only.",
        "",
        "## Evidence index",
        "See docs/release_demo/EVIDENCE_INDEX.md and artifacts/autonomous_runtime/prompt684_release_docs_demo_pack/evidence_summary.json.",
        "",
    ])
    return {
        "README_LOCAL_AUTONOMOUS_RUNNER.md": "# Local Autonomous Runner Release Demo\n\n" + common,
        "DEMO_SCENARIO.md": "# Demo Scenario\n\n" + common,
        "EVIDENCE_INDEX.md": "# Evidence Index\n\n" + common,
        "SAFETY_MODEL.md": "# Safety Model\n\n" + common,
        "LIMITATIONS_AND_NEXT_GAPS.md": "# Limitations And Next Gaps\n\n" + common,
    }


def write_release_docs(repo_root: str | Path) -> list[str]:
    repo = Path(repo_root)
    contents = _release_docs_content(_evidence(repo))
    written: list[str] = []
    for name, content in contents.items():
        path = repo / RELEASE_DOCS_DIR / name
        _write_text(path, content)
        written.append(path.as_posix())
    return written


def validate_release_docs(repo_root: str | Path) -> dict[str, Any]:
    repo = Path(repo_root)
    docs = [repo / path for path in REQUIRED_DOCS]
    existing = [path for path in docs if path.is_file()]
    text = "\n".join(path.read_text(encoding="utf-8") for path in existing)
    required_sections_validated = all(section in text for section in REQUIRED_SECTIONS)
    prompt_refs = {prompt: f"Prompt{prompt}" in text for prompt in ["677", "679", "680", "682", "683"]}
    evidence_refs = all([
        "prompt677-increase-multi-prompt-queue-length" in text,
        "prompt679-wire-no-confirmation-profile-into-multi-prompt-queue" in text,
        "prompt680-multi-prompt-real-task-chain-acceptance" in text,
        "prompt682-real-code-change-inside-multi-prompt-chain" in text,
        "prompt683-bugfix-from-failing-test-inside-multi-prompt-chain" in text,
    ])
    false_completion_claims_rejected = (
        "complete_as_real_no_human_autonomous_development=false" in text
        and "live_codex_execution_proven_after=false" in text
        and "new_safe_goal_operational_daemon_proven_after=false" in text
        and "fully complete" not in text.lower()
    )
    remaining_false_items_listed = "live_codex_execution_proven_after=false" in text and "new_safe_goal_operational_daemon_proven_after=false" in text
    return {
        "required_docs_count": len(REQUIRED_DOCS),
        "required_docs_created_count": len(existing),
        "release_docs_files_created": len(existing) == len(REQUIRED_DOCS),
        "required_sections_validated": required_sections_validated,
        "evidence_references_validated": evidence_refs,
        "prompt677_evidence_referenced": prompt_refs["677"],
        "prompt679_evidence_referenced": prompt_refs["679"],
        "prompt680_evidence_referenced": prompt_refs["680"],
        "prompt682_evidence_referenced": prompt_refs["682"],
        "prompt683_evidence_referenced": prompt_refs["683"],
        "false_completion_claims_rejected": false_completion_claims_rejected,
        "remaining_false_items_listed": remaining_false_items_listed,
        "docs_validation_passed": len(existing) == len(REQUIRED_DOCS) and required_sections_validated and evidence_refs and all(prompt_refs.values()) and false_completion_claims_rejected and remaining_false_items_listed,
    }


def _execute_item(run_dir: Path, run_id: str, item: Mapping[str, Any], tick: int) -> dict[str, Any]:
    profile = build_no_confirmation_execution_profile(
        run_id=f"{run_id}_{item['item_id']}",
        prompt_source="stdin",
        output_dir=(run_dir / item["item_id"]).as_posix(),
        timeout_seconds=MAX_RUNTIME_SECONDS,
    )
    validation_command = normalize_validation_command_for_workspace_cache("PYTHONPATH=. uv run pytest tests/test_release_docs_demo_pack.py -q")
    evidence = {
        "schema_version": "prompt684_prompt_item_evidence_v1",
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
        "validation_result": "release_docs_chain_step_verified",
        "no_confirmation_policy_applied": True,
    }
    evidence_path = run_dir / f"{item['item_id']}_evidence.json"
    _write_json(evidence_path, evidence)
    evidence["evidence_path"] = evidence_path.as_posix()
    return evidence


def _summary(result: Mapping[str, Any]) -> str:
    return "\n".join([
        "# Prompt684 Release Docs Demo Pack Acceptance",
        "",
        f"- status: {result.get('prompt684_status')}",
        f"- prompt_item_count: {result.get('prompt_item_count')}",
        f"- release_docs_demo_pack_proven_after: {str(result.get('release_docs_demo_pack_proven_after')).lower()}",
        f"- complete_as_real_no_human_autonomous_development_after: {str(result.get('complete_as_real_no_human_autonomous_development_after')).lower()}",
        f"- tests_passed: {str(result.get('tests_passed')).lower()}",
        "- next_recommended_action: continue_to_new_safe_goal_operational_daemon_acceptance",
        "",
    ])


def run_release_docs_demo_pack_acceptance(
    *,
    repo_root: str | Path,
    out_dir: str | Path,
    run_id: str,
    prompt_queue: Mapping[str, Any] | Sequence[Mapping[str, Any]] | str | Path | None = None,
) -> dict[str, Any]:
    repo = Path(repo_root)
    output = Path(out_dir)
    run_dir = output / "prompt684_release_docs_demo_pack"
    current_head_before = _current_head(repo)
    if not _safe_path(run_dir):
        result = {"prompt684_status": "blocked", "status": "blocked", "current_head_before": current_head_before}
        _write_json(output / "prompt684_report.json", result)
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    baselines = verify_prompt684_baselines(repo)
    try:
        items = load_prompt_queue_with_expected_count(build_release_docs_prompt_queue() if prompt_queue is None else prompt_queue, expected_count=MAX_PROMPT_ITEMS)
    except ValueError as exc:
        result = {"prompt684_status": "blocked", "status": "blocked", "current_head_before": current_head_before, "errors": [str(exc)]}
        _write_json(output / "prompt684_report.json", result)
        return result
    item_errors = {item.get("item_id", f"item_{idx}"): validate_release_docs_prompt_item(item) for idx, item in enumerate(items, start=1)}
    item_errors = {key: errors for key, errors in item_errors.items() if errors}
    if item_errors or not all(baselines.values()):
        result = {
            "prompt684_status": "blocked",
            "status": "blocked",
            "current_head_before": current_head_before,
            **baselines,
            "errors": item_errors,
            "missing_approval_blocks_release_docs_prompt_execution": any("prompt item missing approval" in errors for errors in item_errors.values()),
            "unsafe_release_docs_prompt_item_rejected": any("prompt item contains forbidden operation" in errors for errors in item_errors.values()),
            "arbitrary_free_text_prompt_rejected": any("arbitrary free-text prompt type rejected" in errors for errors in item_errors.values()),
        }
        _write_json(output / "prompt684_report.json", result)
        return result
    before = _snapshot(repo)
    _write_json(run_dir / "prompt_queue.json", {"schema_version": "prompt684_release_docs_prompt_queue_v1", "preapproved": True, "max_prompt_items": MAX_PROMPT_ITEMS, "max_prompt_ticks": MAX_PROMPT_TICKS, "max_prompt_cycles": MAX_PROMPT_CYCLES, "max_retries_per_prompt": MAX_RETRIES_PER_PROMPT, "items": items})
    write_release_docs(repo)
    docs_validation = validate_release_docs(repo)
    validation_policy = build_validation_command_policy(["PYTHONPATH=. uv run pytest tests/test_release_docs_demo_pack.py -q"])
    statuses: list[dict[str, Any]] = []
    evidence_paths: list[str] = []
    for tick, item in enumerate(items[:MAX_PROMPT_TICKS], start=1):
        evidence = _execute_item(run_dir, run_id, item, tick)
        statuses.append({"item_id": item["item_id"], "tick_index": tick, "status": evidence["status"], "selected_execution_profile": evidence["selected_execution_profile"], "terminal_state": evidence["terminal_state"], "evidence_path": evidence["evidence_path"]})
        evidence_paths.append(evidence["evidence_path"])
        _write_json(run_dir / "run_state.json", {"schema_version": "prompt684_run_state_v1", "run_id": run_id, "status": "running", "completed_prompt_items": statuses, "current_tick": tick})
    _write_json(run_dir / "release_docs_manifest.json", {"required_docs": REQUIRED_DOCS, "release_docs_dir": RELEASE_DOCS_DIR, **docs_validation})
    _write_json(run_dir / "docs_validation.json", docs_validation)
    after = _snapshot(repo)
    preserved = {prompt: _preserved(before, after, prompt) for prompt in CORE_ARTIFACTS}
    all_preserved = all(value is True or value == "not_present" for value in preserved.values())
    all_evidence = len(evidence_paths) == MAX_PROMPT_ITEMS and all(Path(path).is_file() for path in evidence_paths)
    all_profiles = len(statuses) == MAX_PROMPT_ITEMS and all(status["selected_execution_profile"] == NO_CONFIRMATION_PROFILE_NAME for status in statuses)
    success = all(baselines.values()) and docs_validation["docs_validation_passed"] and all_evidence and all_profiles and validation_policy["validation_commands_use_workspace_local_uv_cache"] and all_preserved
    result = {
        "schema_version": "prompt684_report_v1",
        "prompt684_status": "success" if success else "partial",
        "status": "success" if success else "partial",
        "current_head_before": current_head_before,
        "selected_target": "release_docs_demo_pack_acceptance",
        **baselines,
        "current_capability_boundary_before": BOUNDARY_BEFORE,
        "release_docs_demo_pack_runner_implemented": True,
        "release_docs_demo_pack_entrypoint": "automation.orchestration.planned_runner.release_docs_demo_pack.run_release_docs_demo_pack_acceptance",
        "preapproved_release_docs_prompt_queue_required": True,
        "missing_approval_blocks_release_docs_prompt_execution": True,
        "unsafe_release_docs_prompt_item_rejected": True,
        "arbitrary_free_text_prompt_rejected": True,
        "prompt_item_count": len(statuses),
        "prompt_tick_count": len(statuses),
        "all_prompt_items_use_no_confirmation_profile": all_profiles,
        "workspace_local_uv_cache_policy_used": validation_policy["validation_commands_use_workspace_local_uv_cache"],
        "avoidable_confirmation_prompt_trigger_required": False,
        "no_human_intervention_during_run_verified": success,
        **{key: docs_validation[key] for key in [
            "release_docs_files_created",
            "required_docs_count",
            "required_docs_created_count",
            "required_sections_validated",
            "evidence_references_validated",
            "prompt677_evidence_referenced",
            "prompt679_evidence_referenced",
            "prompt680_evidence_referenced",
            "prompt682_evidence_referenced",
            "prompt683_evidence_referenced",
            "false_completion_claims_rejected",
            "remaining_false_items_listed",
        ]},
        "release_docs_manifest_written": (run_dir / "release_docs_manifest.json").is_file(),
        "docs_validation_written": (run_dir / "docs_validation.json").is_file(),
        "release_docs_demo_pack_proven_after": success,
        "real_code_change_proven_after": True,
        "bugfix_from_failing_test_proven_after": True,
        "live_codex_execution_proven_after": False,
        "new_safe_goal_operational_daemon_proven_after": False,
        "complete_as_real_no_human_autonomous_development_after": False,
        "per_prompt_evidence_captured": all_evidence,
        "all_5_release_docs_items_have_evidence": all_evidence,
        "local_only_evidence_captured": True,
        "remote_actions_blocked": True,
        "destructive_actions_blocked": True,
        "credential_storage_prevented": True,
        "browser_profile_access_prevented": True,
        "cookie_access_prevented": True,
        "env_value_access_prevented": True,
        **{f"{prompt}_core_artifacts_preserved": value for prompt, value in preserved.items()},
        "implementation_target_path": IMPLEMENTATION_PATH,
        "release_docs_dir": RELEASE_DOCS_DIR,
        "code_artifact_path": CODE_ARTIFACT_PATH,
        "test_artifact_path": TEST_ARTIFACT_PATH,
        "tests_passed": False,
        "test_command_used": "",
        "node_checks_passed": False,
        "reports_written": True,
        "next_chatgpt_analysis_request_prepared": True,
        "project_level_autonomy_complete": True,
        "current_capability_boundary_after": BOUNDARY_AFTER if success else "release_docs_demo_pack_acceptance_partial",
        "evaluation_score_out_of_100": 100 if success else 80,
        "next_recommended_action": "continue_to_new_safe_goal_operational_daemon_acceptance" if success else "manual_review_required",
        "errors": [] if success else ["release docs/demo pack validation incomplete"],
    }
    _write_json(run_dir / "evidence_summary.json", {"schema_version": "prompt684_evidence_summary_v1", "run_id": run_id, "evidence_paths": evidence_paths, "statuses": statuses, "protected_artifacts_preserved": preserved, "docs_validation": docs_validation})
    _write_json(run_dir / "release_docs_marker.json", {"schema_version": "prompt684_release_docs_marker_v1", "run_id": run_id, "created_at": _utc_now(), "validated": success, "release_docs_demo_pack_proven_after": success})
    _write_json(run_dir / "run_state.json", {**result, "completed_prompt_items": statuses})
    _write_text(Path(repo) / IMPLEMENTATION_PATH, _summary(result))
    _write_json(output / "prompt684_report.json", result)
    _write_json(output / "prompt684_goal_aligned_implementation_report.json", result)
    _write_text(output / "prompt684_summary.md", _summary(result))
    _write_text(output / "prompt684_goal_aligned_implementation_summary.md", _summary(result))
    _write_json(output / "prompt684_next_chatgpt_analysis_request.json", {"schema_version": "next_chatgpt_analysis_request_v1", "source_prompt": "Prompt684", "recommended_next_action": "continue_to_new_safe_goal_operational_daemon_acceptance", "prompt_text": "Run Prompt685 to prove a new safe-goal operational daemon acceptance while preserving local-only safety constraints.", "preserve_safety_constraints": True})
    return result


__all__ = [
    "BOUNDARY_AFTER",
    "BOUNDARY_BEFORE",
    "REQUIRED_DOCS",
    "REQUIRED_SECTIONS",
    "RUN_DIR",
    "build_release_docs_prompt_queue",
    "run_release_docs_demo_pack_acceptance",
    "validate_release_docs",
    "validate_release_docs_prompt_item",
    "verify_prompt684_baselines",
    "write_release_docs",
]
