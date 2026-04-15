from __future__ import annotations

from collections.abc import Callable
from collections.abc import Mapping
import os
from typing import Any


GITHUB_STATE_BACKEND_ENV_VAR = "CODEX_GITHUB_STATE_BACKEND"
_ALLOWED_CHECK_STATES = {"passing", "failing", "pending", "unknown"}
_ALLOWED_REVIEW_STATES = {"approved", "changes_requested", "pending", "unknown"}
_ALLOWED_MERGEABILITY_STATES = {
    "clean",
    "blocked",
    "behind",
    "dirty",
    "draft",
    "unknown",
}


GitHubLiveStateFetcher = Callable[..., Mapping[str, Any] | None]


class GitHubStateBackend:
    """Read-only abstraction for collecting GitHub progression signals."""

    name = "github_state_backend"

    def collect(
        self,
        *,
        request_payload: Mapping[str, Any],
        result_payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError("GitHub state backend must implement collect()")


class ArtifactGitHubStateBackend(GitHubStateBackend):
    """Collect GitHub state from existing request/result artifacts only."""

    name = "artifact_read_only"

    def collect(
        self,
        *,
        request_payload: Mapping[str, Any],
        result_payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        github_state, state_source = _extract_github_state(request_payload, result_payload)
        return _build_normalized_snapshot(
            backend_name=self.name,
            request_payload=request_payload,
            github_state=github_state,
            state_source=state_source,
            source_kind="artifact",
            source_metadata={
                "artifact_state_available": bool(github_state),
                "live_state_available": False,
            },
        )


class LiveReadOnlyGitHubStateBackend(GitHubStateBackend):
    """Optional live read-only backend with conservative artifact fallback."""

    name = "live_read_only"

    def __init__(
        self,
        *,
        fetch_state: GitHubLiveStateFetcher | None = None,
    ) -> None:
        self._fetch_state = fetch_state

    def collect(
        self,
        *,
        request_payload: Mapping[str, Any],
        result_payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        artifact_state, artifact_source = _extract_github_state(request_payload, result_payload)
        live_state, live_state_source, fetch_failed = self._collect_live_state(
            request_payload=request_payload,
            result_payload=result_payload,
            artifact_state=artifact_state,
        )

        extra_reasons: list[str] = []
        source_kind = "live_read_only"
        source_metadata = {
            "artifact_state_available": bool(artifact_state),
            "live_state_available": bool(live_state),
            "fallback_to_artifact": False,
        }
        effective_state = dict(live_state)
        state_source = live_state_source

        if not effective_state:
            extra_reasons.append("github_live_state_unavailable")
            if artifact_state:
                source_kind = "artifact_fallback"
                source_metadata["fallback_to_artifact"] = True
                effective_state = dict(artifact_state)
                state_source = f"artifact_fallback:{artifact_source}"
            else:
                source_kind = "none"
                state_source = (
                    "live.read_only_fetch_failed"
                    if fetch_failed
                    else "live.read_only_unavailable"
                )

        if fetch_failed:
            extra_reasons.append("github_live_state_fetch_failed")

        return _build_normalized_snapshot(
            backend_name=self.name,
            request_payload=request_payload,
            github_state=effective_state,
            state_source=state_source,
            source_kind=source_kind,
            source_metadata=source_metadata,
            extra_conservative_reasons=tuple(extra_reasons),
        )

    def _collect_live_state(
        self,
        *,
        request_payload: Mapping[str, Any],
        result_payload: Mapping[str, Any],
        artifact_state: Mapping[str, Any],
    ) -> tuple[dict[str, Any], str, bool]:
        if self._fetch_state is None:
            return {}, "live.read_only_not_configured", False
        target_hint = _derive_target(
            request_payload=request_payload,
            github_state=artifact_state,
        )
        try:
            fetched = self._fetch_state(
                target=target_hint,
                request_payload=request_payload,
                result_payload=result_payload,
            )
        except Exception:
            return {}, "live.read_only_fetch_failed", True
        if isinstance(fetched, Mapping):
            payload = dict(fetched)
            if payload:
                return payload, "live.read_only", False
        return {}, "live.read_only_unavailable", False


def resolve_github_state_backend(
    *,
    backend_mode: str | None = None,
    live_fetcher: GitHubLiveStateFetcher | None = None,
) -> GitHubStateBackend:
    normalized = _normalize_backend_mode(
        backend_mode if backend_mode is not None else os.getenv(GITHUB_STATE_BACKEND_ENV_VAR, "")
    )
    if normalized == "live_read_only":
        return LiveReadOnlyGitHubStateBackend(fetch_state=live_fetcher)
    return ArtifactGitHubStateBackend()


def build_github_progression_receipt(
    *,
    github_signals: Mapping[str, Any] | None,
    progression_state: str,
    policy_eligible: bool,
    auto_pr_candidate: bool,
) -> dict[str, Any]:
    fallback = ArtifactGitHubStateBackend().collect(request_payload={}, result_payload={})
    snapshot = _normalize_snapshot_shape(github_signals, fallback=fallback)

    progression = snapshot.get("progression")
    github_ready = (
        isinstance(progression, Mapping)
        and bool(progression.get("ready_for_policy_connection"))
    )

    policy_link = {
        "progression_state": str(progression_state),
        "policy_eligible": bool(policy_eligible),
        "auto_pr_candidate": bool(auto_pr_candidate),
        "ready_for_future_auto_pr_progression": bool(policy_eligible) and github_ready,
        "auto_pr_candidate_ready": bool(auto_pr_candidate) and github_ready,
    }

    receipt = dict(snapshot)
    receipt["policy_link"] = policy_link
    return receipt


def _build_normalized_snapshot(
    *,
    backend_name: str,
    request_payload: Mapping[str, Any],
    github_state: Mapping[str, Any],
    state_source: str,
    source_kind: str,
    source_metadata: Mapping[str, Any] | None = None,
    extra_conservative_reasons: tuple[str, ...] = (),
) -> dict[str, Any]:
    target = _derive_target(
        request_payload=request_payload,
        github_state=github_state,
    )
    checks = _derive_checks(github_state)
    review = _derive_review(github_state)
    mergeability = _derive_mergeability(github_state)

    conservative_reasons: list[str] = []
    state_available = bool(github_state)
    if not state_available:
        conservative_reasons.append("github_state_unavailable")

    if not target["repository"]:
        conservative_reasons.append("github_repository_missing")
    if not target["target_ref"]:
        conservative_reasons.append("github_target_ref_missing")

    if checks["state"] != "passing":
        conservative_reasons.append("github_required_checks_not_passing")
    if review["state"] != "approved":
        conservative_reasons.append("github_review_not_approved")

    mergeability_state = mergeability["state"]
    if mergeability_state != "clean":
        conservative_reasons.append("github_mergeability_not_clean")
    if mergeability["is_draft"] is True:
        conservative_reasons.append("github_pull_request_is_draft")

    for reason in extra_conservative_reasons:
        if reason not in conservative_reasons:
            conservative_reasons.append(reason)

    if not state_available:
        progression_state = "unavailable"
    elif conservative_reasons:
        progression_state = "blocked"
    else:
        progression_state = "ready"

    source = {
        "kind": str(source_kind).strip() or "none",
        "state_source": str(state_source).strip() or "none",
    }
    if isinstance(source_metadata, Mapping):
        for key, value in source_metadata.items():
            source[str(key)] = value

    return {
        "backend": str(backend_name).strip() or "unknown",
        "mode": "read_only",
        "write_actions_allowed": False,
        "state_available": state_available,
        "state_source": str(state_source).strip() or "none",
        "source": source,
        "target": target,
        "checks": checks,
        "review": review,
        "mergeability": mergeability,
        "progression": {
            "state": progression_state,
            "conservative_reasons": tuple(conservative_reasons),
            "ready_for_policy_connection": progression_state == "ready",
        },
    }


def _normalize_snapshot_shape(
    snapshot: Mapping[str, Any] | None,
    *,
    fallback: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(snapshot, Mapping):
        return dict(fallback)

    def _fallback_mapping(key: str) -> dict[str, Any]:
        value = fallback.get(key)
        if isinstance(value, Mapping):
            return dict(value)
        return {}

    def _mapping_or_default(key: str, default: Mapping[str, Any]) -> dict[str, Any]:
        value = snapshot.get(key)
        if isinstance(value, Mapping):
            return dict(value)
        return dict(default)

    normalized = {
        "backend": str(snapshot.get("backend", fallback.get("backend", "unknown"))).strip() or "unknown",
        "mode": "read_only",
        "write_actions_allowed": False,
        "state_available": bool(snapshot.get("state_available", False)),
        "state_source": str(snapshot.get("state_source", "none")).strip() or "none",
        "source": _mapping_or_default("source", _fallback_mapping("source")),
        "target": _mapping_or_default("target", _fallback_mapping("target")),
        "checks": _mapping_or_default("checks", _fallback_mapping("checks")),
        "review": _mapping_or_default("review", _fallback_mapping("review")),
        "mergeability": _mapping_or_default("mergeability", _fallback_mapping("mergeability")),
        "progression": _mapping_or_default("progression", _fallback_mapping("progression")),
    }

    progression = normalized["progression"]
    conservative_reasons = progression.get("conservative_reasons")
    if isinstance(conservative_reasons, (list, tuple)):
        progression["conservative_reasons"] = tuple(
            str(reason).strip() for reason in conservative_reasons if str(reason).strip()
        )
    else:
        progression["conservative_reasons"] = ()
    progression["state"] = str(progression.get("state", "unavailable")).strip() or "unavailable"
    progression["ready_for_policy_connection"] = bool(
        progression.get("ready_for_policy_connection", False)
    )
    return normalized


def _normalize_backend_mode(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"live", "live_read_only"}:
        return "live_read_only"
    return "artifact_read_only"


def _extract_github_state(
    request_payload: Mapping[str, Any],
    result_payload: Mapping[str, Any],
) -> tuple[dict[str, Any], str]:
    candidates = (
        ("result.github_state", _get_mapping(result_payload, "github_state")),
        ("result.github", _get_mapping(result_payload, "github")),
        (
            "result.metadata.github_state",
            _get_nested_mapping(result_payload, "metadata", "github_state"),
        ),
        ("result.metadata.github", _get_nested_mapping(result_payload, "metadata", "github")),
        ("request.github_state", _get_mapping(request_payload, "github_state")),
        ("request.github", _get_mapping(request_payload, "github")),
        (
            "request.metadata.github_state",
            _get_nested_mapping(request_payload, "metadata", "github_state"),
        ),
        (
            "request.metadata.github",
            _get_nested_mapping(request_payload, "metadata", "github"),
        ),
    )

    for source, payload in candidates:
        if payload:
            return payload, source
    return {}, "none"


def _derive_target(
    *,
    request_payload: Mapping[str, Any],
    github_state: Mapping[str, Any],
) -> dict[str, Any]:
    execution_target = _get_nested_mapping(request_payload, "metadata", "execution_target")

    repository = _first_non_empty(
        github_state.get("repository"),
        github_state.get("repo"),
        request_payload.get("repo"),
    )
    target_ref = _first_non_empty(
        github_state.get("target_ref"),
        github_state.get("base_ref"),
        github_state.get("base_branch"),
        execution_target.get("target_ref") if execution_target else None,
    )
    head_ref = _first_non_empty(
        github_state.get("head_ref"),
        github_state.get("head_branch"),
        github_state.get("source_branch"),
    )
    source_sha = _first_non_empty(
        github_state.get("source_sha"),
        execution_target.get("source_sha") if execution_target else None,
    )
    base_sha = _first_non_empty(
        github_state.get("base_sha"),
        execution_target.get("base_sha") if execution_target else None,
    )

    return {
        "repository": repository,
        "target_ref": target_ref,
        "head_ref": head_ref,
        "source_sha": source_sha,
        "base_sha": base_sha,
        "pr_number": _as_optional_int(github_state.get("pr_number")),
        "pr_url": _first_non_empty(github_state.get("pr_url"), github_state.get("url")),
    }


def _derive_checks(github_state: Mapping[str, Any]) -> dict[str, Any]:
    required = _normalize_string_list(github_state.get("required_checks"))
    passing = _normalize_string_list(github_state.get("passing_checks"))
    failing = _normalize_string_list(github_state.get("failing_checks"))
    pending = _normalize_string_list(github_state.get("pending_checks"))

    explicit_state = _normalize_choice(
        github_state.get("required_checks_state"),
        allowed=_ALLOWED_CHECK_STATES,
    )

    state = explicit_state
    if state is None:
        if failing:
            state = "failing"
        elif pending:
            state = "pending"
        elif required and set(required).issubset(set(passing)):
            state = "passing"
        else:
            state = "unknown"

    return {
        "state": state,
        "required": required,
        "passing": passing,
        "failing": failing,
        "pending": pending,
    }


def _derive_review(github_state: Mapping[str, Any]) -> dict[str, Any]:
    approvals = _as_non_negative_int(github_state.get("approvals"), default=0)
    changes_requested = _as_non_negative_int(github_state.get("changes_requested"), default=0)
    required_approvals = _as_optional_int(github_state.get("required_approvals"))

    explicit_state = _normalize_choice(
        github_state.get("review_state"),
        allowed=_ALLOWED_REVIEW_STATES,
    )
    state = explicit_state
    if state is None:
        if changes_requested > 0:
            state = "changes_requested"
        elif required_approvals is not None and required_approvals > 0 and approvals >= required_approvals:
            state = "approved"
        elif approvals > 0 and required_approvals in {None, 0}:
            state = "pending"
        elif approvals == 0:
            state = "pending"
        else:
            state = "unknown"

    return {
        "state": state,
        "approvals": approvals,
        "changes_requested": changes_requested,
        "required_approvals": required_approvals,
    }


def _derive_mergeability(github_state: Mapping[str, Any]) -> dict[str, Any]:
    is_mergeable = _as_optional_bool(
        github_state.get("is_mergeable", github_state.get("mergeable"))
    )
    is_draft = _as_optional_bool(github_state.get("is_draft"))

    explicit_state = _normalize_choice(
        github_state.get("mergeability_state"),
        allowed=_ALLOWED_MERGEABILITY_STATES,
    )
    state = explicit_state
    if state is None:
        if is_draft is True:
            state = "draft"
        elif is_mergeable is True:
            state = "clean"
        elif is_mergeable is False:
            state = "blocked"
        else:
            state = "unknown"

    return {
        "state": state,
        "is_mergeable": is_mergeable,
        "is_draft": is_draft,
    }


def _get_mapping(payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _get_nested_mapping(payload: Mapping[str, Any], parent: str, child: str) -> dict[str, Any]:
    parent_value = payload.get(parent)
    if not isinstance(parent_value, Mapping):
        return {}
    child_value = parent_value.get(child)
    if isinstance(child_value, Mapping):
        return dict(child_value)
    return {}


def _first_non_empty(*values: Any) -> str | None:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    items = sorted({str(item).strip() for item in value if str(item).strip()})
    return items


def _normalize_choice(value: Any, *, allowed: set[str]) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in allowed:
        return text
    return None


def _as_optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"1", "true", "yes"}:
            return True
        if text in {"0", "false", "no"}:
            return False
    return None


def _as_non_negative_int(value: Any, *, default: int) -> int:
    parsed = _as_optional_int(value)
    if parsed is None:
        return int(default)
    return max(parsed, 0)


def _as_optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped and stripped.lstrip("-").isdigit():
            return int(stripped)
    return None
