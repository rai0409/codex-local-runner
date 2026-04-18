from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Mapping

LANE_DETERMINISTIC_PYTHON = "deterministic_python"
LANE_GITHUB_DETERMINISTIC = "github_deterministic"
LANE_LLM_BACKED = "llm_backed"

KNOWN_EXECUTION_LANES = {
    LANE_DETERMINISTIC_PYTHON,
    LANE_GITHUB_DETERMINISTIC,
    LANE_LLM_BACKED,
}

LLM_POLICY_DISALLOWED = "disallowed"
LLM_POLICY_FALLBACK_ONLY = "fallback_only"
LLM_POLICY_REQUIRED = "required"

KNOWN_LLM_POLICIES = {
    LLM_POLICY_DISALLOWED,
    LLM_POLICY_FALLBACK_ONLY,
    LLM_POLICY_REQUIRED,
}


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip().lower()
    return text if text else default


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


@dataclass(frozen=True)
class ActionAuthority:
    action_token: str
    default_lane: str
    fallback_lanes: tuple[str, ...]
    deterministic_only: bool
    llm_policy: str


def _authority(
    action_token: str,
    *,
    default_lane: str,
    fallback_lanes: tuple[str, ...] = (),
    deterministic_only: bool = False,
    llm_policy: str = LLM_POLICY_DISALLOWED,
) -> ActionAuthority:
    normalized_default = _normalize_text(default_lane, default="")
    if normalized_default not in KNOWN_EXECUTION_LANES:
        raise ValueError(f"invalid default lane for action '{action_token}': {default_lane}")
    normalized_fallback = tuple(
        lane for lane in (_normalize_text(item, default="") for item in fallback_lanes) if lane in KNOWN_EXECUTION_LANES
    )
    normalized_llm_policy = _normalize_text(llm_policy, default=LLM_POLICY_DISALLOWED)
    if normalized_llm_policy not in KNOWN_LLM_POLICIES:
        raise ValueError(f"invalid llm policy for action '{action_token}': {llm_policy}")
    return ActionAuthority(
        action_token=action_token,
        default_lane=normalized_default,
        fallback_lanes=normalized_fallback,
        deterministic_only=bool(deterministic_only),
        llm_policy=normalized_llm_policy,
    )


# Single source of truth for first-class action-token lane authority.
_ACTION_AUTHORITIES: dict[str, ActionAuthority] = {
    "same_prompt_retry": _authority(
        "same_prompt_retry",
        default_lane=LANE_LLM_BACKED,
        llm_policy=LLM_POLICY_REQUIRED,
    ),
    "repair_prompt_retry": _authority(
        "repair_prompt_retry",
        default_lane=LANE_LLM_BACKED,
        llm_policy=LLM_POLICY_REQUIRED,
    ),
    "signal_recollect": _authority(
        "signal_recollect",
        default_lane=LANE_LLM_BACKED,
        llm_policy=LLM_POLICY_REQUIRED,
    ),
    "wait_for_checks": _authority(
        "wait_for_checks",
        default_lane=LANE_DETERMINISTIC_PYTHON,
        deterministic_only=True,
        llm_policy=LLM_POLICY_DISALLOWED,
    ),
    "prompt_recompile": _authority(
        "prompt_recompile",
        default_lane=LANE_LLM_BACKED,
        llm_policy=LLM_POLICY_REQUIRED,
    ),
    "roadmap_replan": _authority(
        "roadmap_replan",
        default_lane=LANE_LLM_BACKED,
        llm_policy=LLM_POLICY_REQUIRED,
    ),
    "escalate_to_human": _authority(
        "escalate_to_human",
        default_lane=LANE_DETERMINISTIC_PYTHON,
        deterministic_only=True,
        llm_policy=LLM_POLICY_DISALLOWED,
    ),
    "proceed_to_pr": _authority(
        "proceed_to_pr",
        default_lane=LANE_GITHUB_DETERMINISTIC,
        deterministic_only=True,
        llm_policy=LLM_POLICY_DISALLOWED,
    ),
    "github.pr.update": _authority(
        "github.pr.update",
        default_lane=LANE_GITHUB_DETERMINISTIC,
        deterministic_only=True,
        llm_policy=LLM_POLICY_DISALLOWED,
    ),
    "proceed_to_merge": _authority(
        "proceed_to_merge",
        default_lane=LANE_GITHUB_DETERMINISTIC,
        deterministic_only=True,
        llm_policy=LLM_POLICY_DISALLOWED,
    ),
    "rollback_required": _authority(
        "rollback_required",
        default_lane=LANE_GITHUB_DETERMINISTIC,
        deterministic_only=True,
        llm_policy=LLM_POLICY_DISALLOWED,
    ),
}

