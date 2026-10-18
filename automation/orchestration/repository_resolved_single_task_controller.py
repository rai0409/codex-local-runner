"""Fail-closed, local-only controller for one repository-resolved task.

The controller deliberately owns Git mutation only after Registry resolution,
Profile approvals, source preflight, prepared-worktree execution, validation,
and exact change-scope checks have all succeeded.  It never performs remote
operations and preserves unsafe worktrees for inspection instead of repairing
them.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from adapters import resolve_adapter
from automation.orchestration.repository_profile_binding import bind_repository_profile_to_worktree
from automation.orchestration.repository_registry import (
    DEFAULT_REPOSITORY_BINDINGS_PATH,
    load_repository_registry,
    resolve_repository,
)
from automation.orchestration.repository_single_task_spec import (
    RepositorySingleTaskSpec,
    load_repository_single_task_spec,
    serialize_repository_single_task_spec,
    validate_repository_single_task_spec,
)
from automation.orchestration.repository_state_analyzer import analyze_repository_state, repository_state_to_mapping
from automation.orchestration.safe_validation_executor import (
    SafeValidationExecutorError,
    execute_repository_validation,
    validation_execution_result_to_mapping,
)
from automation.orchestration.validation_repair import (
    MAX_VALIDATION_REPAIR_ATTEMPTS,
    ValidationFailureClassification,
    build_repair_prompt,
    classify_validation_failure,
    extract_actionable_failure,
    validation_failure_classification_to_mapping,
)
from automation.orchestration.task_completion_evaluator import (
    TaskCompletionEvaluation,
    build_task_completion_evaluator_prompt,
    build_task_completion_rework_prompt,
    execute_task_completion_evaluator,
    task_completion_evaluation_to_mapping,
)
from orchestrator.codex_execution import DEFAULT_COMPLETION_EVALUATOR_TIMEOUT_SECONDS
from orchestrator.codex_execution import DEFAULT_COMPLETION_REWORK_TIMEOUT_SECONDS


DEFAULT_REPOSITORY_SINGLE_TASK_OUTPUT_ROOT = (
    "~/.local/state/codex-local-runner/"
    "repository-single-task-runs"
)
MAX_TASK_REWORK_ATTEMPTS = 2
MAX_SAFE_SCOPE_AUTO_EXPANSIONS = 3
MAX_UNTRACKED_COMPLETION_CONTENT_BYTES = 8192

_SCOPE_HARD_BLOCK_COMPONENTS = frozenset({
    ".git", ".github", "__pycache__", "alembic", "build", "ci", "credentials",
    "database", "db", "deploy", "deployment", "env", "environment", "infrastructure",
    "kubernetes", "migrations", "requirements", "schema", "schemas", "secrets",
    "terraform", "workflows",
})
_SCOPE_HARD_BLOCK_DIRECTORY_COMPONENTS = frozenset({"data", "dataset", "datasets"})
_SCOPE_HARD_BLOCK_BASENAMES = frozenset({
    ".env", "compose.yaml", "compose.yml", "docker-compose.yaml", "docker-compose.yml",
    "dockerfile", "package.json", "package-lock.json", "pdm.lock", "pnpm-lock.yaml",
    "poetry.lock", "pyproject.toml", "requirements.txt", "setup.cfg", "setup.py",
    "yarn.lock",
})
_SCOPE_HARD_BLOCK_SUFFIXES = (
    ".7z", ".bin", ".bz2", ".dll", ".exe", ".gz", ".jar", ".pyc", ".rar",
    ".so", ".sql", ".tar", ".tgz", ".xz", ".zip",
)


@dataclass(frozen=True)
class _ScopeRecovery:
    declared_allowed_changed_paths: tuple[str, ...]
    actual_changed_files: tuple[str, ...]
    original_unexpected_changed_files: tuple[str, ...]
    scope_recovery_attempted: bool
    scope_recovery_status: str
    auto_expanded_paths: tuple[str, ...]
    effective_allowed_changed_paths: tuple[str, ...]
    unresolved_unexpected_changed_files: tuple[str, ...]


@dataclass(frozen=True)
class _AppliedScopeRecovery:
    """One runner-owned application of the existing changed-path recovery."""
    status: str
    recovery: _ScopeRecovery
    trimmed_paths: tuple[str, ...]


def _phase_timeout(task_value: int | None, profile_value: int | None, default: int) -> int:
    return task_value if task_value is not None else profile_value if profile_value is not None else default


@dataclass(frozen=True)
class RepositorySingleTaskRunResult:
    schema_version: str
    run_id: str
    status: str
    reason_code: str
    detail_reason_code: str | None
    repository_id: str
    task_id: str | None
    source_repository_root: str | None
    source_branch: str | None
    source_head_before: str | None
    source_head_after: str | None
    profile_id: str | None
    task_spec_sha256: str | None
    worktree_path: str | None
    worktree_preserved: bool
    task_branch: str | None
    commit_sha: str | None
    commit_parent_sha: str | None
    changed_files: tuple[str, ...]
    adapter_name: str | None
    execution_status: str | None
    validation_status: str | None
    validation_reason: str | None
    retry_attempted: bool
    retry_outcome: str | None
    receipt_path: str | None
    receipt_sha256_path: str | None
    started_at: str
    finished_at: str


class RepositorySingleTaskControllerError(ValueError):
    """Stable, secret-free controller error."""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}")


def repository_single_task_run_result_to_mapping(result: RepositorySingleTaskRunResult) -> dict[str, Any]:
    if not isinstance(result, RepositorySingleTaskRunResult):
        raise TypeError("result must be RepositorySingleTaskRunResult")
    value = asdict(result)
    value["changed_files"] = list(result.changed_files)
    return value


def serialize_repository_single_task_run_result(result: RepositorySingleTaskRunResult) -> str:
    return json.dumps(
        repository_single_task_run_result_to_mapping(result),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _git_environment() -> dict[str, str]:
    """Return the minimum environment required for local Git operations."""
    environment = {
        "GIT_TERMINAL_PROMPT": "0",
        "LC_ALL": "C",
        "LANG": "C",
    }
    for name in ("HOME", "PATH", "XDG_CONFIG_HOME"):
        value = os.environ.get(name)
        if value:
            environment[name] = value
    return environment


def _git(root: str | Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run a bounded local Git command without a shell or credential prompt."""
    return subprocess.run(
        ["git", "-C", os.fspath(root), *arguments],
        shell=False,
        stdin=subprocess.DEVNULL,
        text=True,
        capture_output=True,
        timeout=20,
        env=_git_environment(),
        check=False,
    )


def _git_bytes(root: str | Path, *arguments: str) -> subprocess.CompletedProcess[bytes]:
    """Read an exact local Git object without decoding its bytes."""
    return subprocess.run(
        ["git", "-C", os.fspath(root), *arguments],
        shell=False,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=20,
        env=_git_environment(),
        check=False,
    )


def _atomic_json(path: Path, value: Any) -> None:
    """Write deterministic JSON atomically and verify the final representation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".receipt-", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        json.loads(temporary.read_text(encoding="utf-8"))
        os.replace(temporary, path)
        json.loads(path.read_text(encoding="utf-8"))
    finally:
        if temporary.exists():
            temporary.unlink()


def _is_clean(snapshot: Any) -> bool:
    return snapshot.worktree_state == "known_clean" and not any(
        (
            snapshot.tracked_modified_files,
            snapshot.staged_files,
            snapshot.untracked_files,
            snapshot.conflicted_files,
            snapshot.operations_in_progress,
        )
    )


def _worktree_can_be_removed(snapshot: Any, expected_head: str, branch_created: bool, commit_sha: str | None) -> bool:
    return bool(
        snapshot
        and _is_clean(snapshot)
        and snapshot.detached_head
        and snapshot.head_sha == expected_head
        and not branch_created
        and commit_sha is None
    )


def _safe_validation_attempts(value: Any) -> list[dict[str, Any]]:
    """Retain only the adapter's secret-safe validation receipt fields."""
    if not isinstance(value, list):
        return []
    allowed = {
        "attempt_number", "phase", "execution_status", "validation_status",
        "validation_reason", "repair_attempt_number", "scope_status",
    }
    failure_allowed = {"command_id", "kind", "status", "return_code", "reason_code", "stdout_tail_sha256", "stderr_tail_sha256"}
    classification_allowed = {
        "failure_class", "auto_repairable", "retryable", "failed_command_ids",
        "failed_test_identifiers", "scope_extension_required", "evidence_refs",
    }
    result: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        safe = {key: item[key] for key in allowed if key in item}
        failure = item.get("failure")
        if isinstance(failure, dict):
            safe["failure"] = {key: failure[key] for key in failure_allowed if key in failure}
        classification = item.get("classification")
        if isinstance(classification, dict):
            safe["classification"] = {
                key: classification[key] for key in classification_allowed if key in classification
            }
        result.append(safe)
    return result


