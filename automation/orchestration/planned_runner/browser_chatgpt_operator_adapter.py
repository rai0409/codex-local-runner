"""Safe ChatGPT browser-operator adapter (Prompt658).

This module wraps the historical Chrome extension bridge as an artifact protocol.
It never launches a browser, executes JavaScript, calls the network, reads local
secret environment files,
or stores browser credentials. Browser operation remains explicitly operator or
extension mediated.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from automation.orchestration.planned_runner.external_analysis_handoff import (
    ANALYSIS_ARTIFACT_SCHEMA,
    ALLOWED_NEXT_ACTIONS,
    analysis_artifact_to_prompt_batch,
    prepare_next_chatgpt_instruction,
    validate_analysis_artifact,
    validate_analysis_request,
)

BROWSER_REQUEST_ENVELOPE_SCHEMA = "browser_chatgpt_request_envelope_v1"
BROWSER_RESPONSE_ENVELOPE_SCHEMA = "browser_chatgpt_response_envelope_v1"
BROWSER_OPERATOR_ADAPTER_NAME = "browser_chatgpt_operator_adapter"
HISTORICAL_CANDIDATE_COMMIT = "d698389"
HISTORICAL_CANDIDATE_PATH = "browser_extension/chatgpt_runner_bridge/content.js"

ALLOWED_RESPONSE_STATUSES = (
    "response_captured",
    "artifact_ready",
    "manual_review_required",
    "error",
)
SECRET_FIELD_PATTERN = re.compile(r"(cookie|token|password|secret|credential)", re.IGNORECASE)
REQUEST_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
PROMPT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
PROMPT_LABEL_PATTERN = re.compile(r"\bprompt\s+([0-9]+[a-z]?)\b", re.IGNORECASE)
PROMPT_ID_SAFE_CHARS = re.compile(r"[^a-z0-9._-]+")

KNOWN_PROMPT_DEFAULTS = {
    "660d": {
        "prompt_id": "prompt660d_two_cycle_autonomy_proof_harness",
        "expected_tag": "prompt660d_two_cycle_autonomy_proof_harness",
        "expected_report_path": "artifacts/autonomous_runtime/prompt660d_two_cycle_autonomy_proof_harness_report.json",
        "expected_summary_path": "artifacts/autonomous_runtime/prompt660d_two_cycle_autonomy_proof_harness_summary.md",
    },
    "660e": {
        "prompt_id": "prompt660e_two_cycle_proof_harness_tests",
        "expected_tag": "prompt660e_two_cycle_proof_harness_tests",
        "expected_report_path": "artifacts/autonomous_runtime/prompt660e_two_cycle_proof_harness_tests_report.json",
        "expected_summary_path": "artifacts/autonomous_runtime/prompt660e_two_cycle_proof_harness_tests_summary.md",
    },
    "660f": {
        "prompt_id": "prompt660f_two_cycle_evidence_summary_writer",
        "expected_tag": "prompt660f_two_cycle_evidence_summary_writer",
        "expected_report_path": "artifacts/autonomous_runtime/prompt660f_two_cycle_evidence_summary_writer_report.json",
        "expected_summary_path": "artifacts/autonomous_runtime/prompt660f_two_cycle_evidence_summary_writer_summary.md",
    },
}


def _txt(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _load_json_or_markdown_payload(path: str | Path) -> tuple[dict[str, Any], list[str]]:
    p = Path(path)
    if not p.is_file():
        return {}, [f"request file not found: {p.as_posix()}"]
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:
        return {}, [f"request file unreadable: {exc}"]
    try:
        parsed = json.loads(text)
        if isinstance(parsed, Mapping):
            return dict(parsed), []
        return {}, ["request JSON must be an object"]
    except json.JSONDecodeError:
        pass

    marker = "```json"
    start = text.find(marker)
    if start < 0:
        return {}, ["request markdown does not contain a ```json machine-readable request block"]
    start = text.find("\n", start)
    end = text.find("```", start + 1)
    if start < 0 or end < 0:
        return {}, ["request markdown JSON block is incomplete"]
    try:
        parsed = json.loads(text[start:end].strip())
    except json.JSONDecodeError as exc:
        return {}, [f"request markdown JSON block is invalid: {exc}"]
    if not isinstance(parsed, Mapping):
        return {}, ["request markdown JSON block must be an object"]
    return dict(parsed), []


def _find_secret_keys(value: Any, prefix: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            path = f"{prefix}.{key_text}" if prefix else key_text
            if SECRET_FIELD_PATTERN.search(key_text):
                hits.append(path)
            hits.extend(_find_secret_keys(nested, path))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            hits.extend(_find_secret_keys(nested, f"{prefix}[{index}]"))
    return hits


def _fingerprint(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [_txt(item) for item in value if _txt(item)]


def _is_safe_relpath(value: str) -> bool:
    text = _txt(value)
    if not text or text.startswith("/") or text.startswith("~"):
        return False
    if ".." in Path(text).parts or "\x00" in text:
        return False
    return True


def _slug_text(value: Any, *, fallback: str) -> str:
    text = _txt(value).lower()
    slug = PROMPT_ID_SAFE_CHARS.sub("_", text).strip("._-")[:64]
    if not slug:
        slug = fallback
    if not slug[0].isalnum():
        slug = f"p_{slug}"[:64]
    return slug if PROMPT_ID_PATTERN.match(slug) else fallback


def _known_prompt_defaults(value: Any) -> dict[str, str]:
    text = _txt(value)
    match = PROMPT_LABEL_PATTERN.search(text)
    if not match:
        return {}
    return dict(KNOWN_PROMPT_DEFAULTS.get(match.group(1).lower(), {}))


def _generic_prompt_defaults(prompt_id: str) -> dict[str, str]:
    return {
        "prompt_id": prompt_id,
        "expected_tag": prompt_id,
        "expected_report_path": f"artifacts/autonomous_runtime/{prompt_id}_report.json",
        "expected_summary_path": f"artifacts/autonomous_runtime/{prompt_id}_summary.md",
    }


def _safe_prompt_id(raw: Any, *, body: str, index: int, seen: set[str]) -> str:
    known = _known_prompt_defaults(body)
    candidate = _txt(raw) or known.get("prompt_id", "")
    if not candidate or not PROMPT_ID_PATTERN.match(candidate):
        label = PROMPT_LABEL_PATTERN.search(body)
        if label:
            prefix = f"prompt{label.group(1).lower()}"
            remainder = body[label.end():].split(".", 1)[0].split(":", 1)[-1]
            candidate = _slug_text(f"{prefix}_{remainder}", fallback=f"{prefix}_{index}")
        else:
            candidate = _slug_text(body[:80], fallback=f"prompt_{index}")
    base = candidate[:64]
    candidate = base
    suffix = 2
    while candidate in seen:
        suffix_text = f"_{suffix}"
        candidate = f"{base[:64 - len(suffix_text)]}{suffix_text}"
        suffix += 1
    seen.add(candidate)
    return candidate


def _normalize_recommended_prompt(raw: Any, index: int, seen: set[str]) -> dict[str, Any]:
    if isinstance(raw, Mapping):
        body = _txt(raw.get("body"), default=_txt(raw.get("title")))
        if not body:
            body = _txt(raw.get("prompt"), default=_txt(raw.get("description")))
        source_for_defaults = body or _txt(raw.get("prompt_id")) or _txt(raw.get("title"))
        prompt_id = _safe_prompt_id(raw.get("prompt_id"), body=source_for_defaults, index=index, seen=seen)
        existing = dict(raw)
    else:
        body = _txt(raw)
        prompt_id = _safe_prompt_id("", body=body, index=index, seen=seen)
        existing = {}

    if not body:
        body = prompt_id
    known = _known_prompt_defaults(body) or _known_prompt_defaults(prompt_id)
    defaults = known or _generic_prompt_defaults(prompt_id)
    expected_tag = _txt(existing.get("expected_tag"), default=defaults["expected_tag"])
    expected_report_path = _txt(existing.get("expected_report_path"), default=defaults["expected_report_path"])
    expected_summary_path = _txt(existing.get("expected_summary_path"), default=defaults["expected_summary_path"])

    pass_conditions = existing.get("pass_conditions", {})
    if not isinstance(pass_conditions, Mapping):
        pass_conditions = {}
    status_field = _txt(pass_conditions.get("status_field"), default=f"{prompt_id}_status")
    status_value = _txt(pass_conditions.get("status_value"), default="success")

    return {
        "prompt_id": prompt_id,
        "title": _txt(existing.get("title"), default=prompt_id),
        "body": body,
        "expected_tag": expected_tag,
        "expected_report_path": expected_report_path,
        "expected_summary_path": expected_summary_path,
        "required_tests": _str_list(existing.get("required_tests")),
        "pass_conditions": {"status_field": status_field, "status_value": status_value},
    }


def normalize_analysis_artifact_for_prompt655_compatibility(
    payload: Mapping[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Normalize loose ChatGPT analysis artifacts without executing prompt text."""
    if not isinstance(payload, Mapping):
        return {}, ["analysis artifact must be a JSON object"]
    artifact = dict(payload)
    raw_prompts = artifact.get("recommended_prompts", [])
    prompt_items = raw_prompts if isinstance(raw_prompts, list) else []
    action = _txt(artifact.get("recommended_next_action"))
    if action not in ALLOWED_NEXT_ACTIONS:
        artifact["recommended_next_action"] = "generate_prompt_batch" if prompt_items else "manual_review_required"

    errors: list[str] = []
    normalized_prompts: list[dict[str, Any]] = []
    seen: set[str] = set()
    if raw_prompts is not None:
        if not isinstance(raw_prompts, list):
            errors.append("recommended_prompts must be a list")
        else:
            for index, item in enumerate(raw_prompts):
                normalized = _normalize_recommended_prompt(item, index, seen)
                for key in ("expected_report_path", "expected_summary_path"):
                    if not _is_safe_relpath(normalized[key]):
                        errors.append(f"{normalized['prompt_id']}.{key} is not repo-relative safe: {normalized[key]!r}")
                normalized_prompts.append(normalized)
    artifact["recommended_prompts"] = normalized_prompts
    return artifact, errors


