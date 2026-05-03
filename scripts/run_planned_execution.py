from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any
from typing import Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automation.execution.codex_executor_adapter import CodexExecutorAdapter  # noqa: E402
from automation.execution.codex_executor_adapter import select_execution_transport  # noqa: E402
from automation.execution.codex_live_transport import CodexLiveExecutionTransport  # noqa: E402
from automation.orchestration.planned_execution_runner import DryRunCodexExecutionTransport  # noqa: E402
from automation.orchestration.planned_execution_runner import PlannedExecutionRunner  # noqa: E402


_REQUIRED_ARTIFACT_FILES = (
    "project_brief.json",
    "repo_facts.json",
    "roadmap.json",
    "pr_plan.json",
)


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _normalize_string_list(value: Any, *, sort_items: bool = False) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    items: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _normalize_text(item)
        if not text or text in seen:
            continue
        seen.add(text)
        items.append(text)
    if sort_items:
        return sorted(items)
    return items


def _as_non_negative_int(value: Any, *, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return max(0, value)
    text = _normalize_text(value)
    if text and text.lstrip("-").isdigit():
        return max(0, int(text))
    return default


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"expected JSON object: {path}")
    return dict(payload)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _normalize_repo_relative_path(path_text: str, *, repo_path: Path) -> str:
    text = _normalize_text(path_text)
    if not text:
        return ""
    normalized = text.replace("\\", "/")
    if normalized.startswith('"') and normalized.endswith('"') and len(normalized) >= 2:
        normalized = normalized[1:-1].strip()
    if not normalized:
        return ""
    candidate = Path(normalized)
    if candidate.is_absolute():
        try:
            normalized = candidate.resolve().relative_to(repo_path.resolve()).as_posix()
        except ValueError:
            return ""
    if normalized.startswith("/tmp/"):
        return ""
    return normalized.lstrip("./")


def _normalize_status_short_line(line: str, *, repo_path: Path) -> str:
    raw = line.rstrip()
    if not raw:
        return ""
    prefix = raw[:3] if len(raw) >= 3 else raw
    remainder = raw[3:] if len(raw) >= 3 else ""
    if not remainder.strip():
        return raw.replace("\\", "/")
    if " -> " in remainder:
        left, right = remainder.split(" -> ", 1)
        normalized_left = _normalize_repo_relative_path(left, repo_path=repo_path) or left.strip().replace("\\", "/")
        normalized_right = _normalize_repo_relative_path(right, repo_path=repo_path) or right.strip().replace("\\", "/")
        normalized_remainder = f"{normalized_left} -> {normalized_right}"
    else:
        normalized_remainder = (
            _normalize_repo_relative_path(remainder, repo_path=repo_path)
            or remainder.strip().replace("\\", "/")
        )
    return f"{prefix}{normalized_remainder}"


def _normalize_status_short_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    lines: list[str] = []
    seen: set[str] = set()
    for item in value:
        line = str(item).rstrip("\n\r")
        if not line or line in seen:
            continue
        seen.add(line)
        lines.append(line)
    return lines


def _run_git_command(repo_path: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )


def _parse_name_only(stdout: str, *, repo_path: Path) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    for line in stdout.splitlines():
        normalized = _normalize_repo_relative_path(line, repo_path=repo_path)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        paths.append(normalized)
    return sorted(paths)


def _parse_numstat(stdout: str, *, repo_path: Path) -> tuple[list[dict[str, Any]], int, int]:
    entries: list[dict[str, Any]] = []
    total_additions = 0
    total_deletions = 0
    for line in stdout.splitlines():
        raw = line.rstrip()
        if not raw:
            continue
        parts = raw.split("\t", 2)
        if len(parts) != 3:
            continue
        additions_raw, deletions_raw, raw_path = parts
        binary = additions_raw == "-" or deletions_raw == "-"
        additions = int(additions_raw) if additions_raw.isdigit() else 0
        deletions = int(deletions_raw) if deletions_raw.isdigit() else 0
        total_additions += additions
        total_deletions += deletions
        normalized_path = _normalize_repo_relative_path(raw_path, repo_path=repo_path)
        if not normalized_path:
            normalized_path = raw_path.strip().replace("\\", "/")
        entries.append(
            {
                "path": normalized_path,
                "raw_path": raw_path.strip().replace("\\", "/"),
                "additions": additions,
                "deletions": deletions,
                "binary": binary,
            }
        )
    return entries, total_additions, total_deletions