def _validation_attempt_from_result(
    *,
    attempt_number: int,
    phase: str,
    repair_attempt_number: int | None,
    result: Any,
    scope_status: str,
) -> tuple[dict[str, Any], ValidationFailureClassification | None]:
    """Create the public, bounded validation evidence for controller-managed runs."""
    mapping = validation_execution_result_to_mapping(result)
    status = mapping["status"]
    entry: dict[str, Any] = {
        "attempt_number": attempt_number,
        "phase": phase,
        "execution_status": "completed",
        "validation_status": status,
        "validation_reason": "validation_passed" if status == "passed" else "validation_failed",
        "scope_status": scope_status,
    }
    if repair_attempt_number is not None:
        entry["repair_attempt_number"] = repair_attempt_number
    if status == "passed":
        return entry, None
    classification = classify_validation_failure(mapping)
    entry["classification"] = validation_failure_classification_to_mapping(classification)
    return entry, classification


def _repair_scope_status(
    root: Path,
    profile: Any,
    effective_allowed_changed_paths: tuple[str, ...],
) -> tuple[str, tuple[str, ...]]:
    """Reject repair path drift before any post-repair validation command runs."""
    snapshot = analyze_repository_state(root)
    changed = _actual_changed_paths(snapshot)
    offending = tuple(sorted(set(changed) - set(effective_allowed_changed_paths)))
    if len(changed) > profile.max_changed_files:
        return "max_changed_files_exceeded", changed
    if offending:
        return "out_of_scope", offending
    if snapshot.head_sha is None or not snapshot.detached_head or snapshot.staged_files or snapshot.operations_in_progress:
        return "worktree_state_invalid", changed
    return "passed", changed


def _actual_changed_paths(snapshot: Any) -> tuple[str, ...]:
    """Return the canonical changed-path set for evaluator and receipts."""
    return tuple(sorted(set(snapshot.tracked_modified_files) | set(snapshot.untracked_files)))


def _bounded_untracked_completion_content(candidate: Path, maximum: int) -> tuple[str | None, int | None, bool, str | None]:
    """Read one regular file for evaluator evidence without following links."""
    try:
        if maximum < 1 or candidate.is_symlink() or not candidate.is_file():
            return None, None, False, "not_regular_file"
        size = candidate.stat().st_size
        with candidate.open("rb") as stream:
            content = stream.read(maximum + 1)
    except OSError:
        return None, None, False, "read_failed"
    truncated = len(content) > maximum or size > maximum
    content = content[:maximum]
    text = content.decode("utf-8", errors="replace")
    # Keep serialized evidence deterministic and legible for arbitrary file bytes.
    text = "".join(character if character in "\n\t" or ord(character) >= 32 else "?" for character in text)
    return text, size, truncated, None


def _completion_changed_artifact_evidence(
    root: Path,
    snapshot: Any,
    effective_allowed_changed_paths: tuple[str, ...],
) -> dict[str, dict[str, Any]]:
    """Return bounded evidence for every in-scope effective changed artifact.

    Git does not include untracked files in ``git diff``. Their content is
    therefore added only after the same effective-scope check used by the
    controller, with a fixed total content budget split deterministically
    between the eligible new files.
    """
    effective = frozenset(effective_allowed_changed_paths)
    tracked = frozenset(snapshot.tracked_modified_files)
    untracked = tuple(sorted(set(snapshot.untracked_files) & effective))
    changed = tuple(sorted(set(_actual_changed_paths(snapshot)) & effective))
    per_file_budget = (
        max(1, MAX_UNTRACKED_COMPLETION_CONTENT_BYTES // len(untracked))
        if untracked else 0
    )
    evidence: dict[str, dict[str, Any]] = {}
    for path in changed:
        candidate = root / path
        is_untracked = path in untracked
        exists = False
        try:
            exists = candidate.exists() and not candidate.is_symlink()
        except OSError:
            pass
        entry: dict[str, Any] = {
            "path": path,
            "inside_effective_scope": True,
            "exists": exists,
            "change_kind": (
                "new_untracked" if is_untracked
                else "modified_tracked" if path in tracked and exists
                else "deleted_tracked"
            ),
        }
        if is_untracked:
            content, size, truncated, unavailable = _bounded_untracked_completion_content(
                candidate, per_file_budget,
            )
            entry.update({
                "content": content,
                "content_bytes": min(size, per_file_budget) if size is not None else 0,
                "file_bytes": size,
                "content_truncated": truncated,
                "content_unavailable_reason": unavailable,
            })
        else:
            entry["content_evidence"] = "bounded_git_diff"
        evidence[path] = entry
    return evidence


def _normalized_repository_relative_path(root: Path, value: Any) -> str | None:
    """Return a safe canonical path, or ``None`` for any ambiguous path."""
    if not isinstance(value, str) or not value:
        return None
    normalized = value.replace("\\", "/")
    if normalized != value:
        return None
    if any(ord(character) < 32 for character in normalized):
        return None
    if ":" in normalized:
        return None
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized):
        return None
    parts = PurePosixPath(normalized).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        return None
    canonical = "/".join(parts)
    if canonical != normalized or ".git" in parts:
        return None
    try:
        root_path = root.resolve(strict=True)
        candidate = root_path.joinpath(*parts)
        if candidate.is_symlink() or not candidate.resolve(strict=False).is_relative_to(root_path):
            return None
    except (OSError, RuntimeError):
        return None
    return canonical


def _is_scope_high_authority_path(path: str) -> bool:
    """Reject paths whose ownership cannot be delegated to bounded recovery."""
    parts = tuple(part.casefold() for part in PurePosixPath(path).parts)
    basename = parts[-1]
    return bool(
        any(part in _SCOPE_HARD_BLOCK_COMPONENTS - {"alembic", "migrations"} for part in parts)
        or any(part in _SCOPE_HARD_BLOCK_DIRECTORY_COMPONENTS for part in parts[:-1])
        or basename in _SCOPE_HARD_BLOCK_BASENAMES
        or basename.startswith(".env")
        or (basename.startswith("requirements") and basename.endswith(".txt"))
        or basename.endswith(".lock")
        or "environment" in basename
        or "secret" in basename
        or "credential" in basename
        or basename.endswith(_SCOPE_HARD_BLOCK_SUFFIXES)
    )


def _is_scope_untrimmable_path(path: str) -> bool:
    """Return only security-sensitive identities that cannot be auto-restored.

    This is deliberately narrower than ``_is_scope_high_authority_path``.
    The latter prevents a model change from becoming authorized; a normal,
    repository-contained tracked file can still be restored exactly to the
    execution-base blob without granting that authority.
    """
    parts = tuple(part.casefold() for part in PurePosixPath(path).parts)
    basename = parts[-1]
    return bool(
        any(part in {".git", ".github", "__pycache__", "credentials", "secrets", "hooks", "deploy", "deployment", "terraform", "kubernetes", "workflows"} for part in parts)
        or basename.startswith(".env")
        or "secret" in basename
        or "credential" in basename
        or basename.endswith(".pyc")
    )


def _scope_extension_candidate_paths(paths: tuple[str, ...]) -> tuple[str, ...]:
    """Return paths that need explicit human scope review after failed rework."""
    candidates = []
    for path in paths:
        parts = tuple(part.casefold() for part in PurePosixPath(path).parts)
        if (
            any(part in {"alembic", "migrations", "schema", "schemas"} for part in parts)
            or "/db/models/" in path.casefold()
        ):
            candidates.append(path)
    return tuple(sorted(set(candidates)))


def _is_new_regular_file(root: Path, path: str, untracked_files: frozenset[str]) -> bool:
    """Only untracked regular files can receive deterministic new-file scope."""
    if path not in untracked_files:
        return False
    candidate = root / path
    try:
        return candidate.exists() and candidate.is_file() and not candidate.is_symlink()
    except OSError:
        return False


_MIGRATION_FILENAME = re.compile(r"^(?:\d{8}_)?(\d{4,}_[a-z0-9_]+)\.py$")


def _migration_identity(path: str) -> tuple[str, str] | None:
    value = PurePosixPath(path)
    match = _MIGRATION_FILENAME.fullmatch(value.name)
    if match is None:
        return None
    return value.parent.as_posix(), match.group(1)


def _is_safe_generated_migration(
    root: Path,
    path: str,
    declared: tuple[str, ...],
    untracked_files: frozenset[str],
) -> bool:
    """Allow one declared migration identity whose generated date changed only."""
    if not _is_new_regular_file(root, path, untracked_files):
        return False
    identity = _migration_identity(path)
    if identity is None:
        return False
    directory, suffix = identity
    return any(
        declared_identity is not None
        and declared_identity[0] == directory
        and declared_identity[1] == suffix
        and declared_path != path
        for declared_path in declared
        for declared_identity in (_migration_identity(declared_path),)
    )