ALL_FIRST_CLASS_ACTION_TOKENS = tuple(
    authority.action_token for authority in sorted(_ACTION_AUTHORITIES.values(), key=lambda item: item.action_token)
)

# Additional operation-level classification for read/write GitHub paths.
_OPERATION_AUTHORITIES: dict[str, ActionAuthority] = {
    "github.read.get_default_branch": _authority(
        "github.read.get_default_branch",
        default_lane=LANE_GITHUB_DETERMINISTIC,
        deterministic_only=True,
        llm_policy=LLM_POLICY_DISALLOWED,
    ),
    "github.read.get_branch_head": _authority(
        "github.read.get_branch_head",
        default_lane=LANE_GITHUB_DETERMINISTIC,
        deterministic_only=True,
        llm_policy=LLM_POLICY_DISALLOWED,
    ),
    "github.read.compare_refs": _authority(
        "github.read.compare_refs",
        default_lane=LANE_GITHUB_DETERMINISTIC,
        deterministic_only=True,
        llm_policy=LLM_POLICY_DISALLOWED,
    ),
    "github.read.find_open_pr": _authority(
        "github.read.find_open_pr",
        default_lane=LANE_GITHUB_DETERMINISTIC,
        deterministic_only=True,
        llm_policy=LLM_POLICY_DISALLOWED,
    ),
    "github.read.get_pr_status_summary": _authority(
        "github.read.get_pr_status_summary",
        default_lane=LANE_GITHUB_DETERMINISTIC,
        deterministic_only=True,
        llm_policy=LLM_POLICY_DISALLOWED,
    ),
    "github.write.create_draft_pr": _authority(
        "github.write.create_draft_pr",
        default_lane=LANE_GITHUB_DETERMINISTIC,
        deterministic_only=True,
        llm_policy=LLM_POLICY_DISALLOWED,
    ),
    "github.write.update_existing_pr": _authority(
        "github.write.update_existing_pr",
        default_lane=LANE_GITHUB_DETERMINISTIC,
        deterministic_only=True,
        llm_policy=LLM_POLICY_DISALLOWED,
    ),
    "github.write.merge_pull_request": _authority(
        "github.write.merge_pull_request",
        default_lane=LANE_GITHUB_DETERMINISTIC,
        deterministic_only=True,
        llm_policy=LLM_POLICY_DISALLOWED,
    ),
    "github.write.rollback_path": _authority(
        "github.write.rollback_path",
        default_lane=LANE_GITHUB_DETERMINISTIC,
        deterministic_only=True,
        llm_policy=LLM_POLICY_DISALLOWED,
    ),
}


def get_action_authority(action_token: str) -> ActionAuthority | None:
    token = _normalize_text(action_token, default="")
    if not token:
        return None
    return _ACTION_AUTHORITIES.get(token)


def get_operation_authority(operation_token: str) -> ActionAuthority | None:
    token = _normalize_text(operation_token, default="")
    if not token:
        return None
    return _OPERATION_AUTHORITIES.get(token)


def _collect_requested_lanes(
    *,
    action_token: str,
    policy_snapshot: Mapping[str, Any] | None,
    handoff_payload: Mapping[str, Any] | None,
) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    action = _normalize_text(action_token, default="")

    if isinstance(handoff_payload, Mapping):
        per_action = _as_mapping(handoff_payload.get("requested_execution_lanes"))
        if isinstance(per_action, Mapping) and action:
            requested = _normalize_text(per_action.get(action), default="")
            if requested:
                candidates.append(("handoff.requested_execution_lanes", requested))
        requested = _normalize_text(handoff_payload.get("requested_execution_lane"), default="")
        if requested:
            candidates.append(("handoff.requested_execution_lane", requested))

    if isinstance(policy_snapshot, Mapping):
        per_action = _as_mapping(policy_snapshot.get("requested_execution_lanes"))
        if isinstance(per_action, Mapping) and action:
            requested = _normalize_text(per_action.get(action), default="")
            if requested:
                candidates.append(("policy_snapshot.requested_execution_lanes", requested))
        requested = _normalize_text(policy_snapshot.get("requested_execution_lane"), default="")
        if requested:
            candidates.append(("policy_snapshot.requested_execution_lane", requested))

    return candidates


