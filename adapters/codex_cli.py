from __future__ import annotations

from pathlib import Path
import shlex
from typing import Any

from adapters.base import ProviderAdapter
from automation.orchestration.repository_profile import RepositoryProfile
from automation.orchestration.repository_profile import RepositoryProfileValidationError
from automation.orchestration.repository_profile import validate_repository_profile
from automation.orchestration.repository_profile_binding import RepositoryProfileBindingError
from automation.orchestration.repository_profile_binding import bind_repository_profile_to_worktree
from automation.orchestration.safe_validation_executor import execute_repository_validation
from automation.orchestration.safe_validation_executor import SafeValidationExecutorError
from automation.orchestration.safe_validation_executor import validation_execution_result_to_mapping
from run_codex import run_codex
from workspace.worktree import cleanup_git_worktree
from workspace.worktree import prepare_git_worktree


def _not_run_reason_for_execution_status(execution_status: str) -> str:
    if execution_status == "not_started":
        return "validation_not_run_execution_status_not_started"
    if execution_status == "timed_out":
        return "validation_not_run_execution_status_timed_out"
    if execution_status == "failed":
        return "validation_not_run_execution_status_failed"
    return "validation_not_run_execution_status_unknown"


def _verify_not_run(reason: str) -> dict[str, Any]:
    return {
        "status": "not_run",
        "success": True,
        "commands": [],
        "error": "",
        "reason": reason,
    }


def _verify_from_safe_validation(result: Any) -> dict[str, Any]:
    mapping = validation_execution_result_to_mapping(result)
    commands = [shlex.join(item["argv"]) for item in mapping["command_results"]]
    command_results = [
        {"command": shlex.join(item["argv"]), "status": item["status"],
         "return_code": item["return_code"], "stdout": item["stdout"],
         "stderr": item["stderr"]}
        for item in mapping["command_results"]
    ]
    failed = sum(item["status"] != "passed" for item in mapping["command_results"])
    status = "passed" if mapping["status"] in {"passed", "partial"} else "failed"
    reason = "validation_partial" if mapping["status"] == "partial" else "validation_passed" if status == "passed" else "validation_failed"
    return {"status": status, "success": status == "passed", "commands": commands,
        "command_results": command_results,
        "summary": {"total": len(command_results), "passed": len(command_results) - failed, "failed": failed},
        "error": "" if status == "passed" else "safe validation failed",
        "reason": reason, "safe_validation": mapping}


def _retry_not_attempted() -> dict[str, Any]:
    return {
        "attempted": False,
        "trigger": "not_applicable",
        "outcome": "not_attempted",
    }


def _derive_result_interpretation(
    execution_status: str,
    verify_result: dict[str, Any],
    retry: dict[str, Any],
) -> str:
    if execution_status != "completed":
        return "execution_not_completed"

    verify_status = str(verify_result.get("status", "")).strip()
    retry_attempted = bool(retry.get("attempted"))
    retry_outcome = str(retry.get("outcome", "")).strip()

    if verify_status == "passed":
        if verify_result.get("reason") == "validation_partial":
            return "completed_verified_partial"
        if retry_attempted and retry_outcome == "retry_succeeded":
            return "completed_verified_passed_after_retry"
        return "completed_verified_passed"

    if verify_status == "failed":
        if retry_attempted and retry_outcome == "retry_failed":
            return "completed_verified_failed_after_retry"
        return "completed_verified_failed"

    if retry_attempted and retry_outcome == "retry_failed":
        return "completed_verified_failed_after_retry"
    return "completed_verified_passed"


def _derive_review_recommendation(result_interpretation: str) -> str:
    if result_interpretation == "completed_verified_passed":
        return "no_review_needed"
    if result_interpretation == "completed_verified_passed_after_retry":
        return "review_recommended"
    if result_interpretation == "completed_verified_partial":
        return "review_recommended"
    if result_interpretation == "completed_verified_failed_after_retry":
        return "review_recommended_after_retry_failure"
    if result_interpretation == "completed_verified_failed":
        return "review_recommended"
    if result_interpretation == "execution_not_completed":
        return "review_recommended"
    raise ValueError(f"unsupported result_interpretation: {result_interpretation}")


def _build_review_handoff_summary(
    *,
    final_status: str,
    final_verify_status: str,
    final_verify_reason: str,
    retry_attempted: bool,
    retry_outcome: str,
    result_interpretation: str,
    review_recommendation: str,
) -> dict[str, Any]:
    return {
        "final_status": final_status,
        "final_verify_status": final_verify_status,
        "final_verify_reason": final_verify_reason,
        "retry_attempted": retry_attempted,
        "retry_outcome": retry_outcome,
        "result_interpretation": result_interpretation,
        "review_recommendation": review_recommendation,
    }