def _task_identifier(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def _is_safe_task_specific_test(
    root: Path,
    path: str,
    declared: tuple[str, ...],
    task_id: str | None,
    untracked_files: frozenset[str],
) -> bool:
    """Allow only a new test named exactly for the runner-owned task ID."""
    if not isinstance(task_id, str) or not task_id or not _is_new_regular_file(root, path, untracked_files):
        return False
    value = PurePosixPath(path)
    if "tests" not in tuple(part.casefold() for part in value.parts[:-1]):
        return False
    if not re.fullmatch(r"test_[a-z0-9_]+\.py", value.name.casefold()):
        return False
    if value.stem.casefold() != "test_" + _task_identifier(task_id):
        return False
    # The same direct test area must already be authorized by the task spec.
    return any(PurePosixPath(item).parent == value.parent and "tests" in tuple(part.casefold() for part in PurePosixPath(item).parts[:-1]) for item in declared)


def _recover_safe_changed_path_scope(
    root: Path,
    declared_allowed_changed_paths: tuple[str, ...],
    actual_changed_files: tuple[str, ...],
    *,
    task_id: str | None = None,
    untracked_files: tuple[str, ...] = (),
) -> _ScopeRecovery:
    """Classify bounded path drift without granting new path authority."""
    declared = tuple(sorted(set(declared_allowed_changed_paths)))
    actual = tuple(sorted(set(actual_changed_files)))
    declared_set = set(declared)
    unexpected = tuple(path for path in actual if path not in declared_set)
    if not unexpected:
        return _ScopeRecovery(declared, actual, unexpected, False, "not_needed", (), declared, ())
    hard_blocked = False
    for raw in unexpected:
        path = _normalized_repository_relative_path(root, raw)
        if path is None or path != raw or _is_scope_untrimmable_path(path):
            hard_blocked = True
            continue
    # Repair headroom and recognisable generated-file names are never path
    # authority.  A task must declare every final changed path explicitly.
    auto_expanded: tuple[str, ...] = ()
    effective = declared
    unresolved = unexpected
    if hard_blocked:
        return _ScopeRecovery(declared, actual, unexpected, True, "blocked", auto_expanded, effective, unresolved)
    return _ScopeRecovery(
        declared, actual, unexpected, True,
        "trim_required", auto_expanded, effective, unresolved,
    )


def _apply_scope_recovery_after_mutating_execution(
    root: Path,
    profile: Any,
    execution_head: str,
    declared_allowed_changed_paths: tuple[str, ...],
    effective_allowed_changed_paths: tuple[str, ...],
    *,
    task_id: str | None,
) -> _AppliedScopeRecovery:
    """Collect, recover, and re-check scope after one mutating Codex phase.

    This deliberately reuses the established classifier and exact-base trim.
    It neither expands scope nor validates: callers retain their phase-specific
    validation and bounded rework budgets.
    """
    snapshot = analyze_repository_state(root)
    changed = _actual_changed_paths(snapshot)
    baseline = tuple(sorted(set(effective_allowed_changed_paths)))
    recovery = _recover_safe_changed_path_scope(
        root,
        baseline,
        changed,
        task_id=task_id,
        untracked_files=snapshot.untracked_files,
    )
    if recovery.scope_recovery_status == "blocked":
        return _AppliedScopeRecovery("forbidden_path", recovery, ())
    trimmed: tuple[str, ...] = ()
    if recovery.unresolved_unexpected_changed_files:
        trimmed = _trim_unexpected_changed_paths(
            root, execution_head, snapshot,
            recovery.unresolved_unexpected_changed_files,
        )
    final_snapshot = analyze_repository_state(root)
    final_changed = _actual_changed_paths(final_snapshot)
    if len(final_changed) > profile.max_changed_files:
        return _AppliedScopeRecovery("max_changed_files_exceeded", recovery, trimmed)
    if set(final_changed) - set(recovery.effective_allowed_changed_paths):
        return _AppliedScopeRecovery("out_of_scope", recovery, trimmed)
    return _AppliedScopeRecovery("passed", recovery, trimmed)


def _execution_base_blob(root: Path, execution_head: str, path: str) -> tuple[bytes, int] | None:
    """Return one exact regular-file blob and mode, or ``None`` when absent."""
    listing = _git_bytes(root, "ls-tree", "-z", execution_head, "--", path)
    if listing.returncode:
        raise OSError("execution base tree unavailable")
    entries = tuple(item for item in listing.stdout.split(b"\0") if item)
    if not entries:
        return None
    if len(entries) != 1 or b"\t" not in entries[0]:
        raise OSError("execution base path ambiguous")
    metadata, recorded_path = entries[0].split(b"\t", 1)
    fields = metadata.split()
    if recorded_path != os.fsencode(path) or len(fields) != 3 or fields[1] != b"blob" or fields[0] not in {b"100644", b"100755"}:
        raise OSError("execution base path unsafe")
    payload = _git_bytes(root, "cat-file", "blob", fields[2].decode("ascii"))
    if payload.returncode:
        raise OSError("execution base blob unavailable")
    return payload.stdout, int(fields[0], 8)


def _restore_execution_base_file(root: Path, path: str, payload: bytes, mode: int) -> None:
    """Atomically restore one exact regular file without broad Git mutation."""
    candidate = root / path
    if candidate.is_symlink() or (candidate.exists() and not candidate.is_file()):
        raise OSError("trim target is not a regular file")
    candidate.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".scope-trim-", suffix=".tmp", dir=candidate.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), mode & 0o777)
        os.replace(temporary, candidate)
    finally:
        if temporary.exists():
            temporary.unlink()


def _trim_unexpected_changed_paths(
    root: Path,
    execution_head: str,
    snapshot: Any,
    unexpected_paths: tuple[str, ...],
) -> tuple[str, ...]:
    """Return normal unauthorized paths exactly to the execution-base state."""
    untracked = frozenset(snapshot.untracked_files)
    trimmed: list[str] = []
    for raw in unexpected_paths:
        path = _normalized_repository_relative_path(root, raw)
        if path is None or path != raw or _is_scope_untrimmable_path(path):
            raise OSError("trim target unsafe")
        candidate = root / path
        base = _execution_base_blob(root, execution_head, path)
        if base is None:
            if raw not in untracked or candidate.is_symlink() or not candidate.is_file():
                raise OSError("trim target is not an exact new regular file")
            candidate.unlink()
        else:
            _restore_execution_base_file(root, path, *base)
        trimmed.append(path)
    return tuple(trimmed)


def _build_scope_constrained_rework_prompt(original_task: str, allowed_paths: tuple[str, ...]) -> str:
    """Use the existing adapter once without giving it any new path authority."""
    return (
        "Mode: Repair\n"
        "Goal: satisfy the original task after the runner removed unauthorized changes.\n"
        "Allowed files: " + ", ".join(allowed_paths) + ".\n"
        "Forbidden files/actions: do not recreate trimmed unauthorized paths, create or modify any other path, authorize paths, or redesign "
        "the task or broaden architecture; do not stage, commit, push, merge, or tag.\n"
        "Expected result: a valid implementation entirely within the listed allowed files.\n"
        "Validation: the runner will run its existing validation contract; run no unrelated validation.\n"
        "Out of scope: any path-authority expansion or unrelated architecture change.\n\n"
        "Original task for context:\n" + original_task
    )


def _evaluation_worktree_fingerprint(root: Path, snapshot: Any) -> tuple[dict[str, Any], tuple[tuple[str, str], ...]]:
    """Capture state plus content identity for evaluator-mutation detection."""
    identities: list[tuple[str, str]] = []
    for relative in sorted(set(snapshot.tracked_modified_files) | set(snapshot.untracked_files)):
        candidate = root / relative
        digest = hashlib.sha256()
        try:
            if candidate.is_symlink():
                value = "symlink:" + os.readlink(candidate)
                identities.append((relative, value))
                continue
            if not candidate.is_file():
                identities.append((relative, "not_regular"))
                continue
            with candidate.open("rb") as stream:
                for chunk in iter(lambda: stream.read(65536), b""):
                    digest.update(chunk)
            identities.append((relative, digest.hexdigest()))
        except OSError:
            identities.append((relative, "unreadable"))
    return repository_state_to_mapping(snapshot), tuple(identities)