def evaluate_action_authority(
    action_token: str,
    *,
    policy_snapshot: Mapping[str, Any] | None = None,
    handoff_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    authority = get_action_authority(action_token)
    if authority is None:
        return {
            "action_token": _normalize_text(action_token, default=""),
            "known_action": False,
            "allowed": False,
            "reason": "action_unclassified",
            "default_lane": None,
            "fallback_lanes": (),
            "deterministic_only": None,
            "llm_policy": None,
            "requested_lane": None,
            "requested_lane_source": None,
            "resolved_lane": None,
            "requested_lane_sources": [],
        }

    requested_candidates = _collect_requested_lanes(
        action_token=authority.action_token,
        policy_snapshot=policy_snapshot,
        handoff_payload=handoff_payload,
    )
    requested_lane_sources = [(source, lane) for source, lane in requested_candidates]
    unique_requested = sorted({lane for _, lane in requested_candidates if lane})
    if len(unique_requested) > 1:
        return {
            "action_token": authority.action_token,
            "known_action": True,
            "allowed": False,
            "reason": "requested_lane_conflict",
            "default_lane": authority.default_lane,
            "fallback_lanes": authority.fallback_lanes,
            "deterministic_only": authority.deterministic_only,
            "llm_policy": authority.llm_policy,
            "requested_lane": None,
            "requested_lane_source": None,
            "resolved_lane": None,
            "requested_lane_sources": requested_lane_sources,
        }

    requested_lane = unique_requested[0] if unique_requested else None
    requested_source = requested_candidates[-1][0] if requested_candidates else None
    resolved_lane = requested_lane or authority.default_lane

    if resolved_lane not in KNOWN_EXECUTION_LANES:
        return {
            "action_token": authority.action_token,
            "known_action": True,
            "allowed": False,
            "reason": "requested_lane_unknown",
            "default_lane": authority.default_lane,
            "fallback_lanes": authority.fallback_lanes,
            "deterministic_only": authority.deterministic_only,
            "llm_policy": authority.llm_policy,
            "requested_lane": requested_lane,
            "requested_lane_source": requested_source,
            "resolved_lane": None,
            "requested_lane_sources": requested_lane_sources,
        }

    if requested_lane is not None:
        allowed_requested = {authority.default_lane, *authority.fallback_lanes}
        if requested_lane not in allowed_requested:
            return {
                "action_token": authority.action_token,
                "known_action": True,
                "allowed": False,
                "reason": "requested_lane_not_allowed",
                "default_lane": authority.default_lane,
                "fallback_lanes": authority.fallback_lanes,
                "deterministic_only": authority.deterministic_only,
                "llm_policy": authority.llm_policy,
                "requested_lane": requested_lane,
                "requested_lane_source": requested_source,
                "resolved_lane": None,
                "requested_lane_sources": requested_lane_sources,
            }

    if authority.deterministic_only and resolved_lane == LANE_LLM_BACKED:
        return {
            "action_token": authority.action_token,
            "known_action": True,
            "allowed": False,
            "reason": "deterministic_only_action_disallows_llm",
            "default_lane": authority.default_lane,
            "fallback_lanes": authority.fallback_lanes,
            "deterministic_only": authority.deterministic_only,
            "llm_policy": authority.llm_policy,
            "requested_lane": requested_lane,
            "requested_lane_source": requested_source,
            "resolved_lane": None,
            "requested_lane_sources": requested_lane_sources,
        }

    if authority.llm_policy == LLM_POLICY_DISALLOWED and resolved_lane == LANE_LLM_BACKED:
        return {
            "action_token": authority.action_token,
            "known_action": True,
            "allowed": False,
            "reason": "llm_lane_disallowed_for_action",
            "default_lane": authority.default_lane,
            "fallback_lanes": authority.fallback_lanes,
            "deterministic_only": authority.deterministic_only,
            "llm_policy": authority.llm_policy,
            "requested_lane": requested_lane,
            "requested_lane_source": requested_source,
            "resolved_lane": None,
            "requested_lane_sources": requested_lane_sources,
        }

    if authority.llm_policy == LLM_POLICY_REQUIRED and resolved_lane != LANE_LLM_BACKED:
        return {
            "action_token": authority.action_token,
            "known_action": True,
            "allowed": False,
            "reason": "llm_lane_required_for_action",
            "default_lane": authority.default_lane,
            "fallback_lanes": authority.fallback_lanes,
            "deterministic_only": authority.deterministic_only,
            "llm_policy": authority.llm_policy,
            "requested_lane": requested_lane,
            "requested_lane_source": requested_source,
            "resolved_lane": None,
            "requested_lane_sources": requested_lane_sources,
        }

    return {
        "action_token": authority.action_token,
        "known_action": True,
        "allowed": True,
        "reason": "ok",
        "default_lane": authority.default_lane,
        "fallback_lanes": authority.fallback_lanes,
        "deterministic_only": authority.deterministic_only,
        "llm_policy": authority.llm_policy,
        "requested_lane": requested_lane,
        "requested_lane_source": requested_source,
        "resolved_lane": resolved_lane,
        "requested_lane_sources": requested_lane_sources,
    }