def _build_reviewer_handoff(
    *,
    review_handoff_summary: dict[str, Any],
    final_status: str,
    attempt_count: int,
    return_code: int | None,
    verify_result: dict[str, Any],
) -> dict[str, Any]:
    validation: dict[str, Any] = {
        "verify_status": verify_result["status"],
        "verify_reason": verify_result["reason"],
    }
    if "summary" in verify_result:
        validation["summary"] = verify_result["summary"]

    reviewer_handoff = {
        "summary": review_handoff_summary,
        "execution": {
            "status": final_status,
            "attempt_count": attempt_count,
            "return_code": return_code,
        },
        "validation": validation,
    }
    return reviewer_handoff

class CodexCliAdapter(ProviderAdapter):
    def __init__(self) -> None:
        super().__init__(name="codex_cli")

    def dispatch(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("codex_cli provider execution is not implemented in Phase 1")

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        prompt = str(payload.get("prompt", "")).strip()
        work_dir = Path(str(payload.get("work_dir", ".")).strip() or ".")
        repo_path = str(Path(str(payload.get("repo_path", ".")).strip() or ".").expanduser())
        profile = payload.get("repository_profile")
        profile_error = ""
        if not isinstance(profile, RepositoryProfile):
            profile_error = "safe_validation.profile.invalid"
        else:
            try:
                profile = validate_repository_profile(profile)
                repository_root = Path(repo_path).resolve(strict=True)
            except (RepositoryProfileValidationError, OSError):
                profile_error = "safe_validation.profile.invalid"
            else:
                if repository_root != Path(profile.repository_root).resolve(strict=True):
                    profile_error = "safe_validation.profile_repository_mismatch"
                elif profile.approval_boundary.test_execution != "automatic":
                    profile_error = "safe_validation.test_execution_not_automatic"
        if profile_error:
            verify = _verify_not_run("validation_not_run_execution_status_failed")
            retry = _retry_not_attempted()
            summary = _build_review_handoff_summary(final_status="failed", final_verify_status=verify["status"], final_verify_reason=verify["reason"], retry_attempted=False, retry_outcome=retry["outcome"], result_interpretation="execution_not_completed", review_recommendation="review_recommended")
            return {"adapter": self.name, "status": "failed", "started_at": None, "finished_at": None,
                "artifacts": [], "error": profile_error, "return_code": None, "verify": verify,
                "attempt_count": 1, "retry": retry, "result_interpretation": "execution_not_completed",
                "review_recommendation": "review_recommended", "review_handoff_summary": summary,
                "reviewer_handoff": _build_reviewer_handoff(review_handoff_summary=summary, final_status="failed", attempt_count=1, return_code=None, verify_result=verify)}
        worktree_result = prepare_git_worktree(
            source_repo_path=repo_path,
            worktree_parent=str(work_dir / "worktrees"),
        )
        if not worktree_result["created"]:
            early_verify = _verify_not_run(reason="validation_not_run_execution_status_failed")
            early_retry = _retry_not_attempted()
            early_status = "failed"
            early_attempt_count = 1
            early_return_code = None
            early_result_interpretation = "execution_not_completed"
            early_review_recommendation = "review_recommended"
            review_handoff_summary = _build_review_handoff_summary(
                final_status=early_status,
                final_verify_status=early_verify["status"],
                final_verify_reason=early_verify["reason"],
                retry_attempted=early_retry["attempted"],
                retry_outcome=early_retry["outcome"],
                result_interpretation=early_result_interpretation,
                review_recommendation=early_review_recommendation,
            )
            reviewer_handoff = _build_reviewer_handoff(
                review_handoff_summary=review_handoff_summary,
                final_status=early_status,
                attempt_count=early_attempt_count,
                return_code=early_return_code,
                verify_result=early_verify,
            )
            return {
                "adapter": self.name,
                "status": early_status,
                "started_at": None,
                "finished_at": None,
                "artifacts": [],
                "error": worktree_result["error"] or "failed to prepare git worktree",
                "return_code": early_return_code,
                "verify": early_verify,
                "attempt_count": early_attempt_count,
                "retry": early_retry,
                "result_interpretation": early_result_interpretation,
                "review_recommendation": early_review_recommendation,
                "review_handoff_summary": review_handoff_summary,
                "reviewer_handoff": reviewer_handoff,
            }

        cleanup_error = ""
        attempt_count = 1
        retry = _retry_not_attempted()
        try:
            try:
                bound_profile = bind_repository_profile_to_worktree(
                    profile, worktree_result["worktree_path"]
                )
            except (RepositoryProfileBindingError, RepositoryProfileValidationError):
                execution_result = {
                    "status": "failed", "return_code": None, "started_at": None,
                    "finished_at": None, "artifacts": [],
                    "error": "safe_validation.profile.invalid",
                }
                execution_status = "failed"
                verify_result = _verify_not_run("validation_not_run_execution_status_failed")
            else:
                execution_result = run_codex(
                    task={"repo_path": worktree_result["worktree_path"]},
                    prompt=prompt,
                    work_root=str(work_dir / "execution_runs"),
                )
                execution_status = str(execution_result["status"])
                if execution_status == "completed":
                    try:
                        verify_result = _verify_from_safe_validation(
                            execute_repository_validation(bound_profile)
                        )
                    except SafeValidationExecutorError:
                        verify_result = _verify_not_run("validation_not_run_execution_status_failed")
                else:
                    verify_result = _verify_not_run(
                        reason=_not_run_reason_for_execution_status(execution_status),
                    )

            if execution_status == "completed" and verify_result.get("status") == "failed":
                attempt_count = 2
                retry = {
                    "attempted": True,
                    "trigger": "verify_failed",
                    "outcome": "retry_failed",
                }
                execution_result = run_codex(
                    task={"repo_path": worktree_result["worktree_path"]},
                    prompt=prompt,
                    work_root=str(work_dir / "execution_runs"),
                )
                execution_status = str(execution_result["status"])
                if execution_status == "completed":
                    try:
                        verify_result = _verify_from_safe_validation(
                            execute_repository_validation(bound_profile)
                        )
                    except SafeValidationExecutorError:
                        verify_result = _verify_not_run(
                            "validation_not_run_execution_status_failed"
                        )
                else:
                    verify_result = _verify_not_run(
                        reason=_not_run_reason_for_execution_status(execution_status),
                    )
                if verify_result.get("status") == "passed":
                    retry["outcome"] = "retry_succeeded"
        finally:
            if worktree_result["cleanup_needed"]:
                cleanup_result = cleanup_git_worktree(
                    source_repo_path=repo_path,
                    worktree_path=worktree_result["worktree_path"],
                    branch_name=worktree_result["branch_name"],
                )
                cleanup_error = cleanup_result["error"]

        artifacts: list[str] = []
        for item in execution_result["artifacts"]:
            if isinstance(item, dict):
                path = str(item.get("path", "")).strip()
                if path:
                    artifacts.append(path)

        execution_error = str(execution_result["error"]).strip()
        if cleanup_error and execution_status != "completed":
            if execution_error:
                execution_error = f"{execution_error}\nWorktree cleanup failed: {cleanup_error}"
            else:
                execution_error = f"Worktree cleanup failed: {cleanup_error}"

        result_interpretation = _derive_result_interpretation(
            execution_status=execution_status,
            verify_result=verify_result,
            retry=retry,
        )
        review_recommendation = _derive_review_recommendation(result_interpretation)
        final_verify_status = verify_result["status"]
        final_verify_reason = verify_result["reason"]
        retry_attempted = retry["attempted"]
        retry_outcome = retry["outcome"]
        review_handoff_summary = _build_review_handoff_summary(
            final_status=execution_status,
            final_verify_status=final_verify_status,
            final_verify_reason=final_verify_reason,
            retry_attempted=retry_attempted,
            retry_outcome=retry_outcome,
            result_interpretation=result_interpretation,
            review_recommendation=review_recommendation,
        )
        final_return_code = execution_result["return_code"]
        reviewer_handoff = _build_reviewer_handoff(
            review_handoff_summary=review_handoff_summary,
            final_status=execution_status,
            attempt_count=attempt_count,
            return_code=final_return_code,
            verify_result=verify_result,
        )
        return {
            "adapter": self.name,
            "status": execution_status,
            "started_at": execution_result["started_at"],
            "finished_at": execution_result["finished_at"],
            "artifacts": artifacts,
            "error": execution_error or None,
            "return_code": final_return_code,
            "verify": verify_result,
            "attempt_count": attempt_count,
            "retry": retry,
            "result_interpretation": result_interpretation,
            "review_recommendation": review_recommendation,
            "review_handoff_summary": review_handoff_summary,
            "reviewer_handoff": reviewer_handoff,
        }