def run_repository_single_task(
    repository_id: str,
    task_spec_path: str | os.PathLike[str] | None,
    *,
    registry_path: str | os.PathLike[str] = "config/repos.yaml",
    bindings_path: str | os.PathLike[str] | None = DEFAULT_REPOSITORY_BINDINGS_PATH,
    providers_path: str | os.PathLike[str] = "config/providers.yaml",
    output_root: str | os.PathLike[str] = DEFAULT_REPOSITORY_SINGLE_TASK_OUTPUT_ROOT,
    adapter_resolver: Callable[[], Any] | None = None,
    evaluator_runner: Callable[..., Any] | None = None,
    execution_base_sha: str | None = None,
    requested_run_id: str | None = None,
    task_spec_override: RepositorySingleTaskSpec | None = None,
) -> RepositorySingleTaskRunResult:
    """Process exactly one task, returning a receipt-backed terminal result.

    Dependency injection is intentionally limited to the adapter resolver for
    isolated tests; production resolves ``codex_cli`` from the providers file.
    """
    started = _utc_now()
    run_id = requested_run_id if requested_run_id is not None else "run-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    if not isinstance(run_id, str) or not re.fullmatch(r"run-[a-z0-9-]{1,80}", run_id):
        raise RepositorySingleTaskControllerError("single_task.run_id.invalid", "invalid requested run ID")
    output_directory = Path(output_root).expanduser() / run_id
    output_directory.mkdir(parents=True, exist_ok=False)

    spec: Any = None
    profile: Any = None
    source_before: Any = None
    source_after: Any = None
    worktree_state: Any = None
    source_root: str | None = None
    source_branch: str | None = None
    source_head: str | None = None
    execution_head: str | None = None
    task_id: str | None = None
    profile_id: str | None = None
    specification_sha: str | None = None
    worktree: Path | None = None
    worktree_preserved = False
    branch_created = False
    task_branch: str | None = None
    commit_sha: str | None = None
    commit_parent: str | None = None
    changed_files: tuple[str, ...] = ()
    adapter_name: str | None = None
    execution_status: str | None = None
    validation_status: str | None = None
    validation_reason: str | None = None
    retry_attempted = False
    retry_outcome: str | None = None
    validation_attempts: list[dict[str, Any]] = []
    repair_summary: dict[str, Any] = {"attempted": False, "max_attempts": 2, "attempts_used": 0, "outcome": "not_attempted"}
    cleanup_status = "not_started"
    task_completion_attempts: list[dict[str, Any]] = []
    final_task_completion: TaskCompletionEvaluation | None = None
    evaluation_reached = False
    declared_allowed_changed_paths: tuple[str, ...] = ()
    original_unexpected_changed_files: tuple[str, ...] = ()
    scope_recovery_attempted = False
    scope_recovery_status = "not_needed"
    auto_expanded_paths: tuple[str, ...] = ()
    effective_allowed_changed_paths: tuple[str, ...] = ()
    scope_repair_attempted = False
    scope_repair_target_paths: tuple[str, ...] = ()
    scope_repair_status = "not_needed"
    scope_trim_attempted = False
    scope_trimmed_paths: tuple[str, ...] = ()
    scope_trim_status = "not_needed"
    post_trim_validation_status: str | None = None
    scope_constrained_rework_attempted = False
    scope_constrained_rework_status = "not_needed"
    scope_extension_required = False
    scope_extension_required_paths: tuple[str, ...] = ()

    def scope_extension_block_reason() -> str:
        nonlocal scope_extension_required, scope_extension_required_paths
        candidates = _scope_extension_candidate_paths(original_unexpected_changed_files)
        if candidates:
            scope_extension_required = True
            scope_extension_required_paths = candidates
            return "single_task.scope_extension_required"
        return "single_task.task_scope.recovery_exhausted"

    def record(status: str, reason: str, detail: str | None = None) -> RepositorySingleTaskRunResult:
        nonlocal source_after, worktree_state, changed_files
        try:
            source_after = analyze_repository_state(source_root) if source_root else None
        except (OSError, ValueError):
            source_after = None
        if worktree is not None and worktree.exists():
            try:
                worktree_state = analyze_repository_state(worktree)
                changed_files = _actual_changed_paths(worktree_state)
            except (OSError, ValueError):
                pass
        finished = _utc_now()
        receipt_path = output_directory / "receipt.json"
        sha_path = output_directory / "receipt.sha256"
        paths = {
            "receipt": str(receipt_path),
            "receipt_sha256": str(sha_path),
            "pre_source_state": str(output_directory / "pre_source_state.json"),
            "post_source_state": str(output_directory / "post_source_state.json"),
            "worktree_state": str(output_directory / "worktree_state.json"),
            "execution_summary": str(output_directory / "execution_summary.json"),
            "changed_files": str(output_directory / "changed_files.json"),
            "validation_attempts": str(output_directory / "validation_attempts.json"),
            "task_completion_evaluation": str(output_directory / "task_completion_evaluation.json"),
            "task_completion_attempts": str(output_directory / "task_completion_attempts.json"),
        }
        receipt = {
            "schema_version": "1", "run_id": run_id, "status": status,
            "reason_code": reason, "detail_reason_code": detail,
            "repository_id": repository_id, "task_id": task_id,
            "task_spec_sha256": specification_sha, "source_repository_root": source_root,
            "profile_id": profile_id,
            "profile_base_branch": getattr(profile, "base_branch", None),
            "profile_max_changed_files": getattr(profile, "max_changed_files", None),
            "approvals": asdict(profile.approval_boundary) if profile is not None else {},
            "source_state_before": repository_state_to_mapping(source_before) if source_before else None,
            "source_state_after": repository_state_to_mapping(source_after) if source_after else None,
            "expected_head_sha": getattr(spec, "expected_head_sha", None),
            "worktree_path": str(worktree) if worktree else None,
            "worktree_preserved": worktree_preserved, "task_branch": task_branch,
            "adapter_name": adapter_name, "execution_status": execution_status,
            "validation_status": validation_status, "validation_reason": validation_reason,
            "retry_attempted": retry_attempted, "retry_outcome": retry_outcome,
            "changed_files": list(changed_files),
            "allowed_changed_paths": list(getattr(spec, "allowed_changed_paths", ())),
            "declared_allowed_changed_paths": list(declared_allowed_changed_paths),
            "actual_changed_files": list(changed_files),
            "original_unexpected_changed_files": list(original_unexpected_changed_files),
            "scope_recovery_attempted": scope_recovery_attempted,
            "scope_recovery_status": scope_recovery_status,
            "auto_expanded_paths": list(auto_expanded_paths),
            "effective_allowed_changed_paths": list(effective_allowed_changed_paths),
            "unresolved_unexpected_changed_files": sorted(set(changed_files) - set(effective_allowed_changed_paths)),
            "scope_repair_attempted": scope_repair_attempted,
            "scope_repair_target_paths": list(scope_repair_target_paths),
            "scope_repair_status": scope_repair_status,
            "scope_trim_attempted": scope_trim_attempted,
            "scope_trimmed_paths": list(scope_trimmed_paths),
            "scope_trim_status": scope_trim_status,
            "post_trim_validation_status": post_trim_validation_status,
            "scope_constrained_rework_attempted": scope_constrained_rework_attempted,
            "scope_constrained_rework_status": scope_constrained_rework_status,
            "scope_extension_required": scope_extension_required,
            "scope_extension_required_paths": list(scope_extension_required_paths),
            "commit_created": commit_sha is not None, "commit_sha": commit_sha,
            "commit_parent_sha": commit_parent,
            "commit_message": getattr(spec, "commit_message", None),
            "worktree_cleanup_status": cleanup_status, "artifact_paths": paths,
            "started_at": started, "finished_at": finished,
        }
        try:
            _atomic_json(Path(paths["pre_source_state"]), receipt["source_state_before"])
            _atomic_json(Path(paths["post_source_state"]), receipt["source_state_after"])
            _atomic_json(Path(paths["worktree_state"]), {
                "path": str(worktree) if worktree else None,
                "head": getattr(worktree_state, "head_sha", None),
                "branch": getattr(worktree_state, "branch", None),
                "staged_files": list(getattr(worktree_state, "staged_files", ())),
                "operations": list(getattr(worktree_state, "operations_in_progress", ())),
                "changed_files": list(changed_files), "preserved": worktree_preserved,
            })
            _atomic_json(Path(paths["execution_summary"]), {
                "adapter_name": adapter_name, "execution_status": execution_status,
                "validation_status": validation_status, "validation_reason": validation_reason,
                "retry_attempted": retry_attempted, "retry_outcome": retry_outcome,
                "repair": repair_summary,
                "task_completion": {
                    "reached": evaluation_reached,
                    "final_status": final_task_completion.status if final_task_completion else None,
                    "reason_code": final_task_completion.reason_code if final_task_completion else None,
                    "attempts": len(task_completion_attempts),
                },
            })
            _atomic_json(Path(paths["validation_attempts"]), {"repair": repair_summary, "validation_attempts": validation_attempts})
            if evaluation_reached:
                _atomic_json(Path(paths["task_completion_evaluation"]), task_completion_evaluation_to_mapping(final_task_completion) if final_task_completion else {})
                _atomic_json(Path(paths["task_completion_attempts"]), {"attempts": task_completion_attempts})
            _atomic_json(Path(paths["changed_files"]), {
                "allowed_changed_paths": receipt["allowed_changed_paths"],
                "declared_allowed_changed_paths": receipt["declared_allowed_changed_paths"],
                "actual_changed_files": list(changed_files),
                "unexpected_changed_files": sorted(set(changed_files) - set(receipt["allowed_changed_paths"])),
                "original_unexpected_changed_files": receipt["original_unexpected_changed_files"],
                "scope_recovery_attempted": receipt["scope_recovery_attempted"],
                "scope_recovery_status": receipt["scope_recovery_status"],
                "auto_expanded_paths": receipt["auto_expanded_paths"],
                "effective_allowed_changed_paths": receipt["effective_allowed_changed_paths"],
                "unresolved_unexpected_changed_files": receipt["unresolved_unexpected_changed_files"],
                "scope_repair_attempted": receipt["scope_repair_attempted"],
                "scope_repair_target_paths": receipt["scope_repair_target_paths"],
                "scope_repair_status": receipt["scope_repair_status"],
                "scope_trim_attempted": receipt["scope_trim_attempted"],
                "scope_trimmed_paths": receipt["scope_trimmed_paths"],
                "scope_trim_status": receipt["scope_trim_status"],
                "post_trim_validation_status": receipt["post_trim_validation_status"],
                "scope_constrained_rework_attempted": receipt["scope_constrained_rework_attempted"],
                "scope_constrained_rework_status": receipt["scope_constrained_rework_status"],
                "scope_extension_required": receipt["scope_extension_required"],
                "scope_extension_required_paths": receipt["scope_extension_required_paths"],
                "staged_files": list(getattr(worktree_state, "staged_files", ())),
                "commit_changed_files": list(changed_files) if commit_sha else [],
            })
            if commit_sha:
                paths["commit"] = str(output_directory / "commit.json")
                receipt["artifact_paths"] = paths
                _atomic_json(Path(paths["commit"]), {
                    "commit_sha": commit_sha, "parent_sha": commit_parent,
                    "branch": task_branch, "message": getattr(spec, "commit_message", None),
                    "changed_files": list(changed_files),
                })
            _atomic_json(receipt_path, receipt)
            digest = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
            sha_path.write_text(f"{digest}  receipt.json\n", encoding="utf-8")
            if not json.loads(receipt_path.read_text(encoding="utf-8")):
                raise OSError("receipt readback failed")
        except (OSError, TypeError, ValueError):
            status, reason, detail = "failed", "single_task.receipt.write_failed", None
        return RepositorySingleTaskRunResult(
            "1", run_id, status, reason, detail, repository_id, task_id, source_root,
            source_branch, source_head, getattr(source_after, "head_sha", source_head),
            profile_id, specification_sha, str(worktree) if worktree else None,
            worktree_preserved, task_branch, commit_sha, commit_parent, changed_files,
            adapter_name, execution_status, validation_status, validation_reason,
            retry_attempted, retry_outcome, str(receipt_path), str(sha_path), started, finished,
        )

    try:
        if (task_spec_path is None) == (task_spec_override is None):
            raise ValueError("exactly one task spec source is required")
        if task_spec_override is not None:
            spec = validate_repository_single_task_spec(task_spec_override)
            specification_sha = hashlib.sha256(
                serialize_repository_single_task_spec(spec).encode("utf-8")
            ).hexdigest()
        else:
            spec = load_repository_single_task_spec(task_spec_path)
            specification_sha = hashlib.sha256(Path(task_spec_path).read_bytes()).hexdigest()
        task_id = spec.task_id
        declared_allowed_changed_paths = spec.allowed_changed_paths
        effective_allowed_changed_paths = declared_allowed_changed_paths
    except (OSError, ValueError):
        return record("blocked", "single_task.task_spec.invalid")
    try:
        registry = load_repository_registry(registry_path, bindings_path)
        resolved = resolve_repository(registry, repository_id)
        profile = resolved.profile
        source_root = profile.repository_root
        profile_id = profile.profile_id
    except (OSError, ValueError):
        return record("blocked", "single_task.repository.resolve_failed")

    for action in ("code_changes", "test_execution", "artifact_generation", "stage", "commit"):
        if getattr(profile.approval_boundary, action) != "automatic":
            return record("blocked", f"single_task.approval.{action}_not_automatic")
    if len(spec.allowed_changed_paths) > profile.max_changed_files:
        return record("blocked", "single_task.scope.allowed_paths_limit_exceeded")
    if profile.max_changed_files - len(spec.allowed_changed_paths) < profile.min_repair_headroom:
        return record("blocked", "single_task.scope.repair_headroom_insufficient")
    try:
        source_before = analyze_repository_state(source_root)
    except (OSError, ValueError):
        return record("blocked", "single_task.source.dirty")
    source_branch, source_head = source_before.branch, source_before.head_sha
    if source_before.repository_root != source_root:
        return record("blocked", "single_task.source.repository_root_mismatch")
    if source_before.detached_head:
        return record("blocked", "single_task.source.detached_head")
    if source_branch != profile.base_branch:
        return record("blocked", "single_task.source.branch_mismatch")
    if source_head != spec.expected_head_sha:
        return record("blocked", "single_task.source.head_mismatch")
    if source_before.conflicted_files:
        return record("blocked", "single_task.source.conflicted")
    if source_before.operations_in_progress:
        return record("blocked", "single_task.source.operation_in_progress")
    if not _is_clean(source_before):
        return record("blocked", "single_task.source.dirty")

    execution_head = source_head if execution_base_sha is None else execution_base_sha
    if not isinstance(execution_head, str) or not re.fullmatch(r"[0-9a-f]{40}", execution_head):
        return record("blocked", "single_task.execution_base.invalid")
    try:
        is_commit = _git(source_root, "cat-file", "-e", f"{execution_head}^{{commit}}").returncode == 0
        is_descendant = _git(source_root, "merge-base", "--is-ancestor", source_head, execution_head).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        is_commit = is_descendant = False
    if not is_commit:
        return record("blocked", "single_task.execution_base.not_found")
    if not is_descendant:
        return record("blocked", "single_task.execution_base.not_descendant")

    task_branch = f"codex-task/{repository_id}/{spec.task_id}"
    if _git(source_root, "show-ref", "--verify", "--quiet", f"refs/heads/{task_branch}").returncode == 0:
        return record("blocked", "single_task.task_branch.exists")
    worktree = output_directory / "worktree"
    try:
        prepared = _git(source_root, "worktree", "add", "--detach", str(worktree), execution_head)
    except (OSError, subprocess.TimeoutExpired):
        return record("failed", "single_task.worktree.prepare_failed")
    if prepared.returncode:
        return record("failed", "single_task.worktree.prepare_failed")
    try:
        worktree_state = analyze_repository_state(worktree)
    except (OSError, ValueError):
        worktree_preserved = True
        return record("blocked", "single_task.worktree.initial_state_invalid")
    if not worktree_state.detached_head or worktree_state.head_sha != execution_head or not _is_clean(worktree_state):
        worktree_preserved = True
        return record("blocked", "single_task.worktree.initial_state_invalid")
    try:
        bound_profile = bind_repository_profile_to_worktree(profile, worktree)
    except (OSError, ValueError):
        worktree_preserved = True
        return record("blocked", "single_task.profile_binding.failed")
    try:
        if adapter_resolver is not None:
            adapter = adapter_resolver()
        else:
            from orchestrator.config_loader import load_yaml_file
            adapter = resolve_adapter("codex_cli", load_yaml_file(providers_path))
        adapter_name = getattr(adapter, "name", "codex_cli")
    except (OSError, ValueError, TypeError):
        worktree_preserved = True
        return record("blocked", "single_task.provider.resolve_failed")
    if not callable(getattr(adapter, "execute_prepared_worktree", None)):
        worktree_preserved = True
        return record("blocked", "single_task.adapter.prepared_surface_missing")
    try:
        response = adapter.execute_prepared_worktree({
            "prompt": spec.prompt, "worktree_path": str(worktree), "work_dir": str(output_directory),
            "repository_profile": bound_profile, "allowed_changed_paths": spec.allowed_changed_paths,
            "controller_managed_validation": True,
            **({"execution_timeout_seconds": spec.execution_timeout_seconds}
               if spec.execution_timeout_seconds is not None else {}),
            **({"validation_timeout_seconds": spec.validation_timeout_seconds}
               if spec.validation_timeout_seconds is not None else {}),
        })
    except Exception:
        worktree_preserved = True
        return record("failed", "single_task.execution.not_completed")
    if not isinstance(response, dict):
        worktree_preserved = True
        return record("blocked", "single_task.validation.failed")
    execution_status = response.get("status")
    verify = response.get("verify")
    retry_data = response.get("retry")
    raw_validation_attempts = response.get("validation_attempts", [])
    raw_repair = response.get("repair", repair_summary)
    controller_managed_validation = response.get("validation_deferred") is True
    if not isinstance(verify, dict) or not isinstance(retry_data, dict):
        worktree_preserved = True
        return record("blocked", "single_task.validation.failed")
    validation_reason = verify.get("reason")
    safe_validation = verify.get("safe_validation")
    validation_status = safe_validation.get("status") if isinstance(safe_validation, dict) else None
    retry_attempted = bool(retry_data.get("attempted"))
    retry_outcome = retry_data.get("outcome")
    validation_attempts = _safe_validation_attempts(raw_validation_attempts)
    if isinstance(raw_repair, dict):
        repair_summary = {key: raw_repair[key] for key in ("attempted", "max_attempts", "attempts_used", "outcome") if key in raw_repair}
    if execution_status != "completed":
        worktree_preserved = True
        return record("blocked", "single_task.execution.not_completed")
    if not controller_managed_validation and validation_reason == "validation_partial":
        worktree_preserved = True
        return record("blocked", "single_task.validation.partial")
    if not controller_managed_validation and validation_reason == "safe_validation_executor_error":
        worktree_preserved = True
        return record("blocked", "single_task.validation.executor_error")
    if not controller_managed_validation and not (verify.get("status") == "passed" and validation_reason == "validation_passed" and validation_status == "passed" and retry_outcome in {"not_attempted", "retry_succeeded"}):
        worktree_preserved = True
        return record("blocked", "single_task.validation.failed")

    try:
        applied_scope = _apply_scope_recovery_after_mutating_execution(
            worktree, profile, execution_head, declared_allowed_changed_paths,
            effective_allowed_changed_paths, task_id=task_id,
        )
    except (OSError, ValueError):
        worktree_preserved = True
        return record("blocked", "single_task.changed_files.out_of_scope")
    scope_recovery = applied_scope.recovery
    original_unexpected_changed_files = scope_recovery.original_unexpected_changed_files
    scope_recovery_attempted = scope_recovery.scope_recovery_attempted
    scope_recovery_status = scope_recovery.scope_recovery_status
    auto_expanded_paths = scope_recovery.auto_expanded_paths
    effective_allowed_changed_paths = scope_recovery.effective_allowed_changed_paths
    if applied_scope.status == "max_changed_files_exceeded":
        worktree_preserved = True
        return record("blocked", "single_task.changed_files.limit_exceeded")
    if applied_scope.status != "passed":
        worktree_preserved = True
        return record("blocked", "single_task.changed_files.out_of_scope")
    if applied_scope.trimmed_paths:
        scope_trim_attempted = True
        scope_trimmed_paths = applied_scope.trimmed_paths
        scope_trim_status = "succeeded"
        scope_recovery_status = "trim_succeeded"
        try:
            post_trim_validation = execute_repository_validation(
                bound_profile,
                timeout_seconds=(
                    spec.validation_timeout_seconds
                    if spec.validation_timeout_seconds is not None
                    else bound_profile.validation_timeout_seconds
                ),
            )
        except SafeValidationExecutorError:
            scope_trim_status = "failed"
            worktree_preserved = True
            return record("blocked", "single_task.changed_files.out_of_scope")
        post_trim_validation_status = post_trim_validation.status
        validation_status = post_trim_validation.status
        validation_reason = "validation_passed" if post_trim_validation.status == "passed" else "validation_failed"
        validation_attempts = [{
            "attempt_number": 1, "phase": "scope_trim", "execution_status": "completed",
            "validation_status": post_trim_validation.status, "validation_reason": validation_reason,
        }]
        if post_trim_validation.status != "passed":
            scope_constrained_rework_attempted = True
            try:
                response = adapter.execute_prepared_worktree({
                    "prompt": _build_scope_constrained_rework_prompt(spec.prompt, effective_allowed_changed_paths),
                    "worktree_path": str(worktree), "work_dir": str(output_directory),
                    "repository_profile": bound_profile,
                    "allowed_changed_paths": effective_allowed_changed_paths,
                    "controller_managed_validation": True,
                    "execution_timeout_seconds": _phase_timeout(
                        spec.completion_rework_timeout_seconds,
                        bound_profile.completion_rework_timeout_seconds,
                        DEFAULT_COMPLETION_REWORK_TIMEOUT_SECONDS,
                    ),
                    **({"validation_timeout_seconds": spec.validation_timeout_seconds}
                       if spec.validation_timeout_seconds is not None else {}),
                })
            except Exception:
                scope_constrained_rework_status = "failed"
                worktree_preserved = True
                return record("blocked", "single_task.execution.not_completed")
            if not isinstance(response, dict):
                scope_constrained_rework_status = "failed"
                worktree_preserved = True
                return record("blocked", "single_task.execution.not_completed")
            verify, retry_data = response.get("verify"), response.get("retry")
            if not isinstance(verify, dict) or not isinstance(retry_data, dict) or response.get("status") != "completed":
                scope_constrained_rework_status = "failed"
                worktree_preserved = True
                return record("blocked", "single_task.execution.not_completed")
            try:
                rework_scope = _apply_scope_recovery_after_mutating_execution(
                    worktree, profile, execution_head, declared_allowed_changed_paths,
                    effective_allowed_changed_paths, task_id=task_id,
                )
                if rework_scope.status != "passed":
                    raise OSError("scope rework left unauthorized changes")
                scope_trimmed_paths = tuple(sorted(
                    set(scope_trimmed_paths) | set(rework_scope.trimmed_paths)
                ))
                final_validation = execute_repository_validation(
                    bound_profile,
                    timeout_seconds=(
                        spec.validation_timeout_seconds
                        if spec.validation_timeout_seconds is not None
                        else bound_profile.validation_timeout_seconds
                    ),
                )
            except (OSError, ValueError, SafeValidationExecutorError):
                scope_constrained_rework_status = "failed"
                worktree_preserved = True
                return record("blocked", "single_task.changed_files.out_of_scope")
            post_trim_validation_status = final_validation.status
            validation_status = final_validation.status
            validation_reason = "validation_passed" if final_validation.status == "passed" else "validation_failed"
            validation_attempts = [{"attempt_number": 1, "phase": "scope_constrained_rework", "execution_status": "completed", "validation_status": final_validation.status, "validation_reason": validation_reason}]
            if final_validation.status != "passed":
                scope_constrained_rework_status = "failed"
                worktree_preserved = True
                return record("blocked", scope_extension_block_reason())
            scope_constrained_rework_status = "succeeded"

    if controller_managed_validation:
        validation_timeout = (
            spec.validation_timeout_seconds
            if spec.validation_timeout_seconds is not None
            else bound_profile.validation_timeout_seconds
        )
        try:
            initial_validation = execute_repository_validation(
                bound_profile, timeout_seconds=validation_timeout,
            )
        except SafeValidationExecutorError:
            worktree_preserved = True
            return record("blocked", "single_task.validation.retry_exhausted", "executor_error")
        initial_entry, classification = _validation_attempt_from_result(
            attempt_number=len(validation_attempts) + 1,
            phase="initial",
            repair_attempt_number=None,
            result=initial_validation,
            scope_status="passed",
        )
        validation_attempts.append(initial_entry)
        validation_status = initial_validation.status
        validation_reason = initial_entry["validation_reason"]
        if initial_validation.status != "passed":
            if classification is None:
                worktree_preserved = True
                return record("blocked", "single_task.validation.unknown_failure")
            if classification.retryable:
                retry_attempted = True
                try:
                    retry_validation = execute_repository_validation(
                        bound_profile, timeout_seconds=validation_timeout,
                    )
                except SafeValidationExecutorError:
                    retry_outcome = "retry_failed"
                    worktree_preserved = True
                    return record("blocked", "single_task.validation.retry_exhausted", "executor_error")
                retry_entry, retry_classification = _validation_attempt_from_result(
                    attempt_number=len(validation_attempts) + 1,
                    phase="retry",
                    repair_attempt_number=None,
                    result=retry_validation,
                    scope_status="passed",
                )
                validation_attempts.append(retry_entry)
                validation_status = retry_validation.status
                validation_reason = retry_entry["validation_reason"]
                if retry_validation.status == "passed":
                    retry_outcome = "retry_succeeded"
                else:
                    retry_outcome = "retry_failed"
                    worktree_preserved = True
                    detail = retry_classification.failure_class if retry_classification else "unknown"
                    return record("blocked", "single_task.validation.retry_exhausted", detail)
            elif not classification.auto_repairable:
                worktree_preserved = True
                reason = (
                    "single_task.validation.unknown_failure"
                    if classification.failure_class == "unknown"
                    else "single_task.validation.non_repairable"
                )
                return record("blocked", reason, classification.failure_class)
            else:
                repair_summary = {
                    "attempted": True,
                    "max_attempts": MAX_VALIDATION_REPAIR_ATTEMPTS,
                    "attempts_used": 0,
                    "outcome": "in_progress",
                }
                current_classification = classification
                current_failure = extract_actionable_failure(
                    validation_execution_result_to_mapping(initial_validation)
                )
                for repair_number in range(1, MAX_VALIDATION_REPAIR_ATTEMPTS + 1):
                    repair_summary["attempts_used"] = repair_number
                    try:
                        repair_response = adapter.execute_prepared_worktree({
                            "prompt": build_repair_prompt(
                                spec.prompt,
                                repair_number,
                                current_failure or {
                                    "command_id": current_classification.failed_command_ids[0],
                                    "kind": current_classification.failure_class,
                                    "status": "failed", "return_code": None,
                                    "reason_code": "validation_repair.classified_failure",
                                    "stdout_tail": "", "stderr_tail": "",
                                },
                                effective_allowed_changed_paths,
                                classification=current_classification,
                                current_changed_paths=_actual_changed_paths(analyze_repository_state(worktree)),
                                remaining_repair_budget=MAX_VALIDATION_REPAIR_ATTEMPTS - repair_number,
                            ),
                            "worktree_path": str(worktree), "work_dir": str(output_directory),
                            "repository_profile": bound_profile,
                            "allowed_changed_paths": effective_allowed_changed_paths,
                            "controller_managed_validation": True,
                            "execution_timeout_seconds": _phase_timeout(
                                spec.completion_rework_timeout_seconds,
                                bound_profile.completion_rework_timeout_seconds,
                                DEFAULT_COMPLETION_REWORK_TIMEOUT_SECONDS,
                            ),
                        })
                    except Exception:
                        repair_summary["outcome"] = "repair_execution_failed"
                        worktree_preserved = True
                        return record("blocked", "single_task.validation.repair_exhausted", "repair_execution_failed")
                    if not isinstance(repair_response, dict) or repair_response.get("status") != "completed":
                        repair_summary["outcome"] = "repair_execution_failed"
                        worktree_preserved = True
                        return record("blocked", "single_task.validation.repair_exhausted", "repair_execution_failed")
                    try:
                        repair_scope = _apply_scope_recovery_after_mutating_execution(
                            worktree, profile, execution_head,
                            declared_allowed_changed_paths,
                            effective_allowed_changed_paths, task_id=task_id,
                        )
                    except (OSError, ValueError):
                        repair_scope = None
                    repair_scope_status = repair_scope.status if repair_scope is not None else "worktree_state_invalid"
                    if repair_scope is not None:
                        if repair_scope.recovery.scope_recovery_attempted:
                            original_unexpected_changed_files = tuple(sorted(
                                set(original_unexpected_changed_files)
                                | set(repair_scope.recovery.original_unexpected_changed_files)
                            ))
                            scope_recovery_attempted = True
                            scope_recovery_status = "trim_succeeded" if repair_scope.trimmed_paths else repair_scope.recovery.scope_recovery_status
                        scope_trimmed_paths = tuple(sorted(
                            set(scope_trimmed_paths) | set(repair_scope.trimmed_paths)
                        ))
                        if repair_scope.trimmed_paths:
                            scope_trim_attempted, scope_trim_status = True, "succeeded"
                    if repair_scope_status != "passed":
                        scope_classification = ValidationFailureClassification(
                            "scope_failure", False, False, (), (), True,
                            ("repair.scope:" + repair_scope_status,),
                        )
                        validation_attempts.append({
                            "attempt_number": len(validation_attempts) + 1,
                            "phase": "repair",
                            "repair_attempt_number": repair_number,
                            "execution_status": "completed",
                            "validation_status": "not_run",
                            "validation_reason": "validation_not_run_scope_violation",
                            "scope_status": repair_scope_status,
                            "classification": validation_failure_classification_to_mapping(scope_classification),
                        })
                        repair_summary["outcome"] = "repair_scope_violation"
                        worktree_preserved = True
                        return record("blocked", "single_task.validation_repair.scope_violation", repair_scope_status)
                    try:
                        repaired_validation = execute_repository_validation(
                            bound_profile, timeout_seconds=validation_timeout,
                        )
                    except SafeValidationExecutorError:
                        repair_summary["outcome"] = "repair_validation_executor_error"
                        worktree_preserved = True
                        return record("blocked", "single_task.validation.repair_exhausted", "executor_error")
                    repair_entry, repaired_classification = _validation_attempt_from_result(
                        attempt_number=len(validation_attempts) + 1,
                        phase="repair",
                        repair_attempt_number=repair_number,
                        result=repaired_validation,
                        scope_status="passed",
                    )
                    validation_attempts.append(repair_entry)
                    validation_status = repaired_validation.status
                    validation_reason = repair_entry["validation_reason"]
                    if repaired_validation.status == "passed":
                        repair_summary["outcome"] = "repair_succeeded"
                        break
                    if repaired_classification is None or not repaired_classification.auto_repairable:
                        repair_summary["outcome"] = "repair_non_repairable"
                        worktree_preserved = True
                        detail = repaired_classification.failure_class if repaired_classification else "unknown"
                        return record("blocked", "single_task.validation.non_repairable", detail)
                    current_classification = repaired_classification
                    current_failure = extract_actionable_failure(
                        validation_execution_result_to_mapping(repaired_validation)
                    )
                else:
                    repair_summary["outcome"] = "repair_exhausted"
                    worktree_preserved = True
                    return record("blocked", "single_task.validation.repair_exhausted")

    # Completion rework starts only after deterministic validation succeeds.
    # Its subsequent validation is controller-managed and recorded separately
    # from validation repair, preserving the three distinct recovery states.
    for evaluation_number in range(1, MAX_TASK_REWORK_ATTEMPTS + 2):
        try:
            pre_evaluation = analyze_repository_state(worktree)
        except (OSError, ValueError):
            worktree_preserved = True
            return record("blocked", "single_task.task_completion.blocked", "state_unavailable")
        pre_evaluation_fingerprint = _evaluation_worktree_fingerprint(worktree, pre_evaluation)
        evaluation_changed = _actual_changed_paths(pre_evaluation)
        bounded_diff = _git(worktree, "diff", "--no-ext-diff", "--", *evaluation_changed).stdout[:8192]
        artifact_requirements: dict[str, Any] = {}
        for requirement in profile.artifact_requirements:
            candidate = worktree / requirement.path
            artifact_requirements[requirement.artifact_id] = {
                "path": requirement.path, "required": requirement.required,
                "exists": candidate.exists(), "expected_type": requirement.expected_type,
            }
        artifact_evidence = {
            "requirements": artifact_requirements,
            "changed_artifacts": _completion_changed_artifact_evidence(
                worktree, pre_evaluation, effective_allowed_changed_paths,
            ),
        }
        prompt = build_task_completion_evaluator_prompt(
            original_task=spec.prompt, allowed_changed_paths=effective_allowed_changed_paths,
            changed_paths=evaluation_changed,
            repository_state=repository_state_to_mapping(pre_evaluation),
            diff_evidence=bounded_diff,
            validation_evidence={"status": validation_status, "reason": validation_reason, "attempts": validation_attempts[-1:]},
            artifact_evidence=artifact_evidence,
        )
        evaluation_reached = True
        final_task_completion = execute_task_completion_evaluator(
            worktree_path=str(worktree), run_root=str(output_directory / "task_completion_evaluation_runs"),
            prompt=prompt,
            timeout_seconds=_phase_timeout(spec.completion_evaluator_timeout_seconds, bound_profile.completion_evaluator_timeout_seconds, DEFAULT_COMPLETION_EVALUATOR_TIMEOUT_SECONDS),
            **({"runner": evaluator_runner} if evaluator_runner is not None else {}),
        )
        try:
            post_evaluation = analyze_repository_state(worktree)
        except (OSError, ValueError):
            post_evaluation = None
        mutation = post_evaluation is None or pre_evaluation_fingerprint != _evaluation_worktree_fingerprint(worktree, post_evaluation)
        attempt: dict[str, Any] = {
            "evaluation_number": evaluation_number,
            "effective_timeout_seconds": _phase_timeout(spec.completion_evaluator_timeout_seconds, bound_profile.completion_evaluator_timeout_seconds, DEFAULT_COMPLETION_EVALUATOR_TIMEOUT_SECONDS),
            **task_completion_evaluation_to_mapping(final_task_completion),
            "rework_attempted": False, "rework_validation_status": None, "rework_validation_reason": None,
        }
        task_completion_attempts.append(attempt)
        if mutation:
            final_task_completion = TaskCompletionEvaluation("blocked", "task_completion.worktree_mutated", (), (), ())
            task_completion_attempts[-1].update(task_completion_evaluation_to_mapping(final_task_completion))
            worktree_preserved = True
            return record("blocked", "single_task.task_completion.blocked", "evaluator_worktree_mutated")
        if final_task_completion.status == "completed":
            break
        if final_task_completion.status == "blocked":
            worktree_preserved = True
            return record("blocked", "single_task.task_completion.blocked", final_task_completion.reason_code)
        if scope_trim_attempted and scope_constrained_rework_attempted:
            worktree_preserved = True
            return record("blocked", "single_task.task_scope.recovery_exhausted")
        if evaluation_number > MAX_TASK_REWORK_ATTEMPTS:
            worktree_preserved = True
            return record("blocked", "single_task.task_completion.rework_exhausted")
        attempt["rework_attempted"] = True
        if scope_trim_attempted:
            scope_constrained_rework_attempted = True
            rework_prompt = _build_scope_constrained_rework_prompt(
                spec.prompt, effective_allowed_changed_paths,
            )
        else:
            rework_prompt = build_task_completion_rework_prompt(
                original_task=spec.prompt, allowed_changed_paths=effective_allowed_changed_paths,
                evaluation=final_task_completion,
            )
        try:
            response = adapter.execute_prepared_worktree({
                "prompt": rework_prompt, "worktree_path": str(worktree), "work_dir": str(output_directory),
                "repository_profile": bound_profile, "allowed_changed_paths": effective_allowed_changed_paths,
                "controller_managed_validation": True,
                "execution_timeout_seconds": _phase_timeout(spec.completion_rework_timeout_seconds, bound_profile.completion_rework_timeout_seconds, DEFAULT_COMPLETION_REWORK_TIMEOUT_SECONDS),
                **({"validation_timeout_seconds": spec.validation_timeout_seconds}
                   if spec.validation_timeout_seconds is not None else {}),
            })
        except Exception:
            worktree_preserved = True
            return record("failed", "single_task.execution.not_completed")
        if not isinstance(response, dict):
            worktree_preserved = True
            return record("blocked", "single_task.validation.failed")
        execution_status, verify, retry_data = response.get("status"), response.get("verify"), response.get("retry")
        raw_validation_attempts, raw_repair = response.get("validation_attempts", []), response.get("repair", repair_summary)
        completion_rework_validation_deferred = response.get("validation_deferred") is True
        if not isinstance(verify, dict) or not isinstance(retry_data, dict):
            worktree_preserved = True
            return record("blocked", "single_task.validation.failed")
        validation_reason = verify.get("reason")
        safe_validation = verify.get("safe_validation")
        validation_status = safe_validation.get("status") if isinstance(safe_validation, dict) else None
        if not completion_rework_validation_deferred:
            retry_attempted, retry_outcome = bool(retry_data.get("attempted")), retry_data.get("outcome")
            validation_attempts = _safe_validation_attempts(raw_validation_attempts)
        if not completion_rework_validation_deferred and isinstance(raw_repair, dict):
            repair_summary = {key: raw_repair[key] for key in ("attempted", "max_attempts", "attempts_used", "outcome") if key in raw_repair}
        attempt["rework_validation_status"], attempt["rework_validation_reason"] = validation_status, validation_reason
        if execution_status != "completed":
            worktree_preserved = True
            return record("blocked", "single_task.execution.not_completed")
        if not completion_rework_validation_deferred and validation_reason == "validation_partial":
            worktree_preserved = True
            return record("blocked", "single_task.validation.partial")
        if not completion_rework_validation_deferred and validation_reason == "safe_validation_executor_error":
            worktree_preserved = True
            return record("blocked", "single_task.validation.executor_error")
        if not completion_rework_validation_deferred and not (verify.get("status") == "passed" and validation_reason == "validation_passed" and validation_status == "passed" and retry_outcome in {"not_attempted", "retry_succeeded"}):
            worktree_preserved = True
            return record("blocked", "single_task.validation.failed")
        try:
            completion_scope = _apply_scope_recovery_after_mutating_execution(
                worktree, profile, execution_head,
                declared_allowed_changed_paths,
                effective_allowed_changed_paths, task_id=task_id,
            )
        except (OSError, ValueError):
            completion_scope = None
        if completion_scope is None or completion_scope.status != "passed":
            worktree_preserved = True
            return record("blocked", "single_task.changed_files.out_of_scope")
        if completion_scope.recovery.scope_recovery_attempted:
            original_unexpected_changed_files = tuple(sorted(
                set(original_unexpected_changed_files)
                | set(completion_scope.recovery.original_unexpected_changed_files)
            ))
            scope_recovery_attempted = True
            scope_recovery_status = "trim_succeeded" if completion_scope.trimmed_paths else completion_scope.recovery.scope_recovery_status
        if completion_scope.trimmed_paths:
            scope_trim_attempted, scope_trim_status = True, "succeeded"
            scope_trimmed_paths = tuple(sorted(
                set(scope_trimmed_paths) | set(completion_scope.trimmed_paths)
            ))
        if completion_rework_validation_deferred:
            try:
                completion_validation = execute_repository_validation(
                    bound_profile,
                    timeout_seconds=(
                        spec.validation_timeout_seconds
                        if spec.validation_timeout_seconds is not None
                        else bound_profile.validation_timeout_seconds
                    ),
                )
            except SafeValidationExecutorError:
                worktree_preserved = True
                return record("blocked", "single_task.validation.executor_error")
            completion_entry, _ = _validation_attempt_from_result(
                attempt_number=len(validation_attempts) + 1,
                phase="completion_rework_validation",
                repair_attempt_number=None,
                result=completion_validation,
                scope_status="passed",
            )
            validation_attempts.append(completion_entry)
            validation_status, validation_reason = completion_validation.status, completion_entry["validation_reason"]
            attempt["rework_validation_status"] = validation_status
            attempt["rework_validation_reason"] = validation_reason
            if completion_validation.status != "passed":
                worktree_preserved = True
                return record("blocked", "single_task.validation.failed", "completion_rework_validation_failed")
        if scope_trim_attempted:
            try:
                final_scope = _apply_scope_recovery_after_mutating_execution(
                    worktree, profile, execution_head,
                    declared_allowed_changed_paths,
                    effective_allowed_changed_paths, task_id=task_id,
                )
                if final_scope.status != "passed":
                    raise OSError("scope-constrained rework left unauthorized changes")
                scope_trimmed_paths = tuple(sorted(
                    set(scope_trimmed_paths) | set(final_scope.trimmed_paths)
                ))
                final_validation = execute_repository_validation(
                    bound_profile,
                    timeout_seconds=(
                        spec.validation_timeout_seconds
                        if spec.validation_timeout_seconds is not None
                        else bound_profile.validation_timeout_seconds
                    ),
                )
            except (OSError, ValueError, SafeValidationExecutorError):
                scope_constrained_rework_status = "failed"
                worktree_preserved = True
                return record("blocked", "single_task.changed_files.out_of_scope")
            post_trim_validation_status = final_validation.status
            validation_status = final_validation.status
            validation_reason = "validation_passed" if final_validation.status == "passed" else "validation_failed"
            validation_attempts = [{
                "attempt_number": 1, "phase": "scope_constrained_rework",
                "execution_status": "completed", "validation_status": final_validation.status,
                "validation_reason": validation_reason,
            }]
            attempt["rework_validation_status"] = validation_status
            attempt["rework_validation_reason"] = validation_reason
            if final_validation.status != "passed":
                scope_constrained_rework_status = "failed"
                worktree_preserved = True
                return record("blocked", scope_extension_block_reason())
            scope_constrained_rework_status = "succeeded"

    worktree_state = analyze_repository_state(worktree)
    if worktree_state.head_sha != execution_head:
        worktree_preserved = True
        return record("blocked", "single_task.codex.head_changed")
    if not worktree_state.detached_head:
        worktree_preserved = True
        return record("blocked", "single_task.codex.branch_changed")
    if worktree_state.staged_files:
        worktree_preserved = True
        return record("blocked", "single_task.codex.staged_changes")
    if worktree_state.operations_in_progress:
        worktree_preserved = True
        return record("blocked", "single_task.codex.operation_in_progress")
    changed_files = _actual_changed_paths(worktree_state)
    if not changed_files:
        cleanup = _git(source_root, "worktree", "remove", str(worktree))
        cleanup_status = "removed" if cleanup.returncode == 0 else "failed"
        worktree_preserved = cleanup.returncode != 0
        return record("blocked", "single_task.changed_files.none")
    if len(changed_files) > profile.max_changed_files:
        worktree_preserved = True
        return record("blocked", "single_task.changed_files.limit_exceeded")
    if set(changed_files) - set(effective_allowed_changed_paths):
        worktree_preserved = True
        return record("blocked", "single_task.changed_files.out_of_scope")
    root_path = worktree.resolve()
    for changed_path in changed_files:
        candidate = worktree / changed_path
        try:
            if candidate.is_symlink() or not candidate.resolve(strict=False).is_relative_to(root_path):
                worktree_preserved = True
                return record("blocked", "single_task.changed_files.symlink_forbidden")
        except OSError:
            worktree_preserved = True
            return record("blocked", "single_task.changed_files.symlink_forbidden")

    if _git(worktree, "switch", "-c", task_branch).returncode:
        worktree_preserved = True
        return record("blocked", "single_task.branch.create_failed")
    branch_created = True
    if _git(worktree, "add", "--", *changed_files).returncode:
        worktree_preserved = True
        return record("blocked", "single_task.stage.failed")
    worktree_state = analyze_repository_state(worktree)
    if set(worktree_state.staged_files) != set(changed_files) or worktree_state.tracked_modified_files or worktree_state.untracked_files or worktree_state.conflicted_files or worktree_state.operations_in_progress:
        worktree_preserved = True
        return record("blocked", "single_task.stage.state_mismatch")
    if _git(worktree, "commit", "-m", spec.commit_message).returncode:
        worktree_preserved = True
        return record("blocked", "single_task.commit.failed")
    commit_sha = _git(worktree, "rev-parse", "HEAD").stdout.strip()
    commit_parent = _git(worktree, "rev-parse", "HEAD^").stdout.strip()
    subject = _git(worktree, "log", "-1", "--format=%s").stdout.strip()
    committed_files = tuple(sorted(filter(None, _git(worktree, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").stdout.splitlines())))
    worktree_state = analyze_repository_state(worktree)
    if len(commit_sha) != 40 or commit_parent != execution_head or subject != spec.commit_message or committed_files != changed_files or worktree_state.branch != task_branch or not _is_clean(worktree_state):
        worktree_preserved = True
        return record("failed", "single_task.commit.contract_mismatch")
    source_after = analyze_repository_state(source_root)
    if source_after.branch != profile.base_branch or source_after.head_sha != source_head or not _is_clean(source_after) or source_after.operations_in_progress:
        worktree_preserved = True
        return record("failed", "single_task.source.changed_during_run")
    removed = _git(source_root, "worktree", "remove", str(worktree))
    if removed.returncode:
        worktree_preserved = True
        cleanup_status = "failed"
        return record("failed", "single_task.worktree.cleanup_failed")
    cleanup_status = "removed"
    return record("completed", "single_task.completed")


__all__ = [
    "DEFAULT_REPOSITORY_SINGLE_TASK_OUTPUT_ROOT", "MAX_TASK_REWORK_ATTEMPTS",
    "RepositorySingleTaskControllerError", "RepositorySingleTaskRunResult",
    "repository_single_task_run_result_to_mapping", "run_repository_single_task",
    "serialize_repository_single_task_run_result",
]
