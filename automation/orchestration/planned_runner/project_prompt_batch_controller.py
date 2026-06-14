"""Project prompt-batch execution controller (Prompt655).

Safe, deterministic, OFFLINE control layer over a prompt batch. It NEVER executes
prompt text, never runs tests/daemon/Codex, never mutates git. It:
- validates a batch manifest,
- lists prompts in deterministic order,
- determines the next runnable prompt,
- verifies post-prompt EVIDENCE (expected tag / report / summary / status field) that an
  operator or Claude Code produced AFTER running a prompt,
- scores each prompt out of 100 with a breakdown,
- decides continue/stop (advance only on PASS),
- emits a clear next-Claude-Code instruction.

External effects (tag existence, source cleanliness) are read via INJECTABLE providers
(default: read-only git) so tests use fakes — no real git mutation, ever.
Writes only under artifacts/autonomous_runtime/prompt_batches/<batch_id>/ when asked.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Callable, Mapping

from automation.orchestration.planned_runner.project_prompt_batch import (
    load_and_validate,
)

_PASS_THRESHOLD = 100  # full evidence required to advance


# --------------------------------------------------------------------------- providers
def _default_tag_checker(repo_root: str, tag: str) -> bool:
    if not tag:
        return True
    try:
        out = subprocess.run(
            ["git", "-C", repo_root, "tag", "-l", tag],
            check=True, capture_output=True, text=True,
        )
    except Exception:
        return False
    return tag in out.stdout.split()


def _default_source_status(repo_root: str) -> dict[str, Any]:
    try:
        out = subprocess.run(
            ["git", "-C", repo_root, "status", "--porcelain"],
            check=True, capture_output=True, text=True,
        )
    except Exception as exc:
        return {"clean": False, "detail": f"git status failed: {exc!r}"}
    dirty = [ln for ln in out.stdout.splitlines() if ln.strip()]
    return {"clean": len(dirty) == 0, "dirty_count": len(dirty)}


# --------------------------------------------------------------------------- artifacts
def _batch_artifacts_root(repo_root: str, batch_id: str) -> Path:
    return Path(repo_root) / "artifacts" / "autonomous_runtime" / "prompt_batches" / batch_id


def _evaluation_path(repo_root: str, batch_id: str, prompt_id: str) -> Path:
    return _batch_artifacts_root(repo_root, batch_id) / "evaluations" / f"{prompt_id}_evaluation.json"


def _receipt_path(repo_root: str, batch_id: str, prompt_id: str) -> Path:
    return _batch_artifacts_root(repo_root, batch_id) / "receipts" / f"{prompt_id}_receipt.json"


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> tuple[dict[str, Any], str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, str(exc)
    if not isinstance(payload, Mapping):
        return {}, "not a JSON object"
    return dict(payload), ""


def _existing_evaluation(repo_root: str, batch_id: str, prompt_id: str) -> dict[str, Any]:
    path = _evaluation_path(repo_root, batch_id, prompt_id)
    if not path.is_file():
        return {}
    payload, _ = _read_json(path)
    return payload


# --------------------------------------------------------------------------- core API
def analyze_prompt_batch(batch_dir: str | Path, *, repo_root: str = ".") -> dict[str, Any]:
    """Validate the batch and summarize each prompt's completion state. Read-only."""
    batch, errors = load_and_validate(batch_dir)
    if errors:
        return {
            "status": "blocked", "reason": "invalid_manifest", "errors": errors,
            "batch_id": batch.get("batch_id", ""), "prompts": [], "completed_count": 0,
            "total_prompts": 0, "next_prompt_id": "", "batch_complete": False,
        }
    batch_id = batch["batch_id"]
    prompt_states: list[dict[str, Any]] = []
    completed = 0
    next_id = ""
    for entry in batch["prompts"]:
        ev = _existing_evaluation(repo_root, batch_id, entry["prompt_id"])
        passed = bool(ev.get("passed"))
        evaluated = bool(ev)
        if passed:
            completed += 1
        if not passed and not next_id:
            next_id = entry["prompt_id"]
        prompt_states.append({
            "prompt_id": entry["prompt_id"],
            "order": entry["order"],
            "prompt_path": entry["prompt_path"],
            "evaluated": evaluated,
            "passed": passed,
            "evaluation_status": ev.get("status", "not_evaluated"),
        })
    return {
        "status": "ok",
        "errors": [],
        "batch_id": batch_id,
        "goal": batch["goal"],
        "total_prompts": len(batch["prompts"]),
        "completed_count": completed,
        "next_prompt_id": next_id,
        "batch_complete": completed == len(batch["prompts"]) and len(batch["prompts"]) > 0,
        "prompts": prompt_states,
        "stop_on_failure": batch["stop_on_failure"],
    }


