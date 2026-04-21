from __future__ import annotations

from collections import OrderedDict
from typing import Any
from typing import Mapping

from automation.orchestration.artifact_index import CONTRACT_ARTIFACT_ROLES

ARTIFACT_RETENTION_SCHEMA_VERSION = "v1"
RETENTION_MANIFEST_SCHEMA_VERSION = "v1"

ARTIFACT_RETENTION_STATUSES = {
    "ready",
    "partial",
    "degraded",
    "insufficient_truth",
}

ARTIFACT_RETENTION_VALIDITIES = {
    "valid",
    "partial",
    "malformed",
    "insufficient_truth",
}

ARTIFACT_RETENTION_CONFIDENCE_LEVELS = {
    "high",
    "medium",
    "low",
}

RETENTION_POLICY_CLASSES = {
    "retain_all_canonical",
    "retain_compact_plus_canonical",
    "retain_with_superseded_markers",
    "retain_with_prunable_markers",
    "unknown",
}

RETENTION_COMPACTION_CLASSES = {
    "fully_compact",
    "compact_with_aliases",
    "compact_with_superseded",
    "needs_tightening",
    "unknown",
}

RETENTION_CLASSES = {
    "canonical",
    "summary_ref",
    "path_ref",
    "compatibility_alias",
    "superseded",
    "prunable_metadata_only",
    "unknown",
}

ARTIFACT_RETENTION_REASON_CODES = {
    "malformed_reference_layout",
    "insufficient_retention_truth",
    "canonical_index_ready",
    "alias_deduplicated",
    "superseded_markers_present",
    "prunable_markers_present",
    "reference_inconsistent",
    "manifest_not_compact",
    "no_reason",
}

ARTIFACT_RETENTION_REASON_ORDER = (
    "malformed_reference_layout",
    "insufficient_retention_truth",
    "reference_inconsistent",
    "manifest_not_compact",
    "superseded_markers_present",
    "prunable_markers_present",
    "alias_deduplicated",
    "canonical_index_ready",
    "no_reason",
)

RETENTION_MANIFEST_REASON_CODES = {
    "malformed_reference_layout",
    "insufficient_retention_truth",
    "canonical_reference_layout_ready",
    "compatibility_alias_present",
    "superseded_markers_present",
    "prunable_markers_present",
    "manifest_not_compact",
    "no_reason",
}

RETENTION_MANIFEST_REASON_ORDER = (
    "malformed_reference_layout",
    "insufficient_retention_truth",
    "manifest_not_compact",
    "superseded_markers_present",
    "prunable_markers_present",
    "compatibility_alias_present",
    "canonical_reference_layout_ready",
    "no_reason",
)

ARTIFACT_RETENTION_RUN_STATE_SUMMARY_SAFE_FIELDS = (
    "artifact_retention_present",
)

ARTIFACT_RETENTION_SUMMARY_SAFE_FIELDS = (
    "artifact_retention_status",
    "artifact_retention_validity",
    "artifact_retention_confidence",
    "retention_policy_class",
    "retention_compaction_class",
    "canonical_artifact_count",
    "superseded_artifact_count",
    "prunable_artifact_count",
    "retention_primary_reason",
)

RETENTION_MANIFEST_SUMMARY_SAFE_FIELDS = (
    "reference_layout_version",
    "reference_order_stable",
    "alias_deduplicated",
    "manifest_compact",
    "canonical_artifact_count",
    "superseded_artifact_count",
    "prunable_artifact_count",
    "retention_manifest_primary_reason",
)

_ALLOWED_SUPPORTING_REFS = (
    "manifest.contract_artifact_index",
    "manifest.run_state_summary_compact",
    "observability_rollup_contract.observability_status",
    "failure_bucketing_hardening_contract.failure_bucketing_status",
    "endgame_closure_contract.final_closure_class",
)


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes"}:
            return True
        if lowered in {"0", "false", "no"}:
            return False
    return False


