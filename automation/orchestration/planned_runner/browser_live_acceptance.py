"""Operator-controlled browser live acceptance harness (Prompt659).

The harness prepares and validates local artifacts only. It does not launch a
browser, read browser profiles, call ChatGPT APIs, call the network, run Codex,
or execute prompt text. Live success requires a response envelope produced by the
Prompt658 browser extension/content-script flow and supplied back to this module.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from automation.orchestration.planned_runner.browser_chatgpt_operator_adapter import (
    BROWSER_OPERATOR_ADAPTER_NAME,
    BROWSER_RESPONSE_ENVELOPE_SCHEMA,
    create_browser_request_envelope,
    inspect_extension_files,
    normalize_browser_response_file_to_analysis_artifact,
    validate_browser_response_envelope,
)
from automation.orchestration.planned_runner.external_analysis_handoff import (
    analysis_artifact_to_prompt_batch,
    validate_analysis_artifact,
)
from automation.orchestration.planned_runner.project_prompt_batch import load_and_validate
from automation.orchestration.planned_runner.project_prompt_batch_controller import (
    analyze_prompt_batch,
    determine_next_prompt,
)

DEFAULT_REQUEST_ID = "prompt659_live_acceptance"
DEFAULT_WORK_ROOT = "/tmp/codex-local-runner-prompt659-browser-live"
EXTENSION_REL_PATH = "browser_extension/chatgpt_runner_bridge"


def _txt(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _read_json(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.is_file():
        return {}, [f"file not found: {path.as_posix()}"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, [f"file unreadable/invalid JSON: {exc}"]
    if not isinstance(payload, Mapping):
        return {}, ["JSON payload must be an object"]
    return dict(payload), []


def build_live_acceptance_analysis_request(
    *,
    request_id: str = DEFAULT_REQUEST_ID,
) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "project_goal": "Verify operator-controlled ChatGPT browser analysis handoff from Prompt658 through Prompt657 and Prompt655.",
        "current_capability_boundary": "browser_chatgpt_operator_adapter_added_to_external_analysis_handoff",
        "questions": [
            "Confirm whether the browser ChatGPT operator adapter can produce analysis_artifact_v1.",
            "Identify the safest next step after live browser acceptance.",
            "Return exactly one harmless Prompt655-compatible recommended prompt.",
        ],
        "required_output_schema": "analysis_artifact_v1",
        "allowed_next_actions": ["generate_prompt_batch", "manual_review_required"],
        "context_files": [
            "artifacts/autonomous_runtime/prompt658_summary.md",
            "artifacts/autonomous_runtime/prompt657_summary.md",
        ],
    }


def _append_strict_artifact_requirements(envelope: dict[str, Any], request_id: str) -> dict[str, Any]:
    prompt_text = _txt(envelope.get("prompt_text"))
    strict_tail = f"""