def determine_next_prompt(batch_dir: str | Path, *, repo_root: str = ".") -> dict[str, Any]:
    """Return the first prompt that has not yet passed (deterministic order)."""
    batch, errors = load_and_validate(batch_dir)
    if errors:
        return {"status": "blocked", "reason": "invalid_manifest", "errors": errors, "next_prompt": None}
    batch_id = batch["batch_id"]
    for entry in batch["prompts"]:
        ev = _existing_evaluation(repo_root, batch_id, entry["prompt_id"])
        if bool(ev.get("passed")):
            continue
        # first not-passed prompt
        status = "failed_blocking" if (ev and not ev.get("passed")) else "runnable"
        return {
            "status": "ok",
            "reason": "next_found",
            "errors": [],
            "next_prompt": entry,
            "next_prompt_evaluated": bool(ev),
            "next_prompt_state": status,
        }
    return {"status": "ok", "reason": "batch_complete", "errors": [], "next_prompt": None}


def record_prompt_receipt(
    batch_dir: str | Path, prompt_id: str, receipt: Mapping[str, Any], *, repo_root: str = "."
) -> dict[str, Any]:
    """Persist an operator/Claude-Code execution receipt for a prompt. No execution."""
    batch, errors = load_and_validate(batch_dir)
    if errors:
        return {"status": "blocked", "reason": "invalid_manifest", "errors": errors, "receipt_path": ""}
    if prompt_id not in {p["prompt_id"] for p in batch["prompts"]}:
        return {"status": "blocked", "reason": "unknown_prompt_id", "errors": [f"unknown prompt_id: {prompt_id}"], "receipt_path": ""}
    safe_receipt = dict(receipt) if isinstance(receipt, Mapping) else {"raw": str(receipt)}
    safe_receipt["prompt_id"] = prompt_id
    path = _receipt_path(repo_root, batch["batch_id"], prompt_id)
    _write_json(path, safe_receipt)
    return {"status": "ok", "errors": [], "receipt_path": path.as_posix(), "receipt": safe_receipt}