def create_browser_request_envelope(
    analysis_request: Mapping[str, Any],
    *,
    require_structured_artifact: bool = True,
) -> dict[str, Any]:
    """Create the envelope consumed by the browser extension/content script."""
    request, errors = validate_analysis_request(analysis_request)
    if errors:
        return {"status": "blocked", "errors": errors, "envelope": {}}
    instruction = prepare_next_chatgpt_instruction(request)
    envelope = {
        "schema_version": BROWSER_REQUEST_ENVELOPE_SCHEMA,
        "adapter": BROWSER_OPERATOR_ADAPTER_NAME,
        "request_id": request["request_id"],
        "source_schema_version": request["schema_version"],
        "target_output_schema": ANALYSIS_ARTIFACT_SCHEMA,
        "require_structured_artifact": bool(require_structured_artifact),
        "allowed_next_actions": list(ALLOWED_NEXT_ACTIONS),
        "status": "request_loaded",
        "prompt_text": instruction,
        "prompt_fingerprint": _fingerprint(instruction),
        "safety": {
            "browser_execution": "operator_or_extension_mediated_only",
            "no_credentials_required": True,
            "no_cookie_or_token_storage": True,
            "no_login_bypass": True,
            "no_repo_side_network": True,
        },
        "provenance": {
            "reused_from_commit": HISTORICAL_CANDIDATE_COMMIT,
            "reused_path": HISTORICAL_CANDIDATE_PATH,
        },
    }
    return {"status": "success", "errors": [], "envelope": envelope}