def _normalize_non_negative_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            return int(text)
    return 0


def _normalize_enum(value: Any, *, allowed: set[str], default: str) -> str:
    text = _normalize_text(value, default="")
    if text in allowed:
        return text
    return default


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = _normalize_text(value, default="")
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _coerce_mapping(value: Any) -> tuple[dict[str, Any], bool]:
    if isinstance(value, Mapping):
        return dict(value), False
    return {}, value is not None


def _normalize_reason_codes(values: list[str], *, allowed: set[str], order: tuple[str, ...]) -> list[str]:
    normalized = [value for value in _ordered_unique(values) if value in allowed]
    ordered: list[str] = []
    for code in order:
        if code in normalized:
            ordered.append(code)
    return ordered


def _normalize_supporting_refs(values: list[str]) -> list[str]:
    allowed = set(_ALLOWED_SUPPORTING_REFS)
    return [value for value in _ordered_unique(values) if value in allowed]


def _ordered_roles(paths: Mapping[str, Any], summaries: Mapping[str, Any]) -> list[str]:
    ordered = list(CONTRACT_ARTIFACT_ROLES)
    seen = set(ordered)
    extras = sorted(set(paths.keys()) | set(summaries.keys()))
    for role in extras:
        if role not in seen:
            ordered.append(role)
    return ordered


def _manifest_is_compact(manifest_payload: Mapping[str, Any]) -> bool:
    if not isinstance(manifest_payload, Mapping):
        return True
    for key, value in manifest_payload.items():
        key_text = _normalize_text(key, default="")
        if key_text.endswith("_payload"):
            return False
        if key_text.endswith("_summary") and value is not None and not isinstance(value, Mapping):
            return False
    return True