def evaluate_prompt_result(
    batch_dir: str | Path,
    prompt_id: str,
    *,
    repo_root: str = ".",
    tag_checker: Callable[[str, str], bool] | None = None,
    write: bool = True,
) -> dict[str, Any]:
    """Verify post-prompt evidence and score the prompt out of 100. Never executes."""
    batch, errors = load_and_validate(batch_dir)
    if errors:
        return {"status": "blocked", "reason": "invalid_manifest", "errors": errors, "passed": False, "score": 0}
    entry = next((p for p in batch["prompts"] if p["prompt_id"] == prompt_id), None)
    if entry is None:
        return {"status": "blocked", "reason": "unknown_prompt_id", "errors": [f"unknown prompt_id: {prompt_id}"], "passed": False, "score": 0}
    tag_checker = tag_checker or _default_tag_checker

    missing: list[str] = []

    # Report evidence + status field.
    report_present = False
    report_parseable = False
    status_match = False
    status_field = entry["pass_conditions"]["status_field"]
    status_value = entry["pass_conditions"]["status_value"]
    report_rel = entry["expected_report_path"]
    if report_rel:
        report_path = Path(repo_root) / report_rel
        report_present = report_path.is_file()
        if not report_present:
            missing.append(f"report missing: {report_rel}")
        else:
            report_obj, read_err = _read_json(report_path)
            report_parseable = not read_err
            if not report_parseable:
                missing.append(f"report not parseable: {report_rel} ({read_err})")
            elif status_field:
                actual = report_obj.get(status_field)
                status_match = (str(actual).strip() == status_value) if status_value else bool(actual)
                if not status_match:
                    missing.append(f"status field {status_field}={actual!r} != expected {status_value!r}")
    else:
        missing.append("no expected_report_path declared")

    # Summary evidence.
    summary_present = False
    summary_rel = entry["expected_summary_path"]
    if summary_rel:
        summary_path = Path(repo_root) / summary_rel
        summary_present = summary_path.is_file() and summary_path.stat().st_size > 0
        if not summary_present:
            missing.append(f"summary missing/empty: {summary_rel}")
    else:
        missing.append("no expected_summary_path declared")

    # Tag evidence (and commit-tag requirement).
    expected_tag = entry["expected_tag"]
    tag_present = bool(tag_checker(repo_root, expected_tag)) if expected_tag else True
    if expected_tag and not tag_present:
        missing.append(f"expected tag missing: {expected_tag}")
    if batch["require_commit_tag_per_prompt"] and not expected_tag:
        missing.append("require_commit_tag_per_prompt is set but no expected_tag declared")
        tag_present = False

    # Score breakdown (out of 100).
    objective_achievement = 40 if status_match else 0
    constraint_compliance = (15 if tag_present else 0) + (15 if (report_present and summary_present) else 0)
    test_evidence_quality = (10 if report_parseable else 0) + (10 if summary_present else 0)
    risk_remaining_gaps = 10 if not missing else 0
    score = objective_achievement + constraint_compliance + test_evidence_quality + risk_remaining_gaps

    passed = bool(status_match and report_present and summary_present and tag_present)
    continue_decision = "continue" if passed else "stop"
    eval_status = "pass" if passed else "fail"

    evaluation = {
        "prompt_id": prompt_id,
        "status": eval_status,
        "passed": passed,
        "score": score,
        "score_breakdown": {
            "objective_achievement": objective_achievement,
            "constraint_compliance": constraint_compliance,
            "test_evidence_quality": test_evidence_quality,
            "risk_remaining_gaps": risk_remaining_gaps,
        },
        "continue_decision": continue_decision,
        "evidence": {
            "report_present": report_present,
            "report_parseable": report_parseable,
            "status_field": status_field,
            "status_value_expected": status_value,
            "status_match": status_match,
            "summary_present": summary_present,
            "expected_tag": expected_tag,
            "tag_present": tag_present,
        },
        "required_tests_declared": entry["required_tests"],
        "required_tests_executed": False,
        "missing_evidence": missing,
        "errors": [],
    }
    if write:
        _write_json(_evaluation_path(repo_root, batch["batch_id"], prompt_id), evaluation)
    return evaluation


def _next_claude_code_instruction(batch_dir: str | Path, entry: Mapping[str, Any]) -> str:
    prompt_full = (Path(batch_dir) / entry["prompt_path"]).as_posix()
    lines = [
        f"NEXT PROMPT: {entry['prompt_id']}",
        f"Read and execute the implementation prompt file: {prompt_full}",
        "After Claude Code/Codex finishes, expected evidence:",
        f"  - expected tag: {entry['expected_tag'] or '(none declared)'}",
        f"  - expected report: {entry['expected_report_path'] or '(none declared)'}",
        f"  - expected summary: {entry['expected_summary_path'] or '(none declared)'}",
    ]
    pc = entry["pass_conditions"]
    if pc.get("status_field"):
        lines.append(f"  - report field {pc['status_field']} must equal {pc['status_value']!r}")
    lines.append("Then run: evaluate this prompt_id; advance only if it PASSES.")
    return "\n".join(lines)


