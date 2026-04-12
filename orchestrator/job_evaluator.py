from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from orchestrator.classify import classify_changes
from orchestrator.evaluate import evaluate_rubric
from orchestrator.merge_gate import apply_merge_gate


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _normalize_changed_files(value: Any) -> tuple[str, ...] | None:
    if not isinstance(value, (list, tuple)):
        return None
    normalized: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            normalized.append(text)
    return tuple(normalized)


def _derive_declared_category(request_payload: dict[str, Any]) -> tuple[str, str]:
    raw = request_payload.get("declared_category")
    text = str(raw).strip() if raw is not None else ""
    if text:
        return text, "request.declared_category"
    return "feature", "fallback_feature"


def _derive_changed_files(
    request_payload: dict[str, Any], result_payload: dict[str, Any]
) -> tuple[tuple[str, ...], str]:
    request_changed = _normalize_changed_files(request_payload.get("changed_files"))
    if request_changed is not None:
        return request_changed, "request.changed_files"

    result_changed = _normalize_changed_files(result_payload.get("changed_files"))
    if result_changed is not None:
        return result_changed, "result.changed_files"

    execution = result_payload.get("execution")
    if isinstance(execution, dict):
        execution_changed = _normalize_changed_files(execution.get("changed_files"))
        if execution_changed is not None:
            return execution_changed, "result.execution.changed_files"

    return (), "fallback_empty_tuple"


def _derive_required_tests_declared(request_payload: dict[str, Any]) -> tuple[bool, str]:
    raw = request_payload.get("validation_commands", [])
    if isinstance(raw, list):
        return len(raw) > 0, "request.validation_commands"
    return False, "fallback_empty_validation_commands"


def _derive_verify_flags(result_payload: dict[str, Any]) -> tuple[bool, bool, str]:
    execution = result_payload.get("execution")
    if not isinstance(execution, dict):
        return False, False, "fallback_no_execution_verify"

    verify = execution.get("verify")
    if not isinstance(verify, dict):
        return False, False, "fallback_no_execution_verify"

    status = str(verify.get("status", "")).strip()
    if status == "passed":
        return True, True, "result.execution.verify.status"
    if status == "failed":
        return True, False, "result.execution.verify.status"
    if status == "not_run":
        return False, False, "result.execution.verify.status"
    return False, False, "fallback_unknown_verify_status"


def _derive_int_signal(
    *,
    request_payload: dict[str, Any],
    result_payload: dict[str, Any],
    key: str,
) -> tuple[int, str]:
    candidates: list[tuple[str, Any]] = [
        (f"result.{key}", result_payload.get(key)),
    ]
    execution = result_payload.get("execution")
    if isinstance(execution, dict):
        candidates.append((f"result.execution.{key}", execution.get(key)))
    candidates.append((f"request.{key}", request_payload.get(key)))

    for source, value in candidates:
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value, source
        if isinstance(value, str):
            stripped = value.strip()
            if stripped and stripped.lstrip("-").isdigit():
                return int(stripped), source

    return 0, f"fallback_{key}_zero"


def _derive_job_id(job_dir: Path, request_payload: dict[str, Any], result_payload: dict[str, Any]) -> tuple[str, str]:
    request_job_id = str(request_payload.get("job_id", "")).strip()
    if request_job_id:
        return request_job_id, "request.job_id"

    result_job_id = str(result_payload.get("job_id", "")).strip()
    if result_job_id:
        return result_job_id, "result.job_id"

    return job_dir.name, "fallback_job_dir_name"