def _collect_git_accounting(repo_path: Path) -> dict[str, Any]:
    commands = [
        ("git_diff_name_only", ["diff", "--name-only"]),
        ("git_diff_numstat", ["diff", "--numstat"]),
        ("git_diff_cached_name_only", ["diff", "--cached", "--name-only"]),
        ("git_diff_cached_numstat", ["diff", "--cached", "--numstat"]),
        ("worktree_status_short", ["status", "--short"]),
    ]
    outputs: dict[str, str] = {}
    for field_name, git_args in commands:
        completed = _run_git_command(repo_path, git_args)
        if completed.returncode != 0:
            command_text = "git " + " ".join(git_args)
            stderr = _normalize_text(completed.stderr, default=_normalize_text(completed.stdout))
            return {
                "available": False,
                "failure_command": command_text,
                "failure_reason": stderr or f"{command_text} exited with {completed.returncode}",
            }
        outputs[field_name] = completed.stdout

    diff_name_only = _parse_name_only(outputs["git_diff_name_only"], repo_path=repo_path)
    diff_cached_name_only = _parse_name_only(outputs["git_diff_cached_name_only"], repo_path=repo_path)
    diff_numstat, diff_additions, diff_deletions = _parse_numstat(
        outputs["git_diff_numstat"],
        repo_path=repo_path,
    )
    diff_cached_numstat, diff_cached_additions, diff_cached_deletions = _parse_numstat(
        outputs["git_diff_cached_numstat"],
        repo_path=repo_path,
    )
    changed_files = sorted(set(diff_name_only) | set(diff_cached_name_only))
    worktree_status_short = [
        normalized
        for normalized in (
            _normalize_status_short_line(line, repo_path=repo_path)
            for line in outputs["worktree_status_short"].splitlines()
        )
        if normalized
    ]
    additions = diff_additions + diff_cached_additions
    deletions = diff_deletions + diff_cached_deletions
    return {
        "available": True,
        "git_diff_name_only": diff_name_only,
        "git_diff_numstat": diff_numstat,
        "git_diff_cached_name_only": diff_cached_name_only,
        "git_diff_cached_numstat": diff_cached_numstat,
        "git_accounted_changed_files": changed_files,
        "git_accounted_additions": additions,
        "git_accounted_deletions": deletions,
        "worktree_status_short": worktree_status_short,
        "worktree_dirty": bool(worktree_status_short),
        "diff_stat": {
            "unstaged": {
                "changed_files": diff_name_only,
                "additions": diff_additions,
                "deletions": diff_deletions,
                "file_count": len(diff_name_only),
            },
            "staged": {
                "changed_files": diff_cached_name_only,
                "additions": diff_cached_additions,
                "deletions": diff_cached_deletions,
                "file_count": len(diff_cached_name_only),
            },
            "combined": {
                "changed_files": changed_files,
                "additions": additions,
                "deletions": deletions,
                "file_count": len(changed_files),
            },
        },
    }


def _extract_validation_fields(result_payload: Mapping[str, Any]) -> tuple[str, list[str]]:
    execution = result_payload.get("execution") if isinstance(result_payload.get("execution"), Mapping) else {}
    verify = execution.get("verify") if isinstance(execution.get("verify"), Mapping) else {}
    validation_status = _normalize_text(
        result_payload.get("validation_status") or verify.get("status"),
        default="unknown",
    ).lower()
    if validation_status not in {"passed", "failed", "not_run", "blocked", "unknown"}:
        validation_status = "unknown"
    validation_commands = _normalize_string_list(
        result_payload.get("validation_commands") or verify.get("commands"),
        sort_items=False,
    )
    return validation_status, validation_commands