def create_browser_request_envelope_from_file(
    request_path: str | Path,
    *,
    require_structured_artifact: bool = True,
) -> dict[str, Any]:
    payload, errors = _load_json_or_markdown_payload(request_path)
    if errors:
        return {"status": "blocked", "errors": errors, "envelope": {}}
    return create_browser_request_envelope(
        payload,
        require_structured_artifact=require_structured_artifact,
    )


def validate_browser_response_envelope(
    payload: Mapping[str, Any],
    *,
    expected_request_id: str = "",
) -> tuple[dict[str, Any], list[str]]:
    """Validate a browser response envelope. No artifact acceptance happens here."""
    errors: list[str] = []
    if not isinstance(payload, Mapping):
        return {}, ["response envelope must be a JSON object"]
    secret_keys = _find_secret_keys(payload)
    if secret_keys:
        errors.append(f"response envelope contains prohibited secret-like fields: {secret_keys}")
    schema = _txt(payload.get("schema_version"))
    if schema != BROWSER_RESPONSE_ENVELOPE_SCHEMA:
        errors.append(f"schema_version must be {BROWSER_RESPONSE_ENVELOPE_SCHEMA!r}")
    request_id = _txt(payload.get("request_id"))
    if not request_id or not REQUEST_ID_PATTERN.match(request_id):
        errors.append("request_id must match ^[a-z0-9][a-z0-9._-]{0,63}$")
    if expected_request_id and request_id != expected_request_id:
        errors.append(f"request_id {request_id!r} does not match expected {expected_request_id!r}")
    status = _txt(payload.get("status"))
    if status not in ALLOWED_RESPONSE_STATUSES:
        errors.append(f"status must be one of {list(ALLOWED_RESPONSE_STATUSES)}")
    output = payload.get("chatgpt_output", "")
    if not isinstance(output, str) or not output.strip():
        errors.append("chatgpt_output must be a non-empty string")
    require_structured = bool(payload.get("require_structured_artifact", True))
    envelope = {
        "schema_version": schema,
        "adapter": _txt(payload.get("adapter"), default=BROWSER_OPERATOR_ADAPTER_NAME),
        "request_id": request_id,
        "status": status,
        "chatgpt_output": output if isinstance(output, str) else "",
        "require_structured_artifact": require_structured,
        "metadata": dict(payload.get("metadata", {})) if isinstance(payload.get("metadata"), Mapping) else {},
        "errors": [str(e) for e in payload.get("errors", [])] if isinstance(payload.get("errors"), list) else [],
    }
    return envelope, errors