def evaluate_job_directory(job_dir: str | Path) -> dict[str, Any]:
    job_dir_path = Path(job_dir)
    request_path = job_dir_path / "request.json"
    result_path = job_dir_path / "result.json"

    request_payload = _read_json(request_path)
    result_payload = _read_json(result_path)

    assumptions: dict[str, Any] = {"fallbacks_used": []}

    job_id, job_id_source = _derive_job_id(job_dir_path, request_payload, result_payload)
    assumptions["job_id_source"] = job_id_source
    if job_id_source.startswith("fallback_"):
        assumptions["fallbacks_used"].append(job_id_source)

    declared_category, declared_source = _derive_declared_category(request_payload)
    assumptions["declared_category_source"] = declared_source
    if declared_source.startswith("fallback_"):
        assumptions["fallbacks_used"].append(declared_source)

    changed_files, changed_files_source = _derive_changed_files(request_payload, result_payload)
    assumptions["changed_files_source"] = changed_files_source
    if changed_files_source.startswith("fallback_"):
        assumptions["fallbacks_used"].append(changed_files_source)

    required_tests_declared, required_tests_declared_source = _derive_required_tests_declared(
        request_payload
    )
    assumptions["required_tests_declared_source"] = required_tests_declared_source
    if required_tests_declared_source.startswith("fallback_"):
        assumptions["fallbacks_used"].append(required_tests_declared_source)

    required_tests_executed, required_tests_passed, verify_source = _derive_verify_flags(
        result_payload
    )
    assumptions["verify_source"] = verify_source
    if verify_source.startswith("fallback_"):
        assumptions["fallbacks_used"].append(verify_source)

    additions, additions_source = _derive_int_signal(
        request_payload=request_payload,
        result_payload=result_payload,
        key="additions",
    )
    deletions, deletions_source = _derive_int_signal(
        request_payload=request_payload,
        result_payload=result_payload,
        key="deletions",
    )
    assumptions["additions_source"] = additions_source
    assumptions["deletions_source"] = deletions_source
    if additions_source.startswith("fallback_"):
        assumptions["fallbacks_used"].append(additions_source)
    if deletions_source.startswith("fallback_"):
        assumptions["fallbacks_used"].append(deletions_source)

    ci_green = False
    assumptions["ci_green_source"] = "fallback_false_no_ci_signal"
    assumptions["fallbacks_used"].append("fallback_false_no_ci_signal")

    rollback_metadata_recorded = False
    assumptions["rollback_metadata_source"] = "fallback_false_no_rollback_signal"
    assumptions["fallbacks_used"].append("fallback_false_no_rollback_signal")

    classification = classify_changes(
        declared_category=declared_category,
        changed_files=changed_files,
    )
    rubric = evaluate_rubric(
        declared_category=declared_category,
        observed_category=classification.observed_category,
        changed_files=changed_files,
        additions=additions,
        deletions=deletions,
        required_tests_declared=required_tests_declared,
        required_tests_executed=required_tests_executed,
        required_tests_passed=required_tests_passed,
        ci_green=ci_green,
        rollback_metadata_recorded=rollback_metadata_recorded,
    )
    merge_gate = apply_merge_gate(rubric=rubric)

    return {
        "job_id": job_id,
        "classification": asdict(classification),
        "rubric": asdict(rubric),
        "merge_gate": asdict(merge_gate),
        "assumptions": assumptions,
    }


def format_human_summary(result: dict[str, Any]) -> str:
    classification = result["classification"]
    rubric = result["rubric"]
    merge_gate = result["merge_gate"]
    assumptions = result["assumptions"]

    fail_reasons = rubric.get("fail_reasons") or merge_gate.get("fail_reasons") or ()
    warnings = rubric.get("warnings") or ()
    fallbacks = assumptions.get("fallbacks_used") or ()

    lines = [
        f"Job ID: {result['job_id']}",
        f"Declared Category: {classification['declared_category']}",
        f"Observed Category: {classification['observed_category']}",
        f"Merge Eligible: {rubric['merge_eligible']}",
        f"Merge Gate Passed: {merge_gate['passed']}",
        "Fail Reasons: " + (", ".join(fail_reasons) if fail_reasons else "none"),
        "Warnings: " + (", ".join(warnings) if warnings else "none"),
    ]
    if fallbacks:
        lines.append("Conservative fallbacks used: " + ", ".join(fallbacks))
    else:
        lines.append("Conservative fallbacks used: none")

    return "\n".join(lines)


def persist_evaluation_artifacts(
    job_dir: str | Path,
    *,
    include_classification: bool = False,
    evaluation_result: dict[str, Any] | None = None,
) -> tuple[str, ...]:
    job_dir_path = Path(job_dir)
    result = evaluation_result if evaluation_result is not None else evaluate_job_directory(job_dir_path)

    written_files: list[str] = []

    rubric_path = job_dir_path / "rubric.json"
    _write_json(rubric_path, result["rubric"])
    written_files.append(rubric_path.name)

    merge_gate_path = job_dir_path / "merge_gate.json"
    _write_json(merge_gate_path, result["merge_gate"])
    written_files.append(merge_gate_path.name)

    if include_classification:
        classification = result["classification"]
        classification_payload = {
            "declared_category": classification.get("declared_category"),
            "observed_category": classification.get("observed_category"),
            "reasons": classification.get("reasons"),
            "changed_files": classification.get("changed_files"),
            "assumptions": result.get("assumptions", {}),
        }
        classification_path = job_dir_path / "classification.json"
        _write_json(classification_path, classification_payload)
        written_files.append(classification_path.name)

    return tuple(written_files)