def _build_corrected_result_payload(
    *,
    result_payload: Mapping[str, Any],
    git_accounting: Mapping[str, Any] | None,
    dry_run: bool,
    repo_path_available: bool,
) -> dict[str, Any]:
    corrected = dict(result_payload)
    execution = dict(corrected.get("execution")) if isinstance(corrected.get("execution"), Mapping) else {}
    verify = dict(execution.get("verify")) if isinstance(execution.get("verify"), Mapping) else {}

    codex_reported_changed_files = _normalize_string_list(corrected.get("changed_files"), sort_items=True)
    codex_reported_additions = _as_non_negative_int(corrected.get("additions"), default=0)
    codex_reported_deletions = _as_non_negative_int(corrected.get("deletions"), default=0)
    validation_status, validation_commands = _extract_validation_fields(corrected)

    stdout_path = _normalize_text(corrected.get("stdout_path") or execution.get("stdout_path"), default="")
    stderr_path = _normalize_text(corrected.get("stderr_path") or execution.get("stderr_path"), default="")

    corrected["codex_reported_changed_files"] = codex_reported_changed_files
    corrected["codex_reported_additions"] = codex_reported_additions
    corrected["codex_reported_deletions"] = codex_reported_deletions
    corrected["stdout_path"] = stdout_path
    corrected["stderr_path"] = stderr_path
    corrected["validation_status"] = validation_status
    corrected["validation_commands"] = validation_commands

    execution["stdout_path"] = stdout_path
    execution["stderr_path"] = stderr_path
    verify["status"] = validation_status
    verify["commands"] = validation_commands
    execution["verify"] = verify
    corrected["execution"] = execution

    if not isinstance(git_accounting, Mapping):
        corrected["git_diff_name_only"] = []
        corrected["git_diff_numstat"] = []
        corrected["git_diff_cached_name_only"] = []
        corrected["git_diff_cached_numstat"] = []
        corrected["git_accounted_changed_files"] = []
        corrected["git_accounted_additions"] = 0
        corrected["git_accounted_deletions"] = 0
        corrected["final_changed_files"] = codex_reported_changed_files
        corrected["final_additions"] = codex_reported_additions
        corrected["final_deletions"] = codex_reported_deletions
        corrected["diff_stat"] = {
            "unstaged": {"changed_files": [], "additions": 0, "deletions": 0, "file_count": 0},
            "staged": {"changed_files": [], "additions": 0, "deletions": 0, "file_count": 0},
            "combined": {
                "changed_files": codex_reported_changed_files,
                "additions": codex_reported_additions,
                "deletions": codex_reported_deletions,
                "file_count": len(codex_reported_changed_files),
            },
        }
        corrected["worktree_status_short"] = []
        corrected["worktree_dirty"] = False
        if dry_run:
            corrected["accounting_source"] = "dry_run_no_worktree_mutation"
            corrected["accounting_status"] = "dry_run"
            corrected["accounting_reason"] = (
                "dry_run_without_repo_path"
                if not repo_path_available
                else "dry_run_does_not_claim_live_worktree_mutation"
            )
        else:
            corrected["accounting_source"] = "unavailable"
            corrected["accounting_status"] = "failed"
            corrected["accounting_reason"] = "git_accounting_unavailable"
        corrected["changed_files"] = codex_reported_changed_files
        corrected["additions"] = codex_reported_additions
        corrected["deletions"] = codex_reported_deletions
        return corrected

    git_changed_files = _normalize_string_list(git_accounting.get("git_accounted_changed_files"), sort_items=True)
    git_additions = _as_non_negative_int(git_accounting.get("git_accounted_additions"), default=0)
    git_deletions = _as_non_negative_int(git_accounting.get("git_accounted_deletions"), default=0)
    worktree_status_short = _normalize_status_short_list(git_accounting.get("worktree_status_short"))
    worktree_dirty = bool(git_accounting.get("worktree_dirty", False))

    corrected["git_diff_name_only"] = _normalize_string_list(
        git_accounting.get("git_diff_name_only"),
        sort_items=True,
    )
    corrected["git_diff_numstat"] = list(git_accounting.get("git_diff_numstat") or [])
    corrected["git_diff_cached_name_only"] = _normalize_string_list(
        git_accounting.get("git_diff_cached_name_only"),
        sort_items=True,
    )
    corrected["git_diff_cached_numstat"] = list(git_accounting.get("git_diff_cached_numstat") or [])
    corrected["git_accounted_changed_files"] = git_changed_files
    corrected["git_accounted_additions"] = git_additions
    corrected["git_accounted_deletions"] = git_deletions
    corrected["worktree_status_short"] = worktree_status_short
    corrected["worktree_dirty"] = worktree_dirty
    corrected["diff_stat"] = dict(git_accounting.get("diff_stat") or {})

    if dry_run:
        final_changed_files = codex_reported_changed_files
        final_additions = codex_reported_additions
        final_deletions = codex_reported_deletions
        accounting_source = "dry_run_no_worktree_mutation"
        accounting_status = "dry_run"
        accounting_reason = "dry_run_does_not_claim_live_worktree_mutation"
    else:
        final_changed_files = git_changed_files
        final_additions = git_additions
        final_deletions = git_deletions
        git_has_changes = bool(git_changed_files or git_additions or git_deletions)
        codex_matches_git = (
            codex_reported_changed_files == git_changed_files
            and codex_reported_additions == git_additions
            and codex_reported_deletions == git_deletions
        )
        empty_codex_despite_git = (
            (bool(git_changed_files) and not codex_reported_changed_files)
            or ((git_additions > 0 or git_deletions > 0) and codex_reported_additions == 0 and codex_reported_deletions == 0)
        )
        if not git_has_changes:
            accounting_source = "git_diff"
            accounting_status = "no_changes"
            accounting_reason = "git_diff_reports_no_changes"
        elif codex_matches_git:
            accounting_source = "combined"
            accounting_status = "accurate"
            accounting_reason = "git_diff_matches_codex_report"
        elif empty_codex_despite_git:
            accounting_source = "combined"
            accounting_status = "inconsistent"
            accounting_reason = "corrected_from_git_diff_after_empty_codex_report"
        else:
            accounting_source = "combined"
            accounting_status = "inconsistent"
            accounting_reason = "corrected_from_git_diff_after_report_mismatch"

    corrected["final_changed_files"] = final_changed_files
    corrected["final_additions"] = final_additions
    corrected["final_deletions"] = final_deletions
    corrected["accounting_source"] = accounting_source
    corrected["accounting_status"] = accounting_status
    corrected["accounting_reason"] = accounting_reason
    corrected["changed_files"] = final_changed_files
    corrected["additions"] = final_additions
    corrected["deletions"] = final_deletions
    return corrected


