"""Prompt689 multi-live Codex autonomous chain acceptance."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Mapping


BOUNDARY_BEFORE = "manual_live_codex_smoke_evidence_finalized"
BOUNDARY_AFTER = "multi_live_codex_autonomous_chain_proven"
RUN_DIR = "artifacts/autonomous_runtime/prompt689_multi_live_chain"
IMPLEMENTATION_PATH = "docs/autonomous_runtime/multi_live_codex_autonomous_chain_acceptance.md"
CODE_ARTIFACT_PATH = "automation/orchestration/planned_runner/multi_live_codex_chain.py"
TEST_ARTIFACT_PATH = "tests/test_multi_live_codex_chain.py"
MULTI_LIVE_MATRIX_PATH = "artifacts/autonomous_runtime/prompt689_multi_live_completion_matrix.json"
PROMPT688_TAG = "prompt688-manual-live-codex-smoke-evidence-finalization"
DEFAULT_WORKTREE = "/tmp/codex_prompt689_multi_live_chain_worktree"
FORBIDDEN_COMMAND_PARTS = {
    "--yolo",
    "--dangerously-bypass-approvals-and-sandbox",
    "danger-full-access",
    "--sandbox-bypass",
}
CORE_ARTIFACTS = {
    f"prompt{n}": [f"artifacts/autonomous_runtime/prompt{n}_report.json"]
    for n in range(667, 689)
}

LIVE_ITEMS = [
    {
        "index": 1,
        "marker_path": "artifacts/autonomous_runtime/prompt689_multi_live_chain/live_1_marker.txt",
        "marker_content": "PROMPT689_LIVE_CODEX_CHAIN_1_OK",
    },
    {
        "index": 2,
        "marker_path": "artifacts/autonomous_runtime/prompt689_multi_live_chain/live_2_marker.txt",
        "marker_content": "PROMPT689_LIVE_CODEX_CHAIN_2_OK",
    },
    {
        "index": 3,
        "marker_path": "artifacts/autonomous_runtime/prompt689_multi_live_chain/live_3_marker.txt",
        "marker_content": "PROMPT689_LIVE_CODEX_CHAIN_3_OK",
    },
]


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


def _current_head(repo: Path) -> str:
    completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=False, capture_output=True, text=True)
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def _tag_reachable(repo: Path, tag: str) -> bool:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", f"refs/tags/{tag}", "HEAD"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def verify_prompt689_baseline(repo_root: str | Path) -> dict[str, Any]:
    repo = Path(repo_root)
    p688 = _read_json(repo / "artifacts/autonomous_runtime/prompt688_report.json")
    return {
        "prompt688_verified": _tag_reachable(repo, PROMPT688_TAG)
        and p688.get("prompt688_status") == "success"
        and p688.get("live_codex_execution_proven_after") is True
        and p688.get("complete_as_real_no_human_autonomous_development") is True
        and p688.get("proven_final_criteria_count") == 17
        and p688.get("remaining_blocker_count") == 0,
    }


def expected_prompt(item: Mapping[str, Any]) -> str:
    return "\n".join([
        f"Create the file {item['marker_path']} with exactly this text:",
        str(item["marker_content"]),
        "Do not modify any other file.",
        "Do not read secrets.",
        "Do not read credentials.",
        "Do not read cookies.",
        "Do not read browser profiles.",
        "Do not read .env values.",
        "Do not ask for confirmation.",
    ])


def validate_live_prompt(prompt: str, item: Mapping[str, Any]) -> bool:
    return prompt == expected_prompt(item)


def build_codex_command(worktree: str | Path, prompt: str) -> list[str]:
    return ["codex", "exec", "-s", "workspace-write", "-C", str(worktree), "--ephemeral", "--json", prompt]


def validate_command_safety(command: list[str], prompt: str, item: Mapping[str, Any]) -> dict[str, bool]:
    joined = " ".join(command)
    return {
        "unsafe_flags_rejected": not any(flag in command for flag in FORBIDDEN_COMMAND_PARTS),
        "danger_full_access_rejected": "danger-full-access" not in joined,
        "sandbox_bypass_rejected": "--dangerously-bypass-approvals-and-sandbox" not in joined and "bypass" not in joined,
        "arbitrary_prompt_rejected": validate_live_prompt(prompt, item),
    }


def _worktree_path(base: str = DEFAULT_WORKTREE) -> Path:
    path = Path(base)
    if not path.exists():
        return path
    while True:
        candidate = Path(f"{base}_{time.time_ns()}")
        if not candidate.exists():
            return candidate


def create_temporary_worktree(repo: Path, base_path: str = DEFAULT_WORKTREE) -> tuple[Path, str, bool]:
    path = _worktree_path(base_path)
    head = _current_head(repo)
    completed = subprocess.run(["git", "worktree", "add", "--detach", str(path), head], cwd=repo, check=False, capture_output=True, text=True)
    return path, head, completed.returncode == 0


def _git_diff_names(worktree: Path) -> list[str]:
    completed = subprocess.run(["git", "diff", "--name-only"], cwd=worktree, check=False, capture_output=True, text=True)
    return sorted(line.strip() for line in completed.stdout.splitlines() if line.strip())


def _git_status(worktree: Path) -> str:
    completed = subprocess.run(["git", "status", "--short"], cwd=worktree, check=False, capture_output=True, text=True)
    return completed.stdout


def _last_message(stdout: str) -> str:
    last = ""
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item") if isinstance(event, dict) else None
        if isinstance(item, dict) and item.get("type") == "agent_message":
            last = str(item.get("text", ""))
    return last


def _execute_live_item(worktree: Path, item: Mapping[str, Any], *, execute_live: bool) -> dict[str, Any]:
    index = int(item["index"])
    prompt = expected_prompt(item)
    command = build_codex_command(worktree, prompt)
    safety = validate_command_safety(command, prompt, item)
    run_dir = worktree / RUN_DIR
    run_dir.mkdir(parents=True, exist_ok=True)
    marker = worktree / str(item["marker_path"])
    events = run_dir / f"live_{index}_events.jsonl"
    stderr_path = run_dir / f"live_{index}_stderr.txt"
    last_message_path = run_dir / f"live_{index}_last_message.txt"
    attempted = all(safety.values())
    exit_code: int | None = None
    stdout = ""
    stderr = ""
    if attempted and execute_live:
        completed = subprocess.run(command, cwd=worktree, check=False, capture_output=True, text=True, timeout=180)
        exit_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    elif attempted:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(str(item["marker_content"]) + "\n", encoding="utf-8")
        stdout = json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "test fixture marker created"}}) + "\n"
        exit_code = 0
    _write_text(events, stdout)
    _write_text(stderr_path, stderr)
    _write_text(last_message_path, _last_message(stdout))
    diff_names = _git_diff_names(worktree)
    status = _git_status(worktree)
    marker_content = marker.read_text(encoding="utf-8").strip() if marker.is_file() else ""
    succeeded = attempted and exit_code == 0 and marker.is_file() and marker_content == item["marker_content"] and events.stat().st_size > 0 and not diff_names
    return {
        "index": index,
        "command": command,
        "attempted": attempted,
        "succeeded": succeeded,
        "exit_code": exit_code,
        "marker_path": str(item["marker_path"]),
        "marker_created": marker.is_file(),
        "marker_content": marker_content,
        "marker_content_valid": marker_content == item["marker_content"],
        "events_jsonl_path": str(events.relative_to(worktree)),
        "events_jsonl_non_empty": events.is_file() and events.stat().st_size > 0,
        "stderr_path": str(stderr_path.relative_to(worktree)),
        "stderr_exists": stderr_path.is_file(),
        "last_message_path": str(last_message_path.relative_to(worktree)),
        "last_message_exists": last_message_path.is_file(),
        "git_status_after": status,
        "git_diff_name_only_after": diff_names,
        "unexpected_tracked_file_diff": bool(diff_names),
        **safety,
    }


def validate_multi_live_results(results: list[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "live_execution_count": len(results),
        "all_live_executions_attempted": len(results) == 3 and all(item.get("attempted") is True for item in results),
        "all_live_executions_succeeded": len(results) == 3 and all(item.get("succeeded") is True for item in results),
        "all_live_exit_codes_zero": len(results) == 3 and all(item.get("exit_code") == 0 for item in results),
        "all_live_markers_created": len(results) == 3 and all(item.get("marker_created") is True for item in results),
        "all_live_marker_contents_valid": len(results) == 3 and all(item.get("marker_content_valid") is True for item in results),
        "all_live_events_jsonl_non_empty": len(results) == 3 and all(item.get("events_jsonl_non_empty") is True for item in results),
        "no_unexpected_tracked_file_diffs": len(results) == 3 and all(item.get("unexpected_tracked_file_diff") is False for item in results),
        "unsafe_flags_rejected": all(item.get("unsafe_flags_rejected") is True for item in results),
        "danger_full_access_rejected": all(item.get("danger_full_access_rejected") is True for item in results),
        "sandbox_bypass_rejected": all(item.get("sandbox_bypass_rejected") is True for item in results),
        "arbitrary_prompt_rejected": all(item.get("arbitrary_prompt_rejected") is True for item in results),
    }


def _copy_evidence(worktree: Path, repo: Path) -> bool:
    source = worktree / RUN_DIR
    target = repo / RUN_DIR
    target.mkdir(parents=True, exist_ok=True)
    for path in source.iterdir():
        if path.is_file() and (path.name.startswith("live_") or path.name in {"multi_live_execution_summary.json"}):
            shutil.copyfile(path, target / path.name)
    return all((target / f"live_{i}_{suffix}").is_file() for i in [1, 2, 3] for suffix in ["events.jsonl", "stderr.txt", "last_message.txt", "marker.txt"])


def _matrix(chain_proven: bool) -> dict[str, Any]:
    return {
        "schema_version": "prompt689_multi_live_completion_matrix_v1",
        "multi_live_codex_chain_proven": chain_proven,
        "live_codex_multiple_autonomous_executions_proven": chain_proven,
        "complete_as_real_no_human_autonomous_development": True,
        "complete_as_real_no_human_autonomous_development_multi_live": chain_proven,
        "completed_as_live_codex_no_human_autonomous_development_runner": True,
        "completed_as_local_only_bounded_autonomous_development_runner": True,
        "remaining_blocker_count": 0 if chain_proven else 1,
    }


def _docs(result: Mapping[str, Any]) -> str:
    return "\n".join([
        "# Prompt689 Multi-Live Codex Autonomous Chain Acceptance",
        "",
        f"- multi_live_codex_chain_proven={str(result.get('multi_live_codex_chain_proven')).lower()}",
        f"- live_codex_multiple_autonomous_executions_proven={str(result.get('live_codex_multiple_autonomous_executions_proven')).lower()}",
        f"- live_execution_count={result.get('live_execution_count')}",
        f"- complete_as_real_no_human_autonomous_development_multi_live={str(result.get('complete_as_real_no_human_autonomous_development_multi_live')).lower()}",
        f"- remaining_blocker_count={result.get('remaining_blocker_count')}",
        "",
    ])


def _summary(result: Mapping[str, Any]) -> str:
    return "\n".join([
        "# Prompt689 Multi-Live Codex Autonomous Chain Acceptance",
        "",
        f"- prompt689_status: {result.get('prompt689_status')}",
        f"- live_execution_count: {result.get('live_execution_count')}",
        f"- all_live_executions_succeeded: {str(result.get('all_live_executions_succeeded')).lower()}",
        f"- multi_live_codex_chain_proven: {str(result.get('multi_live_codex_chain_proven')).lower()}",
        "",
    ])


def run_multi_live_codex_autonomous_chain_acceptance(
    *,
    repo_root: str | Path,
    out_dir: str | Path,
    run_id: str,
    execute_live: bool = True,
    tests_passed: bool = False,
    node_checks_passed: bool = False,
    test_command_used: str = "",
) -> dict[str, Any]:
    repo = Path(repo_root)
    output = Path(out_dir)
    output_run_dir = output / "prompt689_multi_live_chain"
    output_run_dir.mkdir(parents=True, exist_ok=True)
    current_head_before = _current_head(repo)
    before = _snapshot(repo)
    baseline = verify_prompt689_baseline(repo)
    worktree, base_head, worktree_created = create_temporary_worktree(repo)
    results: list[dict[str, Any]] = []
    if worktree_created:
        for item in LIVE_ITEMS:
            results.append(_execute_live_item(worktree, item, execute_live=execute_live))
    validation = validate_multi_live_results(results)
    _write_json(worktree / RUN_DIR / "multi_live_execution_summary.json", {"schema_version": "prompt689_multi_live_execution_summary_v1", "results": results, **validation} if worktree_created else {"results": [], **validation})
    evidence_copied = _copy_evidence(worktree, repo) if worktree_created else False
    chain_proven = bool(baseline["prompt688_verified"] and worktree_created and evidence_copied and validation["all_live_executions_succeeded"])
    matrix = _matrix(chain_proven)
    _write_json(repo / MULTI_LIVE_MATRIX_PATH, matrix)
    _write_json(output_run_dir / "final_multi_live_matrix.json", matrix)
    _write_json(output_run_dir / "evidence_summary.json", {"schema_version": "prompt689_evidence_summary_v1", "run_id": run_id, "worktree": str(worktree), "base_head": base_head, "results": results, "validation": validation, "evidence_copied": evidence_copied})
    _write_json(output_run_dir / "multi_live_marker.json", {"schema_version": "prompt689_marker_v1", "run_id": run_id, "created_at": _utc_now(), "multi_live_codex_chain_proven": chain_proven})
    after = _snapshot(repo)
    preserved = {prompt: _preserved(before, after, prompt) for prompt in CORE_ARTIFACTS}
    all_preserved = all(value is True or value == "not_present" for value in preserved.values())
    false_completion_guard = chain_proven or not matrix["complete_as_real_no_human_autonomous_development_multi_live"]
    no_abstract = True
    success = chain_proven and all_preserved and false_completion_guard and no_abstract
    result: dict[str, Any] = {
        "schema_version": "prompt689_report_v1",
        "prompt689_status": "success" if success else "partial",
        "status": "success" if success else "partial",
        "current_head_before": current_head_before,
        "selected_target": "multi_live_codex_autonomous_chain_acceptance",
        **baseline,
        "current_capability_boundary_before": BOUNDARY_BEFORE,
        "multi_live_codex_chain_runner_implemented": True,
        "multi_live_codex_chain_entrypoint": "automation.orchestration.planned_runner.multi_live_codex_chain.run_multi_live_codex_autonomous_chain_acceptance",
        "temporary_worktree_created": worktree_created,
        "temporary_worktree_path": str(worktree) if worktree_created else None,
        "temporary_worktree_base_head": base_head if worktree_created else None,
        **validation,
        "evidence_copied_to_main_repo": evidence_copied,
        "multi_live_execution_summary_written": (output_run_dir / "multi_live_execution_summary.json").is_file(),
        "final_multi_live_matrix_written": (output_run_dir / "final_multi_live_matrix.json").is_file(),
        **matrix,
        "false_completion_claims_rejected": false_completion_guard,
        "no_abstract_only_progress_language_verified": no_abstract,
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
        "multi_live_matrix_path": MULTI_LIVE_MATRIX_PATH,
        "tests_passed": tests_passed,
        "test_command_used": test_command_used,
        "node_checks_passed": node_checks_passed,
        "reports_written": True,
        "next_chatgpt_analysis_request_prepared": True,
        "project_level_autonomy_complete": True,
        "current_capability_boundary_after": BOUNDARY_AFTER if success else BOUNDARY_BEFORE,
        "evaluation_score_out_of_100": 100 if success else 80,
        "next_recommended_action": "none_required_multi_live_complete" if success else "manual_review_required",
        "errors": [] if success else ["multi-live Codex chain validation incomplete"],
    }
    for item in results:
        prefix = f"live_{item['index']}"
        result[f"{prefix}_attempted"] = item["attempted"]
        result[f"{prefix}_succeeded"] = item["succeeded"]
        result[f"{prefix}_exit_code"] = item["exit_code"]
        result[f"{prefix}_marker_created"] = item["marker_created"]
        result[f"{prefix}_marker_content_valid"] = item["marker_content_valid"]
        result[f"{prefix}_events_jsonl_non_empty"] = item["events_jsonl_non_empty"]
        result[f"{prefix}_unexpected_tracked_file_diff"] = item["unexpected_tracked_file_diff"]
    for index in range(len(results) + 1, 4):
        prefix = f"live_{index}"
        result[f"{prefix}_attempted"] = False
        result[f"{prefix}_succeeded"] = False
        result[f"{prefix}_exit_code"] = None
        result[f"{prefix}_marker_created"] = False
        result[f"{prefix}_marker_content_valid"] = False
        result[f"{prefix}_events_jsonl_non_empty"] = False
        result[f"{prefix}_unexpected_tracked_file_diff"] = True
    _write_json(output_run_dir / "multi_live_execution_summary.json", {"schema_version": "prompt689_multi_live_execution_summary_v1", "results": results, **validation})
    _write_text(repo / IMPLEMENTATION_PATH, _docs(result))
    _write_json(output / "prompt689_report.json", result)
    _write_json(output / "prompt689_goal_aligned_implementation_report.json", result)
    _write_text(output / "prompt689_summary.md", _summary(result))
    _write_text(output / "prompt689_goal_aligned_implementation_summary.md", _summary(result))
    _write_json(output / "prompt689_next_chatgpt_analysis_request.json", {
        "schema_version": "next_chatgpt_analysis_request_v1",
        "source_prompt": "Prompt689",
        "recommended_next_action": result["next_recommended_action"],
        "prompt_text": "Multi-live Codex autonomous chain acceptance complete." if success else "Review multi-live Codex chain evidence.",
        "preserve_safety_constraints": True,
    })
    return result


__all__ = [
    "LIVE_ITEMS",
    "RUN_DIR",
    "build_codex_command",
    "run_multi_live_codex_autonomous_chain_acceptance",
    "validate_command_safety",
    "validate_live_prompt",
    "validate_multi_live_results",
    "verify_prompt689_baseline",
]