def normalize_browser_response_to_analysis_artifact(
    response_envelope: Mapping[str, Any],
    *,
    expected_request_id: str = "",
) -> dict[str, Any]:
    """Turn a browser envelope into a Prompt657 analysis_artifact_v1 object."""
    envelope, errors = validate_browser_response_envelope(
        response_envelope,
        expected_request_id=expected_request_id,
    )
    if errors:
        return {"status": "blocked", "errors": errors, "artifact": {}}
    output = envelope["chatgpt_output"].strip()
    try:
        parsed = json.loads(output)
    except json.JSONDecodeError as exc:
        if envelope["require_structured_artifact"]:
            return {
                "status": "blocked",
                "reason": "structured_artifact_required",
                "errors": [f"chatgpt_output is not valid JSON: {exc}"],
                "artifact": {},
            }
        artifact = {
            "schema_version": ANALYSIS_ARTIFACT_SCHEMA,
            "request_id": envelope["request_id"],
            "source": "chatgpt_browser_operator_adapter",
            "status": "manual_review_required",
            "current_state_summary": output,
            "confirmed_completed": [],
            "missing_gaps": ["browser response was raw text, not analysis_artifact_v1 JSON"],
            "recommended_next_action": "manual_review_required",
            "recommended_prompts": [],
            "evaluation_score_out_of_100": 0,
            "risk_notes": ["raw non-JSON browser response requires manual review"],
        }
        norm, artifact_errors = validate_analysis_artifact(artifact)
        return {
            "status": "success" if not artifact_errors else "blocked",
            "reason": "raw_text_wrapped_for_manual_review",
            "errors": artifact_errors,
            "artifact": norm if not artifact_errors else artifact,
        }
    if not isinstance(parsed, Mapping):
        return {"status": "blocked", "errors": ["chatgpt_output JSON must be an object"], "artifact": {}}
    parsed_request_id = _txt(parsed.get("request_id"))
    if parsed_request_id != envelope["request_id"]:
        return {
            "status": "blocked",
            "errors": [
                f"artifact request_id {parsed_request_id!r} does not match envelope {envelope['request_id']!r}"
            ],
            "artifact": {},
        }
    compatible, compatibility_errors = normalize_analysis_artifact_for_prompt655_compatibility(parsed)
    if compatibility_errors:
        return {
            "status": "blocked",
            "reason": "analysis_artifact_prompt655_compatibility_failed",
            "errors": compatibility_errors,
            "artifact": compatible or dict(parsed),
        }
    artifact, artifact_errors = validate_analysis_artifact(compatible)
    return {
        "status": "success" if not artifact_errors else "blocked",
        "reason": "analysis_artifact_valid" if not artifact_errors else "invalid_analysis_artifact",
        "errors": artifact_errors,
        "artifact": artifact,
    }