def _summarize_result_for_surfaces(
    result_payload: Mapping[str, Any],
    *,
    result_path: str,
    receipt_path: str,
) -> dict[str, Any]:
    return {
        "result_path": result_path,
        "receipt_path": receipt_path,
        "changed_files": _normalize_string_list(result_payload.get("changed_files"), sort_items=True),
        "additions": _as_non_negative_int(result_payload.get("additions"), default=0),
        "deletions": _as_non_negative_int(result_payload.get("deletions"), default=0),
        "diff_stat": dict(result_payload.get("diff_stat") or {}),
        "worktree_dirty": bool(result_payload.get("worktree_dirty", False)),
        "worktree_status_short": _normalize_status_short_list(result_payload.get("worktree_status_short")),
        "stdout_path": _normalize_text(result_payload.get("stdout_path"), default=""),
        "stderr_path": _normalize_text(result_payload.get("stderr_path"), default=""),
        "validation_status": _normalize_text(result_payload.get("validation_status"), default="unknown"),
        "validation_commands": _normalize_string_list(
            result_payload.get("validation_commands"),
            sort_items=False,
        ),
        "accounting_source": _normalize_text(result_payload.get("accounting_source"), default="unavailable"),
        "accounting_status": _normalize_text(result_payload.get("accounting_status"), default="unavailable"),
        "accounting_reason": _normalize_text(result_payload.get("accounting_reason"), default=""),
        "codex_reported_changed_files": _normalize_string_list(
            result_payload.get("codex_reported_changed_files"),
            sort_items=True,
        ),
        "codex_reported_additions": _as_non_negative_int(
            result_payload.get("codex_reported_additions"),
            default=0,
        ),
        "codex_reported_deletions": _as_non_negative_int(
            result_payload.get("codex_reported_deletions"),
            default=0,
        ),
        "git_accounted_changed_files": _normalize_string_list(
            result_payload.get("git_accounted_changed_files"),
            sort_items=True,
        ),
        "git_accounted_additions": _as_non_negative_int(
            result_payload.get("git_accounted_additions"),
            default=0,
        ),
        "git_accounted_deletions": _as_non_negative_int(
            result_payload.get("git_accounted_deletions"),
            default=0,
        ),
        "final_changed_files": _normalize_string_list(
            result_payload.get("final_changed_files"),
            sort_items=True,
        ),
        "final_additions": _as_non_negative_int(result_payload.get("final_additions"), default=0),
        "final_deletions": _as_non_negative_int(result_payload.get("final_deletions"), default=0),
        "git_diff_name_only": _normalize_string_list(
            result_payload.get("git_diff_name_only"),
            sort_items=True,
        ),
        "git_diff_numstat": list(result_payload.get("git_diff_numstat") or []),
        "git_diff_cached_name_only": _normalize_string_list(
            result_payload.get("git_diff_cached_name_only"),
            sort_items=True,
        ),
        "git_diff_cached_numstat": list(result_payload.get("git_diff_cached_numstat") or []),
    }


