"""Deterministic repair-headroom policy and task-shape diagnostics."""
from __future__ import annotations

from typing import Any, Sequence


def repair_headroom_evidence(*, task_id: str, task_index: int, allowed_changed_paths: Sequence[str], max_changed_files: int, min_repair_headroom: int) -> dict[str, Any]:
    count = len(allowed_changed_paths)
    headroom = max_changed_files - count
    prefixes = set()
    categories = set()
    for path in allowed_changed_paths:
        parts = path.split("/")
        prefixes.add("/".join(parts[:2]) if len(parts) > 1 else parts[0])
        lower = path.casefold()
        if "alembic/" in lower or "migration" in lower: categories.add("migration")
        if lower.startswith("packages/common/"): categories.add("common_model")
        if "/companies/" in lower or "/ingest" in lower: categories.add("ingestion_company")
        if "resolver" in lower: categories.add("resolver_domain")
        if "/gold_export/" in lower: categories.add("gold_export")
        elif "/export/" in lower: categories.add("export")
        if "/tests/" in lower or lower.startswith("tests/"): categories.add("tests")
        if lower.startswith("docs/") or lower.startswith("config/"): categories.add("docs_config")
    production_count = sum(not ("/tests/" in p.casefold() or p.casefold().startswith("tests/")) for p in allowed_changed_paths)
    test_count = count - production_count
    return {
        "task_id": task_id, "task_index": task_index,
        "allowed_changed_path_count": count, "profile_max_changed_files": max_changed_files,
        "min_repair_headroom": min_repair_headroom, "repair_headroom": headroom,
        "scope_utilization_percent": (count * 100) // max_changed_files if max_changed_files else 0,
        "distinct_subsystem_count": len(prefixes), "production_path_count": production_count,
        "test_path_count": test_count, "migration_present": "migration" in categories,
        "categories": sorted(categories), "cross_layer": len(categories - {"tests", "docs_config"}) > 1,
    }


__all__ = ["repair_headroom_evidence"]
