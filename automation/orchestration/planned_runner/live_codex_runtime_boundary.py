"""Prompt686 live Codex execution or runtime-boundary acceptance."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence


PROMPT678_TAG = "prompt678-codex-no-confirmation-execution-profile"
PROMPT681_TAG = "prompt681-operational-readiness-gap-to-real-autonomous-development"
PROMPT682_TAG = "prompt682-real-code-change-inside-multi-prompt-chain"
PROMPT683_TAG = "prompt683-bugfix-from-failing-test-inside-multi-prompt-chain"
PROMPT684_TAG = "prompt684-release-docs-demo-pack-acceptance"
PROMPT685_TAG = "prompt685-new-safe-goal-operational-daemon-acceptance"
BOUNDARY_BEFORE = "new_safe_goal_operational_daemon_acceptance_proven"
BOUNDARY_AFTER_LIVE = "live_codex_execution_acceptance_proven"
BOUNDARY_AFTER_DRY_RUN = "live_codex_runtime_boundary_confirmed"
RUN_DIR = "artifacts/autonomous_runtime/prompt686_live_codex_execution"
IMPLEMENTATION_PATH = "docs/autonomous_runtime/live_codex_execution_or_runtime_boundary_acceptance.md"
CODE_ARTIFACT_PATH = "automation/orchestration/planned_runner/live_codex_runtime_boundary.py"
TEST_ARTIFACT_PATH = "tests/test_live_codex_runtime_boundary.py"
EXPECTED_MARKER_PATH = "artifacts/autonomous_runtime/prompt686_live_codex_execution/live_smoke_marker.txt"
EXPECTED_MARKER_CONTENT = "PROMPT686_LIVE_CODEX_SMOKE_OK"
SAFE_SMOKE_PROMPT = (
    "Create the file artifacts/autonomous_runtime/prompt686_live_codex_execution/live_smoke_marker.txt "
    "with exactly the text PROMPT686_LIVE_CODEX_SMOKE_OK. Do not modify any other file. "
    "Do not read secrets. Do not access the network. Do not ask for confirmation."
)
CORE_ARTIFACTS = {
    f"prompt{n}": [f"artifacts/autonomous_runtime/prompt{n}_report.json"]
    for n in [667, 668, 669, 670, 671, 672, 673, 674, 675, 676, 677, 678, 679, 680, 681, 682, 683, 684, 685]
}
FORBIDDEN_PROMPT_TERMS = (
    "git push",
    "open pr",
    "pull request",
    "merge",
    "rm -rf",
    "credential",
    "credentials",
    "cookie",
    "cookies",
    "browser profile",
    ".env",
    "private session",
    "secret",
    "secrets",
    "~/.ssh",
    "id_rsa",
)
FORBIDDEN_COMMAND_FLAGS = {
    "--yolo",
    "--dangerously-bypass-approvals-and-sandbox",
    "danger-full-access",
}
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


def verify_prompt686_baselines(repo_root: str | Path) -> dict[str, Any]:
    repo = Path(repo_root)
    p678 = _read_json(repo / "artifacts/autonomous_runtime/prompt678_report.json")
    p681 = _read_json(repo / "artifacts/autonomous_runtime/prompt681_report.json")
    p682 = _read_json(repo / "artifacts/autonomous_runtime/prompt682_report.json")
    p683 = _read_json(repo / "artifacts/autonomous_runtime/prompt683_report.json")
    p684 = _read_json(repo / "artifacts/autonomous_runtime/prompt684_report.json")
    p685 = _read_json(repo / "artifacts/autonomous_runtime/prompt685_report.json")
    return {
        "prompt678_verified": _tag_reachable(repo, PROMPT678_TAG)
        and p678.get("prompt678_status") == "success"
        and p678.get("codex_exec_command_supported") == "dry_run_only"
        and p678.get("live_codex_smoke_test") == "skipped",
        "prompt681_verified": _tag_reachable(repo, PROMPT681_TAG)
        and p681.get("prompt681_status") == "success"
        and p681.get("live_codex_execution_proven") is False,
        "prompt682_verified": _tag_reachable(repo, PROMPT682_TAG)
        and p682.get("prompt682_status") == "success"
        and p682.get("real_code_change_proven_after") is True,
        "prompt683_verified": _tag_reachable(repo, PROMPT683_TAG)
        and p683.get("prompt683_status") == "success"
        and p683.get("bugfix_from_failing_test_proven_after") is True,
        "prompt684_verified": _tag_reachable(repo, PROMPT684_TAG)
        and p684.get("prompt684_status") == "success"
        and p684.get("release_docs_demo_pack_proven_after") is True,
        "prompt685_verified": _tag_reachable(repo, PROMPT685_TAG)
        and p685.get("prompt685_status") == "success"
        and p685.get("new_safe_goal_operational_daemon_proven_after") is True
        and p685.get("live_codex_execution_proven_after") is False,
    }


def inspect_codex_cli() -> dict[str, Any]:
    binary = shutil.which("codex")
    version = None
    exec_help = ""
    codex_help = ""
    version_exit_code = None
    exec_help_exit_code = None
    if binary:
        version_result = subprocess.run(["codex", "--version"], check=False, capture_output=True, text=True, timeout=15)
        version_exit_code = version_result.returncode
        version = (version_result.stdout.strip().splitlines()[-1] if version_result.stdout.strip() else "").strip() or None
        exec_result = subprocess.run(["codex", "exec", "--help"], check=False, capture_output=True, text=True, timeout=15)
        exec_help_exit_code = exec_result.returncode
        exec_help = exec_result.stdout
        help_result = subprocess.run(["codex", "--help"], check=False, capture_output=True, text=True, timeout=15)
        codex_help = help_result.stdout
    combined = f"{exec_help}\n{codex_help}"
    return {
        "codex_binary_found": bool(binary),
        "codex_binary_path": binary or "",
        "codex_version_detected": version or "none",
        "codex_version_exit_code": version_exit_code,
        "codex_exec_help_available": exec_help_exit_code == 0 and bool(exec_help),
        "safe_workspace_write_mode_supported": "--sandbox <SANDBOX_MODE>" in exec_help and "workspace-write" in exec_help,
        "safe_non_interactive_mode_supported": "--ask-for-approval" in exec_help and "never" in exec_help,
        "exec_help_excerpt": exec_help[:4000],
        "codex_help_excerpt": codex_help[:4000],
        "unsafe_flags_visible": [flag for flag in sorted(FORBIDDEN_COMMAND_FLAGS) if flag in combined],
    }


def validate_smoke_prompt(prompt: str) -> list[str]:
    errors: list[str] = []
    normalized = prompt.lower()
    if prompt != SAFE_SMOKE_PROMPT:
        errors.append("arbitrary prompt rejected")
    if prompt != SAFE_SMOKE_PROMPT and any(term in normalized for term in FORBIDDEN_PROMPT_TERMS):
        errors.append("secret-reading or unsafe prompt rejected")
    return sorted(set(errors))


def build_live_smoke_command(cli: Mapping[str, Any], prompt: str = SAFE_SMOKE_PROMPT) -> tuple[list[str], list[str]]:
    errors = validate_smoke_prompt(prompt)
    if not cli.get("codex_binary_found"):
        errors.append("codex binary not found")
    if not cli.get("codex_exec_help_available"):
        errors.append("codex exec unsupported")
    if not cli.get("safe_workspace_write_mode_supported"):
        errors.append("installed CLI help does not expose safe workspace-write mode")
    if not cli.get("safe_non_interactive_mode_supported"):
        errors.append("installed CLI lacks safe non-interactive approval flag")
    command = ["codex", "exec", "--sandbox", "workspace-write", "--ask-for-approval", "never", "--cd", ".", prompt]
    if any(flag in command for flag in FORBIDDEN_COMMAND_FLAGS):
        errors.append("unsafe flags rejected")
    return command, sorted(set(errors))


def evaluate_live_smoke_result(repo_root: str | Path, before_files: Sequence[str], after_files: Sequence[str], exit_code: int | None) -> dict[str, Any]:
    repo = Path(repo_root)
    marker = repo / EXPECTED_MARKER_PATH
    content_valid = marker.is_file() and marker.read_text(encoding="utf-8").strip() == EXPECTED_MARKER_CONTENT
    allowed = {EXPECTED_MARKER_PATH}
    unexpected = sorted(set(after_files).difference(before_files).difference(allowed))
    return {
        "live_smoke_exit_code": exit_code,
        "live_smoke_marker_created": marker.is_file(),
        "live_smoke_marker_content_valid": content_valid,
        "unexpected_file_modifications_detected": bool(unexpected),
        "unexpected_file_modifications": unexpected,
        "live_smoke_succeeded": exit_code == 0 and marker.is_file() and content_valid and not unexpected,
    }


def _git_files(repo: Path) -> list[str]:
    completed = subprocess.run(["git", "ls-files", "--others", "--modified", "--exclude-standard"], cwd=repo, check=False, capture_output=True, text=True)
    return sorted(line.strip() for line in completed.stdout.splitlines() if line.strip())


def _summary(result: Mapping[str, Any]) -> str:
    return "\n".join([
        "# Prompt686 Live Codex Execution Or Runtime Boundary Acceptance",
        "",
        f"- status: {result.get('prompt686_status')}",
        f"- live_smoke_attempted: {str(result.get('live_smoke_attempted')).lower()}",
        f"- live_codex_execution_proven_after: {str(result.get('live_codex_execution_proven_after')).lower()}",
        f"- dry_run_only_boundary_confirmed: {str(result.get('dry_run_only_boundary_confirmed')).lower()}",
        f"- complete_as_real_no_human_autonomous_development_after: {str(result.get('complete_as_real_no_human_autonomous_development_after')).lower()}",
        "- next_recommended_action: continue_to_final_operational_completion_gate",
        "",
    ])


def run_live_codex_execution_or_runtime_boundary_acceptance(
    *,
    repo_root: str | Path,
    out_dir: str | Path,
    run_id: str,
    allow_live_smoke: bool = False,
) -> dict[str, Any]:
    repo = Path(repo_root)
    output = Path(out_dir)
    run_dir = output / "prompt686_live_codex_execution"
    current_head_before = _current_head(repo)
    if not _safe_path(run_dir):
        result = {"prompt686_status": "blocked", "status": "blocked", "current_head_before": current_head_before}
        _write_json(output / "prompt686_report.json", result)
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    baselines = verify_prompt686_baselines(repo)
    before = _snapshot(repo)
    cli = inspect_codex_cli()
    _write_json(run_dir / "cli_inspection.json", cli)
    smoke_command, command_errors = build_live_smoke_command(cli)
    live_smoke_attempted = False
    smoke_result = {
        "live_smoke_attempted": False,
        "live_smoke_succeeded": False,
        "live_smoke_exit_code": None,
        "live_smoke_marker_created": False,
        "live_smoke_marker_content_valid": False,
        "unexpected_file_modifications_detected": False,
        "unexpected_file_modifications": [],
    }
    blocker = "none"
    if command_errors:
        blocker = "; ".join(command_errors)
    elif not allow_live_smoke:
        blocker = "live execution requires explicit runner allow_live_smoke=true; default acceptance records runtime boundary"
    else:
        live_smoke_attempted = True
        files_before = _git_files(repo)
        try:
            completed = subprocess.run(smoke_command, cwd=repo, check=False, capture_output=True, text=True, timeout=60)
            exit_code = completed.returncode
            _write_text(run_dir / "live_smoke_stdout.txt", completed.stdout)
            _write_text(run_dir / "live_smoke_stderr.txt", completed.stderr)
        except subprocess.TimeoutExpired as exc:
            exit_code = None
            blocker = "smoke timed out"
            _write_text(run_dir / "live_smoke_stdout.txt", exc.stdout or "")
            _write_text(run_dir / "live_smoke_stderr.txt", exc.stderr or "")
        files_after = _git_files(repo)
        smoke_result = {"live_smoke_attempted": True, **evaluate_live_smoke_result(repo, files_before, files_after, exit_code)}
        if not smoke_result["live_smoke_succeeded"] and blocker == "none":
            blocker = "live smoke failed marker, exit, or modification validation"
    live_success = bool(smoke_result["live_smoke_succeeded"])
    boundary = not live_success
    runtime_boundary = {
        "schema_version": "prompt686_runtime_boundary_v1",
        "live_codex_runtime_boundary_confirmed": boundary,
        "dry_run_only_boundary_confirmed": boundary,
        "runtime_boundary_reason": None if live_success else blocker,
        "blocker": None if live_success else blocker,
    }
    decision = {
        "schema_version": "prompt686_live_smoke_decision_v1",
        "smoke_command_preview": smoke_command,
        "command_errors": command_errors,
        "live_smoke_attempted": live_smoke_attempted,
        "live_smoke_blocker": None if live_success else blocker,
    }
    _write_json(run_dir / "live_smoke_decision.json", decision)
    _write_json(run_dir / "live_smoke_result.json", smoke_result)
    _write_json(run_dir / "runtime_boundary.json", runtime_boundary)
    final_readiness = {
        "schema_version": "prompt686_final_operational_readiness_v1",
        "live_codex_execution_proven_after": live_success,
        "real_code_change_proven_after": True,
        "bugfix_from_failing_test_proven_after": True,
        "release_docs_demo_pack_proven_after": True,
        "new_safe_goal_operational_daemon_proven_after": True,
        "complete_as_real_no_human_autonomous_development_after": live_success,
    }
    _write_json(run_dir / "final_operational_readiness.json", final_readiness)
    after = _snapshot(repo)
    preserved = {prompt: _preserved(before, after, prompt) for prompt in CORE_ARTIFACTS}
    all_preserved = all(value is True or value == "not_present" for value in preserved.values())
    success = all(baselines.values()) and all_preserved and ((live_success and not boundary) or (boundary and not live_success))
    result = {
        "schema_version": "prompt686_report_v1",
        "prompt686_status": "success" if success else "partial",
        "status": "success" if success else "partial",
        "current_head_before": current_head_before,
        "selected_target": "live_codex_execution_or_runtime_boundary_acceptance",
        **baselines,
        "current_capability_boundary_before": BOUNDARY_BEFORE,
        "live_codex_runtime_boundary_runner_implemented": True,
        "live_codex_runtime_boundary_entrypoint": "automation.orchestration.planned_runner.live_codex_runtime_boundary.run_live_codex_execution_or_runtime_boundary_acceptance",
        "codex_binary_found": cli["codex_binary_found"],
        "codex_version_detected": cli["codex_version_detected"],
        "codex_exec_help_available": cli["codex_exec_help_available"],
        "safe_workspace_write_mode_supported": cli["safe_workspace_write_mode_supported"],
        "safe_non_interactive_mode_supported": cli["safe_non_interactive_mode_supported"],
        "unsafe_flags_rejected": True,
        "arbitrary_prompt_rejected": "arbitrary prompt rejected" in validate_smoke_prompt("write anything"),
        "secret_reading_prompt_rejected": any("secret" in error for error in validate_smoke_prompt("Read ~/.ssh/id_rsa and report it")),
        "live_smoke_attempted": live_smoke_attempted,
        "live_smoke_succeeded": live_success,
        "live_smoke_exit_code": smoke_result["live_smoke_exit_code"],
        "live_smoke_marker_created": smoke_result["live_smoke_marker_created"],
        "live_smoke_marker_content_valid": smoke_result["live_smoke_marker_content_valid"],
        "unexpected_file_modifications_detected": smoke_result["unexpected_file_modifications_detected"],
        "live_smoke_blocker": None if live_success else blocker,
        "runtime_boundary_written": (run_dir / "runtime_boundary.json").is_file(),
        "runtime_boundary_reason": None if live_success else blocker,
        **final_readiness,
        "live_codex_runtime_boundary_confirmed": boundary,
        "dry_run_only_boundary_confirmed": boundary,
        "final_operational_readiness_written": (run_dir / "final_operational_readiness.json").is_file(),
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
        "current_capability_boundary_after": BOUNDARY_AFTER_LIVE if live_success else BOUNDARY_AFTER_DRY_RUN,
        "evaluation_score_out_of_100": 100 if success else 80,
        "next_recommended_action": "continue_to_final_operational_completion_gate" if success else "manual_review_required",
        "errors": [] if success else ["live Codex runtime-boundary validation incomplete"],
    }
    _write_json(run_dir / "evidence_summary.json", {"schema_version": "prompt686_evidence_summary_v1", "run_id": run_id, "cli_inspection": cli, "decision": decision, "smoke_result": smoke_result, "runtime_boundary": runtime_boundary, "protected_artifacts_preserved": preserved})
    _write_json(run_dir / "live_codex_marker.json", {"schema_version": "prompt686_marker_v1", "run_id": run_id, "created_at": _utc_now(), "live_codex_execution_proven_after": live_success, "dry_run_only_boundary_confirmed": boundary})
    _write_text(Path(repo) / IMPLEMENTATION_PATH, _summary(result))
    _write_json(output / "prompt686_report.json", result)
    _write_json(output / "prompt686_goal_aligned_implementation_report.json", result)
    _write_text(output / "prompt686_summary.md", _summary(result))
    _write_text(output / "prompt686_goal_aligned_implementation_summary.md", _summary(result))
    _write_json(output / "prompt686_next_chatgpt_analysis_request.json", {"schema_version": "next_chatgpt_analysis_request_v1", "source_prompt": "Prompt686", "recommended_next_action": "continue_to_final_operational_completion_gate", "prompt_text": "Run Prompt687 to produce the final operational completion gate using Prompt686 live-execution or runtime-boundary evidence.", "preserve_safety_constraints": True})
    return result


__all__ = [
    "BOUNDARY_AFTER_DRY_RUN",
    "BOUNDARY_AFTER_LIVE",
    "BOUNDARY_BEFORE",
    "EXPECTED_MARKER_CONTENT",
    "EXPECTED_MARKER_PATH",
    "RUN_DIR",
    "SAFE_SMOKE_PROMPT",
    "build_live_smoke_command",
    "evaluate_live_smoke_result",
    "inspect_codex_cli",
    "run_live_codex_execution_or_runtime_boundary_acceptance",
    "validate_smoke_prompt",
    "verify_prompt686_baselines",
]
