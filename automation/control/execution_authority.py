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

ROUTING_CLASS_EXECUTOR = "executor"
ROUTING_CLASS_RETRY = "retry"
ROUTING_CLASS_CONTROL = "control"

KNOWN_ROUTING_CLASSES = {
    ROUTING_CLASS_EXECUTOR,
    ROUTING_CLASS_RETRY,
    ROUTING_CLASS_CONTROL,
}

_REQUESTED_EXECUTION_KEY = "requested_execution"
_REQUESTED_LANE_KEY = "requested_lane"
_REQUESTED_LANES_KEY = "requested_lanes"
_LEGACY_REQUESTED_LANE_KEY = "requested_execution_lane"
_LEGACY_REQUESTED_LANES_KEY = "requested_execution_lanes"


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
    routing_class: str


def _authority(
    action_token: str,
    *,
    default_lane: str,
    fallback_lanes: tuple[str, ...] = (),
    deterministic_only: bool = False,
    llm_policy: str = LLM_POLICY_DISALLOWED,
    routing_class: str = ROUTING_CLASS_CONTROL,
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
    normalized_routing = _normalize_text(routing_class, default=ROUTING_CLASS_CONTROL)
    if normalized_routing not in KNOWN_ROUTING_CLASSES:
        raise ValueError(f"invalid routing class for action '{action_token}': {routing_class}")
    return ActionAuthority(
        action_token=action_token,
        default_lane=normalized_default,
        fallback_lanes=normalized_fallback,
        deterministic_only=bool(deterministic_only),
        llm_policy=normalized_llm_policy,
        routing_class=normalized_routing,
    )


# Single source of truth for first-class action-token lane authority.
_ACTION_AUTHORITIES: dict[str, ActionAuthority] = {
    "same_prompt_retry": _authority(
        "same_prompt_retry",
        default_lane=LANE_LLM_BACKED,
        llm_policy=LLM_POLICY_REQUIRED,
        routing_class=ROUTING_CLASS_RETRY,
    ),
    "repair_prompt_retry": _authority(
        "repair_prompt_retry",
        default_lane=LANE_LLM_BACKED,
        llm_policy=LLM_POLICY_REQUIRED,
        routing_class=ROUTING_CLASS_RETRY,
    ),
    "signal_recollect": _authority(
        "signal_recollect",
        default_lane=LANE_LLM_BACKED,
        llm_policy=LLM_POLICY_REQUIRED,
        routing_class=ROUTING_CLASS_RETRY,
    ),
    "wait_for_checks": _authority(
        "wait_for_checks",
        default_lane=LANE_DETERMINISTIC_PYTHON,
        deterministic_only=True,
        llm_policy=LLM_POLICY_DISALLOWED,
        routing_class=ROUTING_CLASS_RETRY,
    ),
    "prompt_recompile": _authority(
        "prompt_recompile",
        default_lane=LANE_LLM_BACKED,
        llm_policy=LLM_POLICY_REQUIRED,
        routing_class=ROUTING_CLASS_RETRY,
    ),
    "roadmap_replan": _authority(
        "roadmap_replan",
        default_lane=LANE_LLM_BACKED,
        llm_policy=LLM_POLICY_REQUIRED,
        routing_class=ROUTING_CLASS_RETRY,
    ),
    "escalate_to_human": _authority(
        "escalate_to_human",
        default_lane=LANE_DETERMINISTIC_PYTHON,
        deterministic_only=True,
        llm_policy=LLM_POLICY_DISALLOWED,
        routing_class=ROUTING_CLASS_CONTROL,
    ),
    "proceed_to_pr": _authority(
        "proceed_to_pr",
        default_lane=LANE_GITHUB_DETERMINISTIC,
        deterministic_only=True,
        llm_policy=LLM_POLICY_DISALLOWED,
        routing_class=ROUTING_CLASS_EXECUTOR,
    ),
    "github.pr.update": _authority(
        "github.pr.update",
        default_lane=LANE_GITHUB_DETERMINISTIC,
        deterministic_only=True,
        llm_policy=LLM_POLICY_DISALLOWED,
        routing_class=ROUTING_CLASS_EXECUTOR,
    ),
    "proceed_to_merge": _authority(
        "proceed_to_merge",
        default_lane=LANE_GITHUB_DETERMINISTIC,
        deterministic_only=True,
        llm_policy=LLM_POLICY_DISALLOWED,
        routing_class=ROUTING_CLASS_EXECUTOR,
    ),
    "rollback_required": _authority(
        "rollback_required",
        default_lane=LANE_GITHUB_DETERMINISTIC,
        deterministic_only=True,
        llm_policy=LLM_POLICY_DISALLOWED,
        routing_class=ROUTING_CLASS_EXECUTOR,
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
        routing_class=ROUTING_CLASS_CONTROL,
    ),
    "github.read.get_branch_head": _authority(
        "github.read.get_branch_head",
        default_lane=LANE_GITHUB_DETERMINISTIC,
        deterministic_only=True,
        llm_policy=LLM_POLICY_DISALLOWED,
        routing_class=ROUTING_CLASS_CONTROL,
    ),
    "github.read.compare_refs": _authority(
        "github.read.compare_refs",
        default_lane=LANE_GITHUB_DETERMINISTIC,
        deterministic_only=True,
        llm_policy=LLM_POLICY_DISALLOWED,
        routing_class=ROUTING_CLASS_CONTROL,
    ),
    "github.read.find_open_pr": _authority(
        "github.read.find_open_pr",
        default_lane=LANE_GITHUB_DETERMINISTIC,
        deterministic_only=True,
        llm_policy=LLM_POLICY_DISALLOWED,
        routing_class=ROUTING_CLASS_CONTROL,
    ),
    "github.read.get_pr_status_summary": _authority(
        "github.read.get_pr_status_summary",
        default_lane=LANE_GITHUB_DETERMINISTIC,
        deterministic_only=True,
        llm_policy=LLM_POLICY_DISALLOWED,
        routing_class=ROUTING_CLASS_CONTROL,
    ),
    "github.write.create_draft_pr": _authority(
        "github.write.create_draft_pr",
        default_lane=LANE_GITHUB_DETERMINISTIC,
        deterministic_only=True,
        llm_policy=LLM_POLICY_DISALLOWED,
        routing_class=ROUTING_CLASS_EXECUTOR,
    ),
    "github.write.update_existing_pr": _authority(
        "github.write.update_existing_pr",
        default_lane=LANE_GITHUB_DETERMINISTIC,
        deterministic_only=True,
        llm_policy=LLM_POLICY_DISALLOWED,
        routing_class=ROUTING_CLASS_EXECUTOR,
    ),
    "github.write.merge_pull_request": _authority(
        "github.write.merge_pull_request",
        default_lane=LANE_GITHUB_DETERMINISTIC,
        deterministic_only=True,
        llm_policy=LLM_POLICY_DISALLOWED,
        routing_class=ROUTING_CLASS_EXECUTOR,
    ),
    "github.write.rollback_path": _authority(
        "github.write.rollback_path",
        default_lane=LANE_GITHUB_DETERMINISTIC,
        deterministic_only=True,
        llm_policy=LLM_POLICY_DISALLOWED,
        routing_class=ROUTING_CLASS_EXECUTOR,
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
    normalized = normalize_requested_lane_input(
        action_token,
        policy_snapshot=policy_snapshot,
        handoff_payload=handoff_payload,
    )
    return list(normalized.get("requested_lane_sources", []))


def _surface_lane_candidates(
    *,
    surface_name: str,
    payload: Mapping[str, Any] | None,
    action_token: str,
) -> list[tuple[str, str]]:
    source = payload if isinstance(payload, Mapping) else {}
    action = _normalize_text(action_token, default="")
    candidates: list[tuple[str, str]] = []

    canonical = _as_mapping(source.get(_REQUESTED_EXECUTION_KEY)) or {}
    canonical_lanes = _as_mapping(canonical.get(_REQUESTED_LANES_KEY))
    if isinstance(canonical_lanes, Mapping) and action:
        lane = _normalize_text(canonical_lanes.get(action), default="")
        if lane:
            candidates.append((f"{surface_name}.{_REQUESTED_EXECUTION_KEY}.{_REQUESTED_LANES_KEY}", lane))
    lane = _normalize_text(canonical.get(_REQUESTED_LANE_KEY), default="")
    if lane:
        candidates.append((f"{surface_name}.{_REQUESTED_EXECUTION_KEY}.{_REQUESTED_LANE_KEY}", lane))

    legacy_lanes = _as_mapping(source.get(_LEGACY_REQUESTED_LANES_KEY))
    if isinstance(legacy_lanes, Mapping) and action:
        lane = _normalize_text(legacy_lanes.get(action), default="")
        if lane:
            candidates.append((f"{surface_name}.{_LEGACY_REQUESTED_LANES_KEY}", lane))
    lane = _normalize_text(source.get(_LEGACY_REQUESTED_LANE_KEY), default="")
    if lane:
        candidates.append((f"{surface_name}.{_LEGACY_REQUESTED_LANE_KEY}", lane))
    return candidates


def normalize_requested_lane_input(
    action_token: str,
    *,
    policy_snapshot: Mapping[str, Any] | None = None,
    handoff_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    action = _normalize_text(action_token, default="")
    policy_candidates = _surface_lane_candidates(
        surface_name="policy_snapshot",
        payload=policy_snapshot if isinstance(policy_snapshot, Mapping) else None,
        action_token=action,
    )
    handoff_candidates = _surface_lane_candidates(
        surface_name="handoff",
        payload=handoff_payload if isinstance(handoff_payload, Mapping) else None,
        action_token=action,
    )

    def _surface_value(candidates: list[tuple[str, str]]) -> tuple[str | None, str | None]:
        lanes = sorted({lane for _, lane in candidates if lane})
        if not lanes:
            return None, None
        if len(lanes) > 1:
            return None, "requested_lane_conflict"
        return lanes[0], None

    policy_lane, policy_conflict = _surface_value(policy_candidates)
    handoff_lane, handoff_conflict = _surface_value(handoff_candidates)
    conflict_reason: str | None = None
    if policy_conflict or handoff_conflict:
        conflict_reason = "requested_lane_conflict"
    elif policy_lane and handoff_lane and policy_lane != handoff_lane:
        conflict_reason = "requested_lane_conflict"

    requested_lane: str | None = None
    requested_lane_source: str | None = None
    requested_lane_sources = list(policy_candidates) + list(handoff_candidates)
    if conflict_reason is None:
        if policy_lane:
            requested_lane = policy_lane
            requested_lane_source = "policy_snapshot"
        elif handoff_lane:
            requested_lane = handoff_lane
            requested_lane_source = "handoff"

    fingerprint = (
        f"policy={policy_lane or '_'}|"
        f"handoff={handoff_lane or '_'}|"
        f"conflict={conflict_reason or '_'}"
    )
    return {
        "requested_lane": requested_lane,
        "requested_lane_source": requested_lane_source,
        "requested_lane_sources": requested_lane_sources,
        "policy_lane": policy_lane,
        "handoff_lane": handoff_lane,
        "conflict_reason": conflict_reason,
        "routing_input_fingerprint": fingerprint,
    }


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
            "routing_class": None,
            "requested_lane": None,
            "requested_lane_source": None,
            "resolved_lane": None,
            "requested_lane_sources": [],
        }

    normalized_requested = normalize_requested_lane_input(
        authority.action_token,
        policy_snapshot=policy_snapshot,
        handoff_payload=handoff_payload,
    )
    requested_lane_sources = list(normalized_requested.get("requested_lane_sources", []))
    conflict_reason = _normalize_text(normalized_requested.get("conflict_reason"), default="")
    if conflict_reason:
        return {
            "action_token": authority.action_token,
            "known_action": True,
            "allowed": False,
            "reason": conflict_reason,
            "default_lane": authority.default_lane,
            "fallback_lanes": authority.fallback_lanes,
            "deterministic_only": authority.deterministic_only,
            "llm_policy": authority.llm_policy,
            "routing_class": authority.routing_class,
            "requested_lane": None,
            "requested_lane_source": None,
            "resolved_lane": None,
            "requested_lane_sources": requested_lane_sources,
            "routing_input_fingerprint": _normalize_text(
                normalized_requested.get("routing_input_fingerprint"),
                default="",
            ),
        }

    requested_lane = _normalize_text(normalized_requested.get("requested_lane"), default="") or None
    requested_source = (
        _normalize_text(normalized_requested.get("requested_lane_source"), default="") or None
    )
    routing_input_fingerprint = _normalize_text(
        normalized_requested.get("routing_input_fingerprint"),
        default="",
    )
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
            "routing_class": authority.routing_class,
            "requested_lane": requested_lane,
            "requested_lane_source": requested_source,
            "resolved_lane": None,
            "requested_lane_sources": requested_lane_sources,
            "routing_input_fingerprint": routing_input_fingerprint,
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
                "routing_class": authority.routing_class,
                "requested_lane": requested_lane,
                    "requested_lane_source": requested_source,
                    "resolved_lane": None,
                    "requested_lane_sources": requested_lane_sources,
                    "routing_input_fingerprint": routing_input_fingerprint,
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
            "routing_class": authority.routing_class,
            "requested_lane": requested_lane,
            "requested_lane_source": requested_source,
            "resolved_lane": None,
            "requested_lane_sources": requested_lane_sources,
            "routing_input_fingerprint": routing_input_fingerprint,
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
            "routing_class": authority.routing_class,
            "requested_lane": requested_lane,
            "requested_lane_source": requested_source,
            "resolved_lane": None,
            "requested_lane_sources": requested_lane_sources,
            "routing_input_fingerprint": routing_input_fingerprint,
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
            "routing_class": authority.routing_class,
            "requested_lane": requested_lane,
            "requested_lane_source": requested_source,
            "resolved_lane": None,
            "requested_lane_sources": requested_lane_sources,
            "routing_input_fingerprint": routing_input_fingerprint,
        }

    if resolved_lane == LANE_LLM_BACKED and authority.routing_class != ROUTING_CLASS_RETRY:
        return {
            "action_token": authority.action_token,
            "known_action": True,
            "allowed": False,
            "reason": "llm_lane_disallowed_for_routing_class",
            "default_lane": authority.default_lane,
            "fallback_lanes": authority.fallback_lanes,
            "deterministic_only": authority.deterministic_only,
            "llm_policy": authority.llm_policy,
            "routing_class": authority.routing_class,
            "requested_lane": requested_lane,
            "requested_lane_source": requested_source,
            "resolved_lane": None,
            "requested_lane_sources": requested_lane_sources,
            "routing_input_fingerprint": routing_input_fingerprint,
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
        "routing_class": authority.routing_class,
        "requested_lane": requested_lane,
        "requested_lane_source": requested_source,
        "resolved_lane": resolved_lane,
        "requested_lane_sources": requested_lane_sources,
        "routing_input_fingerprint": routing_input_fingerprint,
    }


def resolve_action_routing(
    action_token: str,
    *,
    policy_snapshot: Mapping[str, Any] | None = None,
    handoff_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    evaluation = evaluate_action_authority(
        action_token,
        policy_snapshot=policy_snapshot,
        handoff_payload=handoff_payload,
    )
    routing_class = _normalize_text(evaluation.get("routing_class"), default="") or None
    if routing_class not in KNOWN_ROUTING_CLASSES:
        routing_class = None
    resolved_lane = _normalize_text(evaluation.get("resolved_lane"), default="") or None
    if resolved_lane not in KNOWN_EXECUTION_LANES:
        resolved_lane = None
    return {
        "known_action": bool(evaluation.get("known_action", False)),
        "allowed": bool(evaluation.get("allowed", False)),
        "reason": _normalize_text(evaluation.get("reason"), default=""),
        "action_token": _normalize_text(evaluation.get("action_token"), default=""),
        "routing_class": routing_class,
        "resolved_lane": resolved_lane,
        "default_lane": _normalize_text(evaluation.get("default_lane"), default="") or None,
        "requested_lane": _normalize_text(evaluation.get("requested_lane"), default="") or None,
        "requested_lane_source": _normalize_text(evaluation.get("requested_lane_source"), default="") or None,
        "routing_input_fingerprint": _normalize_text(
            evaluation.get("routing_input_fingerprint"),
            default="",
        )
        or None,
        "authority_evaluation": evaluation,
    }