STRICT LIVE ACCEPTANCE OUTPUT REQUIREMENTS:
- Return only one JSON object. Do not wrap it in Markdown.
- schema_version must be "analysis_artifact_v1".
- request_id must be "{request_id}".
- source must be "chatgpt_browser".
- status must be "success".
- recommended_next_action must be "generate_prompt_batch".
- recommended_prompts must contain exactly one harmless prompt.
- The one prompt body must ask only for a small documentation/report follow-up; it must not request credential handling, browser profile access, network calls, pushes, PRs, merges, daemon runs, or arbitrary prompt execution.
- expected_tag must be "prompt660-browser-to-codex-full-cycle-acceptance".
- expected_report_path must be "artifacts/autonomous_runtime/prompt660_report.json".
- expected_summary_path must be "artifacts/autonomous_runtime/prompt660_summary.md".
- pass_conditions.status_field must be "prompt660_status" and status_value must be "success".
"""
    envelope = dict(envelope)
    envelope["prompt_text"] = prompt_text + strict_tail
    return envelope


def prepare_live_acceptance(
    *,
    repo_root: str | Path,
    work_root: str | Path = DEFAULT_WORK_ROOT,
    request_id: str = DEFAULT_REQUEST_ID,
) -> dict[str, Any]:
    repo = Path(repo_root)
    work = Path(work_root)
    request = build_live_acceptance_analysis_request(request_id=request_id)
    created = create_browser_request_envelope(request, require_structured_artifact=True)
    if created.get("status") != "success":
        return {"status": "blocked", "errors": created.get("errors", []), "request_envelope_path": ""}
    envelope = _append_strict_artifact_requirements(created["envelope"], request_id)
    request_path = work / "request_envelope.json"
    response_path = work / "live_response_envelope.json"
    artifact_path = work / "live_analysis_artifact.json"
    batch_dir = work / "prompt_batch"
    expected_schema_path = work / "expected_response_envelope_schema.json"
    _write_json(request_path, envelope)
    _write_json(
        expected_schema_path,
        {
            "schema_version": BROWSER_RESPONSE_ENVELOPE_SCHEMA,
            "adapter": BROWSER_OPERATOR_ADAPTER_NAME,
            "request_id": request_id,
            "status": "response_captured|artifact_ready",
            "chatgpt_output": "non-empty JSON string containing analysis_artifact_v1",
            "captured_at": "ISO-8601 timestamp required for live success",
            "metadata": {"page_url": "https://chatgpt.com/..."},
        },
    )
    extension_path = repo / EXTENSION_REL_PATH
    extension = inspect_extension_files(extension_path)
    return {
        "status": "success" if extension.get("status") == "ok" else "blocked",
        "errors": extension.get("errors", []),
        "request_id": request_id,
        "repo_root": repo.as_posix(),
        "work_root": work.as_posix(),
        "request_envelope_path": request_path.as_posix(),
        "response_envelope_path": response_path.as_posix(),
        "analysis_artifact_path": artifact_path.as_posix(),
        "batch_dir": batch_dir.as_posix(),
        "expected_response_envelope_schema_path": expected_schema_path.as_posix(),
        "browser_extension_path": extension_path.as_posix(),
        "browser_extension_path_verified": extension.get("status") == "ok",
        "request_envelope_created": request_path.is_file(),
    }


def operator_steps(
    *,
    repo_root: str | Path,
    work_root: str | Path = DEFAULT_WORK_ROOT,
    request_id: str = DEFAULT_REQUEST_ID,
) -> list[str]:
    prepared = prepare_live_acceptance(repo_root=repo_root, work_root=work_root, request_id=request_id)
    request_path = prepared.get("request_envelope_path", str(Path(work_root) / "request_envelope.json"))
    response_path = prepared.get("response_envelope_path", str(Path(work_root) / "live_response_envelope.json"))
    extension_path = prepared.get("browser_extension_path", str(Path(repo_root) / EXTENSION_REL_PATH))
    return [
        "Open Chrome or Edge.",
        f"Load the unpacked extension from: {extension_path}",
        "Open https://chatgpt.com/ in a normal tab using the operator's already logged-in session.",
        "Do not export, copy, or store cookies, passwords, tokens, browser profile data, or account/session pages.",
        f"Open the request envelope file: {request_path}",
        "Place the entire request envelope JSON into the local bridge request input used by the Prompt658 extension flow.",
        "Click the ChatGPT Runner Bridge extension action on the visible ChatGPT tab.",
        "Wait for the extension to capture the ChatGPT response and emit a browser_chatgpt_response_envelope_v1 JSON object.",
        f"Save that exact response envelope as: {response_path}",
        "Return to the terminal and run:",
        f"python scripts/run_operator_controlled_browser_live_acceptance.py validate-response --repo-root {Path(repo_root).as_posix()} --work-root {Path(work_root).as_posix()} --response-envelope {response_path}",
    ]


def _envelope_live_evidence(payload: Mapping[str, Any], request_id: str) -> tuple[bool, list[str], bool]:
    errors: list[str] = []
    mocked = bool(payload.get("mocked") or payload.get("test_only"))
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else {}
    if payload.get("request_id") != request_id:
        errors.append("response envelope request_id does not match live acceptance request")
    if not _txt(payload.get("chatgpt_output")):
        errors.append("response envelope chatgpt_output is empty")
    if not (
        _txt(payload.get("captured_at"))
        or _txt(payload.get("generated_at"))
        or _txt(metadata.get("captured_at"))
        or _txt(metadata.get("generated_at"))
    ):
        errors.append("response envelope missing captured_at or generated_at timestamp")
    source_text = " ".join(
        [
            _txt(payload.get("adapter")),
            _txt(payload.get("source")),
            _txt(metadata.get("source")),
            _txt(metadata.get("page_url")),
        ]
    ).lower()
    if "chatgpt" not in source_text and "browser_chatgpt_operator_adapter" not in source_text:
        errors.append("response envelope does not indicate ChatGPT/browser adapter origin")
    if mocked:
        errors.append("response envelope is marked mocked/test_only and cannot prove live browser success")
    return not errors, errors, mocked


def validate_live_response(
    *,
    repo_root: str | Path,
    work_root: str | Path = DEFAULT_WORK_ROOT,
    response_envelope: str | Path | None = None,
    request_id: str = DEFAULT_REQUEST_ID,
) -> dict[str, Any]:
    repo = Path(repo_root)
    work = Path(work_root)
    response_path = Path(response_envelope) if response_envelope else work / "live_response_envelope.json"
    payload, read_errors = _read_json(response_path)
    if read_errors:
        return {
            "status": "partial",
            "reason": "response_envelope_missing_or_invalid",
            "errors": read_errors,
            "browser_live_run_performed": False,
            "mocked_only": False,
        }
    envelope, envelope_errors = validate_browser_response_envelope(payload, expected_request_id=request_id)
    live_ok, live_errors, mocked = _envelope_live_evidence(payload, request_id)
    normalized = normalize_browser_response_file_to_analysis_artifact(
        response_path,
        expected_request_id=request_id,
    )
    artifact = normalized.get("artifact", {}) if normalized.get("status") == "success" else {}
    artifact_errors: list[str] = []
    if artifact:
        _, artifact_errors = validate_analysis_artifact(artifact)
    artifact_path = work / "live_analysis_artifact.json"
    if artifact and not artifact_errors:
        _write_json(artifact_path, artifact)
    batch_dir = work / "prompt_batch"
    batch_result = {}
    batch_errors: list[str] = []
    batch_valid_errors: list[str] = []
    analysis_state = {}
    next_prompt = {}
    if artifact and not artifact_errors:
        batch_result = analysis_artifact_to_prompt_batch(artifact, batch_dir)
        batch_errors = list(batch_result.get("errors", []))
        _, batch_valid_errors = load_and_validate(batch_dir)
        if batch_result.get("status") == "success" and not batch_valid_errors:
            analysis_state = analyze_prompt_batch(batch_dir, repo_root=repo.as_posix())
            next_prompt = determine_next_prompt(batch_dir, repo_root=repo.as_posix())
    all_errors = (
        envelope_errors
        + live_errors
        + list(normalized.get("errors", []))
        + artifact_errors
        + batch_errors
        + batch_valid_errors
        + list(analysis_state.get("errors", []))
        + list(next_prompt.get("errors", []))
    )
    response_validated = not envelope_errors
    artifact_normalized = normalized.get("status") == "success" and not artifact_errors
    prompt657_ok = artifact_normalized
    prompt655_ok = batch_result.get("status") == "success" and not batch_valid_errors
    next_prompt_ok = next_prompt.get("status") == "ok" and bool(next_prompt.get("next_prompt"))
    success = bool(live_ok and response_validated and artifact_normalized and prompt655_ok and next_prompt_ok)
    return {
        "status": "success" if success else "partial",
        "reason": "live_acceptance_passed" if success else "live_acceptance_not_proven",
        "errors": all_errors,
        "request_id": request_id,
        "response_envelope_path": response_path.as_posix(),
        "analysis_artifact_path": artifact_path.as_posix(),
        "batch_dir": batch_dir.as_posix(),
        "browser_live_run_performed": success,
        "response_envelope_validated": response_validated,
        "analysis_artifact_normalized": artifact_normalized,
        "prompt657_validation_compatibility_verified": prompt657_ok,
        "prompt655_batch_conversion_compatibility_verified": prompt655_ok,
        "next_prompt_selection_verified": next_prompt_ok,
        "mocked_only": mocked,
        "browser_origin_verified": live_ok,
        "normalized_result": normalized,
        "batch_result": batch_result,
        "batch_analysis": analysis_state,
        "next_prompt": next_prompt,
    }


def run_if_response_present(
    *,
    repo_root: str | Path,
    work_root: str | Path = DEFAULT_WORK_ROOT,
    request_id: str = DEFAULT_REQUEST_ID,
) -> dict[str, Any]:
    response_path = Path(work_root) / "live_response_envelope.json"
    if not response_path.is_file():
        prepared = prepare_live_acceptance(repo_root=repo_root, work_root=work_root, request_id=request_id)
        return {
            "status": "partial",
            "reason": "not_ready_response_envelope_not_present",
            "errors": [f"live response envelope not found: {response_path.as_posix()}"],
            "browser_live_run_performed": False,
            "prepare": prepared,
        }
    return validate_live_response(
        repo_root=repo_root,
        work_root=work_root,
        response_envelope=response_path,
        request_id=request_id,
    )


def inspect_live_acceptance(
    *,
    repo_root: str | Path,
    work_root: str | Path = DEFAULT_WORK_ROOT,
    request_id: str = DEFAULT_REQUEST_ID,
) -> dict[str, Any]:
    repo = Path(repo_root)
    work = Path(work_root)
    extension = inspect_extension_files(repo / EXTENSION_REL_PATH)
    return {
        "status": "ok" if extension.get("status") == "ok" else "blocked",
        "errors": extension.get("errors", []),
        "request_id": request_id,
        "repo_root": repo.as_posix(),
        "work_root": work.as_posix(),
        "request_envelope_path": (work / "request_envelope.json").as_posix(),
        "response_envelope_path": (work / "live_response_envelope.json").as_posix(),
        "browser_extension_path": (repo / EXTENSION_REL_PATH).as_posix(),
        "browser_extension_path_verified": extension.get("status") == "ok",
        "response_envelope_present": (work / "live_response_envelope.json").is_file(),
    }


__all__ = [
    "DEFAULT_REQUEST_ID",
    "DEFAULT_WORK_ROOT",
    "build_live_acceptance_analysis_request",
    "prepare_live_acceptance",
    "operator_steps",
    "validate_live_response",
    "run_if_response_present",
    "inspect_live_acceptance",
]