def _refresh_result_accounting_surfaces(
    *,
    manifest: dict[str, Any],
    output_dir: Path,
    repo_path: Path | None,
    dry_run: bool,
) -> dict[str, Any]:
    run_root = output_dir / _normalize_text(manifest.get("job_id"), default="")
    manifest_path = run_root / "manifest.json"
    accounting_records: list[dict[str, Any]] = []
    git_accounting: Mapping[str, Any] | None = None
    collected: Mapping[str, Any] | None = None

    if repo_path is not None:
        collected = _collect_git_accounting(repo_path)
        if collected.get("available"):
            git_accounting = collected
        else:
            git_accounting = None
    for entry in manifest.get("pr_units", []):
        if not isinstance(entry, dict):
            continue
        result_path_text = _normalize_text(entry.get("result_path"), default="")
        if not result_path_text:
            continue
        result_path = Path(result_path_text)
        if not result_path.exists():
            continue
        result_payload = _read_json_object(result_path)

        unit_git_accounting: Mapping[str, Any] | None
        if repo_path is None:
            unit_git_accounting = None
        elif git_accounting is not None:
            unit_git_accounting = git_accounting
        else:
            failure_reason = "git_accounting_unavailable"
            if isinstance(collected, Mapping):
                failure_reason = _normalize_text(
                    collected.get("failure_reason"),
                    default=failure_reason,
                )
            unit_git_accounting = None
            result_payload = dict(result_payload)
            result_payload["accounting_source"] = "unavailable" if not dry_run else "dry_run_no_worktree_mutation"
            result_payload["accounting_status"] = "failed" if not dry_run else "dry_run"
            result_payload["accounting_reason"] = failure_reason

        corrected_result = _build_corrected_result_payload(
            result_payload=result_payload,
            git_accounting=unit_git_accounting,
            dry_run=dry_run,
            repo_path_available=repo_path is not None,
        )
        if repo_path is not None and git_accounting is None and not dry_run:
            corrected_result["accounting_source"] = "unavailable"
            corrected_result["accounting_status"] = "failed"
            corrected_result["accounting_reason"] = _normalize_text(
                collected.get("failure_reason") if isinstance(collected, Mapping) else "",
                default="git_accounting_unavailable",
            )
        _write_json(result_path, corrected_result)

        receipt_path_text = _normalize_text(entry.get("receipt_path"), default="")
        if receipt_path_text:
            receipt_path = Path(receipt_path_text)
            if receipt_path.exists():
                receipt_payload = _read_json_object(receipt_path)
                receipt_payload.update(
                    _summarize_result_for_surfaces(
                        corrected_result,
                        result_path=result_path_text,
                        receipt_path=receipt_path_text,
                    )
                )
                _write_json(receipt_path, receipt_payload)

        summary = _summarize_result_for_surfaces(
            corrected_result,
            result_path=result_path_text,
            receipt_path=receipt_path_text,
        )
        entry.update(summary)
        accounting_records.append({"pr_id": _normalize_text(entry.get("pr_id"), default=""), **summary})

    manifest["result_accounting_summary"] = accounting_records
    if accounting_records:
        manifest["result_accounting_overview"] = {
            "unit_count": len(accounting_records),
            "worktree_dirty": any(bool(item.get("worktree_dirty", False)) for item in accounting_records),
            "changed_files": sorted(
                {
                    path
                    for item in accounting_records
                    for path in _normalize_string_list(item.get("changed_files"), sort_items=False)
                }
            ),
            "additions": sum(_as_non_negative_int(item.get("additions"), default=0) for item in accounting_records),
            "deletions": sum(_as_non_negative_int(item.get("deletions"), default=0) for item in accounting_records),
        }
    if manifest_path.exists():
        _write_json(manifest_path, manifest)
    return manifest