def build_retention_manifest_surface(
    *,
    run_id: str,
    objective_contract_payload: Mapping[str, Any] | None,
    paths_by_role: Mapping[str, Any] | None,
    summaries_by_role: Mapping[str, Any] | None,
    contract_artifact_index_payload: Mapping[str, Any] | None,
    manifest_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    objective, objective_malformed = _coerce_mapping(objective_contract_payload)
    paths, paths_malformed = _coerce_mapping(paths_by_role)
    summaries, summaries_malformed = _coerce_mapping(summaries_by_role)
    artifact_index, artifact_index_malformed = _coerce_mapping(contract_artifact_index_payload)
    manifest, manifest_malformed = _coerce_mapping(manifest_payload)

    malformed_layout = any(
        (
            objective_malformed,
            paths_malformed,
            summaries_malformed,
            artifact_index_malformed,
            manifest_malformed,
        )
    )

    role_order = _ordered_roles(paths, summaries)

    canonical_artifacts: list[dict[str, Any]] = []
    summary_safe_refs: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
    path_refs: "OrderedDict[str, str]" = OrderedDict()

    for role in role_order:
        path_value = _normalize_text(paths.get(role), default="")
        summary_value = summaries.get(role)

        if path_value:
            canonical_artifacts.append(
                {
                    "role": role,
                    "path": path_value,
                    "retention_class": "canonical",
                }
            )
            path_refs[role] = path_value

        if isinstance(summary_value, Mapping):
            summary_safe_refs[role] = {
                "retention_class": "summary_ref",
                "summary_keys": sorted([str(key) for key in summary_value.keys()]),
            }

    compatibility_alias_refs: list[dict[str, Any]] = []
    if (
        _normalize_text(manifest.get("run_state_summary"), default="") == ""
        and isinstance(manifest.get("run_state_summary"), Mapping)
        and isinstance(manifest.get("run_state_summary_compact"), Mapping)
        and dict(manifest.get("run_state_summary")) == dict(manifest.get("run_state_summary_compact"))
    ):
        compatibility_alias_refs.append(
            {
                "alias": "manifest.run_state_summary",
                "canonical": "manifest.run_state_summary_compact",
                "retention_class": "compatibility_alias",
            }
        )
    elif (
        isinstance(manifest.get("run_state_summary"), Mapping)
        and isinstance(manifest.get("run_state_summary_compact"), Mapping)
        and dict(manifest.get("run_state_summary")) == dict(manifest.get("run_state_summary_compact"))
    ):
        compatibility_alias_refs.append(
            {
                "alias": "manifest.run_state_summary",
                "canonical": "manifest.run_state_summary_compact",
                "retention_class": "compatibility_alias",
            }
        )

    superseded_artifacts: list[dict[str, Any]] = []
    if "failure_bucket_rollup" in path_refs and "failure_bucketing_hardening_contract" in path_refs:
        superseded_artifacts.append(
            {
                "role": "failure_bucket_rollup",
                "superseded_by": "failure_bucketing_hardening_contract",
                "retention_class": "superseded",
            }
        )

    prunable_artifacts: list[dict[str, Any]] = []
    if compatibility_alias_refs:
        prunable_artifacts.append(
            {
                "ref": "manifest.run_state_summary",
                "reason": "compact_alias_superseded",
                "retention_class": "prunable_metadata_only",
            }
        )

    manifest_compact = _manifest_is_compact(manifest)
    reference_order_stable = True
    alias_deduplicated = bool(compatibility_alias_refs)

    canonical_roles = _ordered_unique([str(item.get("role", "")) for item in canonical_artifacts])
    canonical_artifact_count = len(canonical_roles)
    superseded_artifact_count = len(superseded_artifacts)
    prunable_artifact_count = len(prunable_artifacts)

    reason_codes = _normalize_reason_codes(
        [
            "malformed_reference_layout" if malformed_layout else "",
            "insufficient_retention_truth" if canonical_artifact_count == 0 else "",
            "manifest_not_compact" if not manifest_compact else "",
            "superseded_markers_present" if superseded_artifact_count > 0 else "",
            "prunable_markers_present" if prunable_artifact_count > 0 else "",
            "compatibility_alias_present" if compatibility_alias_refs else "",
            "canonical_reference_layout_ready" if canonical_artifact_count > 0 else "",
        ],
        allowed=RETENTION_MANIFEST_REASON_CODES,
        order=RETENTION_MANIFEST_REASON_ORDER,
    )
    if not reason_codes:
        reason_codes = ["no_reason"]

    objective_id = _normalize_text(
        objective.get("objective_id") or manifest.get("objective_id"),
        default="",
    )

    return {
        "schema_version": RETENTION_MANIFEST_SCHEMA_VERSION,
        "run_id": _normalize_text(run_id, default=""),
        "objective_id": objective_id,
        "canonical_artifacts": canonical_artifacts,
        "summary_safe_refs": dict(summary_safe_refs),
        "path_refs": dict(path_refs),
        "superseded_artifacts": superseded_artifacts,
        "prunable_artifacts": prunable_artifacts,
        "compatibility_alias_refs": compatibility_alias_refs,
        "reference_layout_version": "v1",
        "reference_order_stable": bool(reference_order_stable),
        "alias_deduplicated": bool(alias_deduplicated),
        "manifest_compact": bool(manifest_compact),
        "retention_manifest_primary_reason": reason_codes[0],
        "retention_manifest_reason_codes": reason_codes,
        "canonical_artifact_count": canonical_artifact_count,
        "superseded_artifact_count": superseded_artifact_count,
        "prunable_artifact_count": prunable_artifact_count,
    }


def build_artifact_retention_contract_surface(
    *,
    run_id: str,
    objective_contract_payload: Mapping[str, Any] | None,
    retention_manifest_payload: Mapping[str, Any] | None,
    contract_artifact_index_payload: Mapping[str, Any] | None,
    observability_rollup_payload: Mapping[str, Any] | None,
    failure_bucketing_hardening_payload: Mapping[str, Any] | None,
    endgame_closure_contract_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    objective, objective_malformed = _coerce_mapping(objective_contract_payload)
    retention_manifest, retention_malformed = _coerce_mapping(retention_manifest_payload)
    artifact_index, artifact_index_malformed = _coerce_mapping(contract_artifact_index_payload)
    observability, observability_malformed = _coerce_mapping(observability_rollup_payload)
    hardening, hardening_malformed = _coerce_mapping(failure_bucketing_hardening_payload)
    endgame, endgame_malformed = _coerce_mapping(endgame_closure_contract_payload)

    malformed_inputs = any(
        (
            objective_malformed,
            retention_malformed,
            artifact_index_malformed,
            observability_malformed,
            hardening_malformed,
            endgame_malformed,
        )
    )

    canonical_artifacts = retention_manifest.get("canonical_artifacts")
    summary_safe_refs = retention_manifest.get("summary_safe_refs")
    path_refs = retention_manifest.get("path_refs")
    compatibility_alias_refs = retention_manifest.get("compatibility_alias_refs")
    superseded_artifacts = retention_manifest.get("superseded_artifacts")
    prunable_artifacts = retention_manifest.get("prunable_artifacts")

    canonical_list = canonical_artifacts if isinstance(canonical_artifacts, list) else []
    summary_map = summary_safe_refs if isinstance(summary_safe_refs, Mapping) else {}
    path_map = path_refs if isinstance(path_refs, Mapping) else {}
    alias_list = compatibility_alias_refs if isinstance(compatibility_alias_refs, list) else []
    superseded_list = superseded_artifacts if isinstance(superseded_artifacts, list) else []
    prunable_list = prunable_artifacts if isinstance(prunable_artifacts, list) else []

    canonical_roles = _ordered_unique([_normalize_text(item.get("role"), default="") for item in canonical_list if isinstance(item, Mapping)])
    canonical_artifact_count = len(canonical_roles)
    summary_ref_count = len(summary_map)
    path_ref_count = len(path_map)
    alias_ref_count = len(alias_list)
    superseded_artifact_count = len(superseded_list)
    prunable_artifact_count = len(prunable_list)

    artifact_count = len(
        set(
            canonical_roles
            + list(summary_map.keys())
            + list(path_map.keys())
        )
    )

    reference_consistent = True
    for role in canonical_roles:
        canonical_path = ""
        for item in canonical_list:
            if isinstance(item, Mapping) and _normalize_text(item.get("role"), default="") == role:
                canonical_path = _normalize_text(item.get("path"), default="")
                break
        if _normalize_text(path_map.get(role), default="") != canonical_path:
            reference_consistent = False
            break
        index_entry = artifact_index.get(role)
        if isinstance(index_entry, Mapping):
            if _normalize_text(index_entry.get("path"), default="") not in {"", canonical_path}:
                reference_consistent = False
                break

    manifest_compact = _normalize_bool(retention_manifest.get("manifest_compact"))
    alias_deduplicated = _normalize_bool(retention_manifest.get("alias_deduplicated")) or alias_ref_count > 0
    pruning_metadata_present = prunable_artifact_count > 0

    retention_validity = "valid"
    retention_status = "ready"
    retention_confidence = "high"

    if malformed_inputs:
        retention_validity = "malformed"
        retention_status = "degraded"
        retention_confidence = "low"
    elif canonical_artifact_count == 0 or path_ref_count == 0:
        retention_validity = "insufficient_truth"
        retention_status = "insufficient_truth"
        retention_confidence = "low"
    elif (not reference_consistent) or (not manifest_compact):
        retention_validity = "partial"
        retention_status = "partial"
        retention_confidence = "medium"
    elif alias_ref_count > 0 or superseded_artifact_count > 0 or prunable_artifact_count > 0:
        retention_validity = "valid"
        retention_status = "ready"
        retention_confidence = "medium"

    if retention_status == "insufficient_truth":
        retention_policy_class = "unknown"
    elif prunable_artifact_count > 0:
        retention_policy_class = "retain_with_prunable_markers"
    elif superseded_artifact_count > 0:
        retention_policy_class = "retain_with_superseded_markers"
    elif alias_ref_count > 0:
        retention_policy_class = "retain_compact_plus_canonical"
    else:
        retention_policy_class = "retain_all_canonical"

    if not manifest_compact:
        retention_compaction_class = "needs_tightening"
    elif superseded_artifact_count > 0:
        retention_compaction_class = "compact_with_superseded"
    elif alias_ref_count > 0:
        retention_compaction_class = "compact_with_aliases"
    elif canonical_artifact_count > 0:
        retention_compaction_class = "fully_compact"
    else:
        retention_compaction_class = "unknown"

    reason_codes = _normalize_reason_codes(
        [
            "malformed_reference_layout" if malformed_inputs else "",
            "insufficient_retention_truth" if retention_status == "insufficient_truth" else "",
            "reference_inconsistent" if not reference_consistent else "",
            "manifest_not_compact" if not manifest_compact else "",
            "superseded_markers_present" if superseded_artifact_count > 0 else "",
            "prunable_markers_present" if pruning_metadata_present else "",
            "alias_deduplicated" if alias_deduplicated else "",
            "canonical_index_ready" if canonical_artifact_count > 0 else "",
        ],
        allowed=ARTIFACT_RETENTION_REASON_CODES,
        order=ARTIFACT_RETENTION_REASON_ORDER,
    )
    if not reason_codes:
        reason_codes = ["no_reason"]

    supporting_refs = _normalize_supporting_refs(
        [
            "manifest.contract_artifact_index" if artifact_index else "",
            "manifest.run_state_summary_compact"
            if isinstance(summary_map.get("run_state_summary_compact"), Mapping)
            else "",
            "observability_rollup_contract.observability_status"
            if _normalize_text(observability.get("observability_status"), default="")
            else "",
            "failure_bucketing_hardening_contract.failure_bucketing_status"
            if _normalize_text(hardening.get("failure_bucketing_status"), default="")
            else "",
            "endgame_closure_contract.final_closure_class"
            if _normalize_text(endgame.get("final_closure_class"), default="")
            else "",
        ]
    )

    objective_id = _normalize_text(
        objective.get("objective_id") or retention_manifest.get("objective_id"),
        default="",
    )

    return {
        "schema_version": ARTIFACT_RETENTION_SCHEMA_VERSION,
        "run_id": _normalize_text(run_id, default=""),
        "objective_id": objective_id,
        "artifact_retention_status": _normalize_enum(
            retention_status,
            allowed=ARTIFACT_RETENTION_STATUSES,
            default="insufficient_truth",
        ),
        "artifact_retention_validity": _normalize_enum(
            retention_validity,
            allowed=ARTIFACT_RETENTION_VALIDITIES,
            default="insufficient_truth",
        ),
        "artifact_retention_confidence": _normalize_enum(
            retention_confidence,
            allowed=ARTIFACT_RETENTION_CONFIDENCE_LEVELS,
            default="low",
        ),
        "artifact_count": _normalize_non_negative_int(artifact_count),
        "canonical_artifact_count": _normalize_non_negative_int(canonical_artifact_count),
        "summary_ref_count": _normalize_non_negative_int(summary_ref_count),
        "path_ref_count": _normalize_non_negative_int(path_ref_count),
        "alias_ref_count": _normalize_non_negative_int(alias_ref_count),
        "superseded_artifact_count": _normalize_non_negative_int(superseded_artifact_count),
        "prunable_artifact_count": _normalize_non_negative_int(prunable_artifact_count),
        "retention_primary_reason": reason_codes[0],
        "retention_reason_codes": reason_codes,
        "retention_policy_class": _normalize_enum(
            retention_policy_class,
            allowed=RETENTION_POLICY_CLASSES,
            default="unknown",
        ),
        "retention_compaction_class": _normalize_enum(
            retention_compaction_class,
            allowed=RETENTION_COMPACTION_CLASSES,
            default="unknown",
        ),
        "retention_alias_deduplicated": bool(alias_deduplicated),
        "retention_reference_consistent": bool(reference_consistent),
        "retention_manifest_compact": bool(manifest_compact),
        "retention_pruning_metadata_present": bool(pruning_metadata_present),
        "artifact_index_present": bool(artifact_index),
        "observability_status": _normalize_text(
            observability.get("observability_status"),
            default="insufficient_truth",
        ),
        "failure_bucketing_status": _normalize_text(
            hardening.get("failure_bucketing_status"),
            default="insufficient_truth",
        ),
        "final_closure_class": _normalize_text(
            endgame.get("final_closure_class"),
            default="unknown",
        ),
        "supporting_compact_truth_refs": supporting_refs,
    }


def build_artifact_retention_run_state_summary_surface(
    artifact_retention_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(artifact_retention_payload or {})
    return {
        "artifact_retention_present": bool(
            _normalize_text(payload.get("artifact_retention_status"), default="")
        )
        or _normalize_bool(payload.get("artifact_retention_present"))
    }


def build_artifact_retention_summary_surface(
    artifact_retention_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(artifact_retention_payload or {})
    return {
        "artifact_retention_status": _normalize_enum(
            payload.get("artifact_retention_status"),
            allowed=ARTIFACT_RETENTION_STATUSES,
            default="insufficient_truth",
        ),
        "artifact_retention_validity": _normalize_enum(
            payload.get("artifact_retention_validity"),
            allowed=ARTIFACT_RETENTION_VALIDITIES,
            default="insufficient_truth",
        ),
        "artifact_retention_confidence": _normalize_enum(
            payload.get("artifact_retention_confidence"),
            allowed=ARTIFACT_RETENTION_CONFIDENCE_LEVELS,
            default="low",
        ),
        "retention_policy_class": _normalize_enum(
            payload.get("retention_policy_class"),
            allowed=RETENTION_POLICY_CLASSES,
            default="unknown",
        ),
        "retention_compaction_class": _normalize_enum(
            payload.get("retention_compaction_class"),
            allowed=RETENTION_COMPACTION_CLASSES,
            default="unknown",
        ),
        "canonical_artifact_count": _normalize_non_negative_int(
            payload.get("canonical_artifact_count")
        ),
        "superseded_artifact_count": _normalize_non_negative_int(
            payload.get("superseded_artifact_count")
        ),
        "prunable_artifact_count": _normalize_non_negative_int(
            payload.get("prunable_artifact_count")
        ),
        "retention_primary_reason": _normalize_text(
            payload.get("retention_primary_reason"),
            default="no_reason",
        )
        if _normalize_text(payload.get("retention_primary_reason"), default="")
        in ARTIFACT_RETENTION_REASON_CODES
        else "no_reason",
    }


def build_retention_manifest_summary_surface(
    retention_manifest_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(retention_manifest_payload or {})
    return {
        "reference_layout_version": _normalize_text(
            payload.get("reference_layout_version"),
            default="v1",
        ),
        "reference_order_stable": _normalize_bool(payload.get("reference_order_stable")),
        "alias_deduplicated": _normalize_bool(payload.get("alias_deduplicated")),
        "manifest_compact": _normalize_bool(payload.get("manifest_compact")),
        "canonical_artifact_count": _normalize_non_negative_int(
            payload.get("canonical_artifact_count")
        ),
        "superseded_artifact_count": _normalize_non_negative_int(
            payload.get("superseded_artifact_count")
        ),
        "prunable_artifact_count": _normalize_non_negative_int(
            payload.get("prunable_artifact_count")
        ),
        "retention_manifest_primary_reason": _normalize_text(
            payload.get("retention_manifest_primary_reason"),
            default="no_reason",
        )
        if _normalize_text(payload.get("retention_manifest_primary_reason"), default="")
        in RETENTION_MANIFEST_REASON_CODES
        else "no_reason",
    }