def normalize_browser_response_file_to_analysis_artifact(
    response_path: str | Path,
    *,
    expected_request_id: str = "",
) -> dict[str, Any]:
    p = Path(response_path)
    if not p.is_file():
        return {"status": "blocked", "errors": [f"response file not found: {p.as_posix()}"], "artifact": {}}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "blocked", "errors": [f"response envelope unreadable/invalid JSON: {exc}"], "artifact": {}}
    if not isinstance(payload, Mapping):
        return {"status": "blocked", "errors": ["response envelope must be a JSON object"], "artifact": {}}
    return normalize_browser_response_to_analysis_artifact(
        payload,
        expected_request_id=expected_request_id,
    )


def inspect_extension_files(extension_dir: str | Path = "browser_extension/chatgpt_runner_bridge") -> dict[str, Any]:
    base = Path(extension_dir)
    expected = ["manifest.json", "content.js", "background.js", "README.md"]
    files = {name: (base / name).is_file() for name in expected}
    errors: list[str] = []
    for name, exists in files.items():
        if not exists:
            errors.append(f"missing extension file: {name}")
    content_text = ""
    if files.get("content.js"):
        content_text = (base / "content.js").read_text(encoding="utf-8")
        for unsafe in ("document.cookie", "localStorage", "sessionStorage"):
            if unsafe in content_text:
                errors.append(f"content.js contains prohibited browser storage access: {unsafe}")
        if HISTORICAL_CANDIDATE_COMMIT not in content_text or HISTORICAL_CANDIDATE_PATH not in content_text:
            errors.append("content.js missing historical provenance comment")
    return {
        "status": "ok" if not errors else "blocked",
        "errors": errors,
        "extension_dir": base.as_posix(),
        "files": files,
        "historical_reuse_documented": not errors and bool(content_text),
    }


def manual_acceptance_steps() -> list[str]:
    return [
        "Create a request envelope with scripts/run_browser_chatgpt_operator_adapter.py create-request-envelope.",
        "Load browser_extension/chatgpt_runner_bridge as an unpacked extension in Chrome or Edge.",
        "Open an already logged-in ChatGPT tab manually; do not provide credentials to this repo.",
        "Use the extension/operator action to submit the request envelope prompt.",
        "Copy or save the produced browser_chatgpt_response_envelope_v1 JSON.",
        "Validate it with validate-response-envelope.",
        "Normalize it with normalize-to-analysis-artifact and then validate/convert through Prompt657.",
    ]


def validate_and_convert_normalized_artifact(
    artifact: Mapping[str, Any],
    batch_dir: str | Path,
) -> dict[str, Any]:
    norm, errors = validate_analysis_artifact(artifact)
    if errors:
        return {"status": "blocked", "errors": errors, "batch_result": {}}
    batch_result = analysis_artifact_to_prompt_batch(norm, batch_dir)
    return {
        "status": "success" if batch_result.get("status") == "success" else "blocked",
        "errors": batch_result.get("errors", []),
        "artifact": norm,
        "batch_result": batch_result,
    }


__all__ = [
    "BROWSER_REQUEST_ENVELOPE_SCHEMA",
    "BROWSER_RESPONSE_ENVELOPE_SCHEMA",
    "BROWSER_OPERATOR_ADAPTER_NAME",
    "HISTORICAL_CANDIDATE_COMMIT",
    "HISTORICAL_CANDIDATE_PATH",
    "create_browser_request_envelope",
    "create_browser_request_envelope_from_file",
    "validate_browser_response_envelope",
    "normalize_analysis_artifact_for_prompt655_compatibility",
    "normalize_browser_response_to_analysis_artifact",
    "normalize_browser_response_file_to_analysis_artifact",
    "inspect_extension_files",
    "manual_acceptance_steps",
    "validate_and_convert_normalized_artifact",
]