def _read_json_file_if_present(path_value: str | None) -> dict[str, object] | None:
    text = str(path_value or "").strip()
    if not text:
        return None
    path = Path(text)
    if not path.exists():
        raise ValueError(f"input file does not exist: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"input file must contain a JSON object: {path}")
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run planned PR-slice execution with explicit transport mode")
    parser.add_argument("--artifacts-dir", required=True, help="Directory containing planning artifacts")
    parser.add_argument("--out-dir", required=True, help="Output root for execution artifacts")
    parser.add_argument("--job-id", default=None, help="Optional override for execution job_id")
    parser.add_argument("--retry-context", default=None, help="Optional retry context JSON path")
    parser.add_argument("--policy-snapshot", default=None, help="Optional policy snapshot JSON path")
    parser.add_argument("--github-read-evidence", default=None, help="Optional GitHub read evidence JSON path")
    parser.add_argument(
        "--transport-mode",
        default="dry-run",
        choices=("dry-run", "live"),
        help="Execution transport mode",
    )
    parser.add_argument("--enable-live-transport", action="store_true", help="Explicitly allow live transport mode")
    parser.add_argument("--repo-path", default=None, help="Repository path required for live transport mode")
    parser.add_argument("--live-timeout-seconds", type=int, default=600, help="Timeout for live Codex execution")
    parser.add_argument("--stop-on-failure", action="store_true", default=True, help="Stop when a unit fails")
    parser.add_argument("--continue-on-failure", action="store_true", help="Continue processing units after failures")
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def _validate_inputs(artifacts_dir: Path) -> None:
    if not artifacts_dir.exists() or not artifacts_dir.is_dir():
        raise ValueError(f"artifacts directory does not exist: {artifacts_dir}")

    missing: list[str] = []
    for filename in _REQUIRED_ARTIFACT_FILES:
        if not (artifacts_dir / filename).exists():
            missing.append(filename)
    if missing:
        raise ValueError("missing required planning artifacts: " + ", ".join(missing))


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    artifacts_dir = Path(args.artifacts_dir)
    out_dir = Path(args.out_dir)

    try:
        _validate_inputs(artifacts_dir)

        retry_context = _read_json_file_if_present(args.retry_context)
        policy_snapshot = _read_json_file_if_present(args.policy_snapshot)
        github_read_evidence = _read_json_file_if_present(args.github_read_evidence)
        if args.transport_mode == "live":
            if not args.enable_live_transport:
                raise ValueError("live transport mode requires --enable-live-transport")
            repo_path_text = str(args.repo_path or "").strip()
            if not repo_path_text:
                raise ValueError("live transport mode requires --repo-path")
            repo_path = Path(repo_path_text)
            if not repo_path.exists() or not repo_path.is_dir():
                raise ValueError(f"repo_path does not exist or is not a directory: {repo_path}")
            if args.live_timeout_seconds <= 0:
                raise ValueError("live timeout must be a positive integer")

        dry_run_transport = DryRunCodexExecutionTransport()
        live_transport = (
            CodexLiveExecutionTransport(
                repo_path=str(Path(args.repo_path).resolve()),
                timeout_seconds=args.live_timeout_seconds,
            )
            if args.transport_mode == "live"
            else None
        )
        selected_transport, resolved_mode = select_execution_transport(
            mode=args.transport_mode,
            dry_run_transport=dry_run_transport,
            live_transport=live_transport,
            live_transport_enabled=bool(args.enable_live_transport),
        )
        dry_run = resolved_mode == "dry-run"
        stop_on_failure = False if args.continue_on_failure else bool(args.stop_on_failure)

        adapter = CodexExecutorAdapter(transport=selected_transport)
        runner = PlannedExecutionRunner(adapter=adapter)
        manifest = runner.run(
            artifacts_input_dir=artifacts_dir,
            output_dir=out_dir,
            job_id=args.job_id,
            dry_run=dry_run,
            stop_on_failure=stop_on_failure,
            retry_context=retry_context,
            policy_snapshot=policy_snapshot,
            github_read_evidence=github_read_evidence,
            execution_repo_path=str(Path(args.repo_path).resolve()) if args.repo_path else None,
        )
        manifest = _refresh_result_accounting_surfaces(
            manifest=manifest,
            output_dir=out_dir,
            repo_path=Path(args.repo_path).resolve() if args.repo_path else None,
            dry_run=dry_run,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.as_json:
        print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    else:
        print(f"job_id={manifest['job_id']}")
        print(f"run_status={manifest['run_status']}")
        print(f"processed_units={len(manifest.get('pr_units', []))}")
        print(f"next_action={manifest.get('decision_summary', {}).get('next_action', '')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