def advance_prompt_batch(
    batch_dir: str | Path,
    *,
    repo_root: str = ".",
    source_status_provider: Callable[[str], Mapping[str, Any]] | None = None,
    write: bool = True,
) -> dict[str, Any]:
    """Decide whether the batch can proceed to the next prompt; emit an instruction.

    NEVER executes the prompt; it only checks prerequisites and produces the next
    Claude Code instruction. Stops on: invalid manifest, prior failure (when
    stop_on_failure), dirty source (when required), or batch complete."""
    source_status_provider = source_status_provider or _default_source_status
    batch, errors = load_and_validate(batch_dir)
    if errors:
        result = {"status": "blocked", "reason": "invalid_manifest", "errors": errors,
                  "next_prompt_id": "", "next_instruction": "", "batch_complete": False}
        if write and batch.get("batch_id"):
            _write_json(_batch_artifacts_root(repo_root, batch["batch_id"]) / "batch_report.json", result)
        return result
    batch_id = batch["batch_id"]

    # Walk prompts in order; stop at the first not-passed.
    next_entry = None
    for entry in batch["prompts"]:
        ev = _existing_evaluation(repo_root, batch_id, entry["prompt_id"])
        if bool(ev.get("passed")):
            continue
        if ev and not ev.get("passed") and batch["stop_on_failure"]:
            result = {
                "status": "blocked", "reason": "previous_prompt_failed",
                "errors": [f"prompt {entry['prompt_id']} evaluation failed (score {ev.get('score')})"],
                "blocked_on_prompt_id": entry["prompt_id"], "next_prompt_id": "",
                "next_instruction": "", "batch_complete": False, "batch_id": batch_id,
            }
            if write:
                _write_json(_batch_artifacts_root(repo_root, batch_id) / "batch_report.json", result)
            return result
        next_entry = entry
        break

    if next_entry is None:
        result = {"status": "complete", "reason": "batch_complete", "errors": [],
                  "next_prompt_id": "", "next_instruction": "", "batch_complete": True, "batch_id": batch_id}
        if write:
            _write_json(_batch_artifacts_root(repo_root, batch_id) / "batch_report.json", result)
        return result

    # Prerequisite: clean source if required.
    if batch["require_clean_source_before_each_prompt"]:
        src = source_status_provider(repo_root)
        if not (isinstance(src, Mapping) and src.get("clean")):
            result = {
                "status": "blocked", "reason": "dirty_source",
                "errors": ["source tree is not clean; commit/clean before running the next prompt"],
                "source_status": dict(src) if isinstance(src, Mapping) else {"clean": False},
                "next_prompt_id": next_entry["prompt_id"], "next_instruction": "",
                "batch_complete": False, "batch_id": batch_id,
            }
            if write:
                _write_json(_batch_artifacts_root(repo_root, batch_id) / "batch_report.json", result)
            return result

    instruction = _next_claude_code_instruction(batch_dir, next_entry)
    result = {
        "status": "ready", "reason": "next_prompt_ready", "errors": [],
        "next_prompt_id": next_entry["prompt_id"],
        "next_prompt_path": (Path(batch_dir) / next_entry["prompt_path"]).as_posix(),
        "next_instruction": instruction,
        "batch_complete": False, "batch_id": batch_id,
        "arbitrary_prompt_execution": False,
    }
    if write:
        _write_json(_batch_artifacts_root(repo_root, batch_id) / "batch_report.json", result)
    return result


__all__ = [
    "analyze_prompt_batch",
    "determine_next_prompt",
    "record_prompt_receipt",
    "evaluate_prompt_result",
    "advance_prompt_batch",
]
