"""Local-only compatibility server for the ChatGPT Runner Bridge (Prompt659A).

The historical bridge used a Chrome extension background script that fetched a
local runner server and relayed content-script status/results. This module keeps
that shape, but binds to loopback by default and validates all response envelopes
through the Prompt658/657/655 artifact path.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping

from automation.orchestration.planned_runner.browser_chatgpt_operator_adapter import (
    BROWSER_OPERATOR_ADAPTER_NAME,
    BROWSER_REQUEST_ENVELOPE_SCHEMA,
    BROWSER_RESPONSE_ENVELOPE_SCHEMA,
    create_browser_request_envelope,
    normalize_browser_response_to_analysis_artifact,
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

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_WORK_ROOT = "/tmp/codex-local-runner-chatgpt-bridge"
DEFAULT_REQUEST_ID = "prompt659a_bridge_server"
HISTORICAL_CANDIDATE_COMMIT = "d698389"
HISTORICAL_CANDIDATE_PATH = "browser_extension/chatgpt_runner_bridge/content.js"
PROTOCOL_CLASSIFICATION = "local_runner_server_protocol_found"
LEGACY_ENDPOINTS = ["/next-task", "/status", "/result"]
ENVELOPE_ENDPOINTS = ["/health", "/request", "/response", "/status"]
PRIVATE_BIND_RANGES = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _txt(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _fingerprint(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.is_file():
        return {}, [f"file not found: {path.as_posix()}"]
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, [f"invalid JSON: {exc}"]
    if not isinstance(loaded, Mapping):
        return {}, ["JSON payload must be an object"]
    return dict(loaded), []


def _request_prompt_text(envelope: Mapping[str, Any]) -> str:
    for key in ("prompt_text", "prompt"):
        value = envelope.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [_txt(v) for v in value if _txt(v)]


def build_prompt_text_from_instruction_request(payload: Mapping[str, Any]) -> str:
    """Build a bridge prompt from a higher-level instruction-style request artifact."""
    request_id = _txt(payload.get("request_id"))
    instruction = _txt(payload.get("instruction"))
    boundary = _txt(payload.get("current_capability_boundary"))
    requested_schemas = _str_list(payload.get("requested_output_schema_versions"))
    schema_text = ", ".join(requested_schemas) if requested_schemas else "analysis_artifact_v1"
    lines = [
        f"ANALYSIS REQUEST: {request_id}",
    ]
    if boundary:
        lines += ["", f"Current capability boundary: {boundary}"]
    lines += [
        "",
        "Instruction:",
        instruction,
        "",
        f"Requested output schema versions: {schema_text}",
        "",
        "Return ONE JSON object only. Do not include markdown, commentary, or extra text.",
        "The JSON object must use schema_version=\"analysis_artifact_v1\" and include these fields:",
        "- schema_version",
        "- request_id",
        "- source",
        "- status",
        "- current_state_summary",
        "- confirmed_completed[]",
        "- missing_gaps[]",
        "- recommended_next_action",
        "- recommended_prompts[]",
        "- evaluation_score_out_of_100",
        "- risk_notes[]",
        "",
        f"The request_id field must be \"{request_id}\".",
        "Use source=\"chatgpt_browser\" and status=\"success\" when the analysis succeeds.",
        "",
        "Safety constraints:",
        "- No secrets.",
        "- No credentials.",
        "- No cookies.",
        "- No browser profile data.",
        "- No private session files.",
        f"- No {'.'}env values.",
        "- No remote pushes.",
        "- No PRs.",
        "- No merges.",
        "- No destructive operations.",
        "- No arbitrary prompt execution.",
    ]
    return "\n".join(lines) + "\n"


def normalize_bridge_request_envelope(payload: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Normalize full bridge envelopes and instruction-style request artifacts."""
    errors: list[str] = []
    if not isinstance(payload, Mapping):
        return {}, ["request envelope must be a JSON object"]
    schema = _txt(payload.get("schema_version"))
    if schema != BROWSER_REQUEST_ENVELOPE_SCHEMA:
        errors.append(f"schema_version must be {BROWSER_REQUEST_ENVELOPE_SCHEMA!r}")
    request_id = _txt(payload.get("request_id"))
    if not request_id:
        errors.append("request_id is required")
    prompt_text = _request_prompt_text(payload)
    instruction = _txt(payload.get("instruction"))
    if not prompt_text:
        if instruction and request_id:
            prompt_text = build_prompt_text_from_instruction_request(payload)
        else:
            errors.append("prompt_text, prompt, or instruction is required")
    envelope = dict(payload)
    envelope["schema_version"] = schema
    envelope["adapter"] = _txt(envelope.get("adapter"), default=BROWSER_OPERATOR_ADAPTER_NAME)
    envelope["request_id"] = request_id
    envelope["status"] = _txt(envelope.get("status"), default="request_loaded")
    if prompt_text:
        envelope["prompt_text"] = prompt_text
    if "prompt_fingerprint" not in envelope and prompt_text:
        envelope["prompt_fingerprint"] = _fingerprint(prompt_text)
    return envelope, errors


def validate_browser_request_envelope(payload: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Validate the local browser request envelope shape consumed by the extension."""
    return normalize_bridge_request_envelope(payload)


def _load_request_envelope_file(path: str | Path) -> tuple[dict[str, Any], list[str]]:
    payload, errors = _read_json(Path(path))
    if errors:
        return {}, errors
    return validate_browser_request_envelope(payload)


def _write_prepared_request(paths: Mapping[str, Path], envelope: Mapping[str, Any]) -> None:
    prompt_text = _request_prompt_text(envelope)
    _write_json(paths["request_envelope"], envelope)
    paths["legacy_request"].parent.mkdir(parents=True, exist_ok=True)
    paths["legacy_request"].write_text(prompt_text, encoding="utf-8")
    _write_json(
        paths["status"],
        {
            "status": "request_prepared",
            "request_id": _txt(envelope.get("request_id")),
            "request_envelope_path": paths["request_envelope"].as_posix(),
            "updated_at": _now_iso(),
        },
    )


def is_safe_bridge_bind_host(host: str, *, allow_private_host_bind: bool = False) -> bool:
    """Return whether a bridge bind host is safe under the current mode."""
    normalized = _txt(host).lower()
    if normalized in {"127.0.0.1", "localhost"}:
        return True
    if not normalized or normalized == "0.0.0.0":
        return False
    try:
        address = ipaddress.ip_address(normalized)
    except ValueError:
        return False
    if address.version != 4:
        return False
    if address.is_loopback:
        return True
    if not allow_private_host_bind:
        return False
    return any(address in network for network in PRIVATE_BIND_RANGES)


def inspect_protocol(repo_root: str | Path = ".") -> dict[str, Any]:
    repo = Path(repo_root)
    background = repo / "browser_extension" / "chatgpt_runner_bridge" / "background.js"
    content = repo / "browser_extension" / "chatgpt_runner_bridge" / "content.js"
    manifest = repo / "browser_extension" / "chatgpt_runner_bridge" / "manifest.json"
    evidence: list[str] = []
    errors: list[str] = []
    background_text = background.read_text(encoding="utf-8") if background.is_file() else ""
    content_text = content.read_text(encoding="utf-8") if content.is_file() else ""
    manifest_text = manifest.read_text(encoding="utf-8") if manifest.is_file() else ""
    if "127.0.0.1:8765" in background_text or "127.0.0.1:8765" in manifest_text:
        evidence.append("current extension references 127.0.0.1:8765")
    if "/next-task" in background_text and "/status" in background_text and "/result" in background_text:
        evidence.append("background.js fetches /next-task, /status, and /result")
    if "BRIDGE_GET_NEXT_TASK" in content_text and "BRIDGE_POST_RESULT" in content_text:
        evidence.append("content.js relays through chrome.runtime messages to the background fetch layer")
    if not evidence:
        errors.append("local runner server protocol evidence not found in current extension files")
    return {
        "status": "ok" if not errors else "partial",
        "errors": errors,
        "historical_candidate_commit": HISTORICAL_CANDIDATE_COMMIT,
        "historical_candidate_path": HISTORICAL_CANDIDATE_PATH,
        "old_protocol_classification": PROTOCOL_CLASSIFICATION if evidence else "artifact_adapter_only_no_live_browser_protocol",
        "old_endpoints_found": bool(evidence),
        "expected_endpoints": {
            "legacy": list(LEGACY_ENDPOINTS),
            "envelope_native": list(ENVELOPE_ENDPOINTS),
        },
        "expected_request_shape": {
            "legacy_next_task": {
                "has_task": True,
                "prompt": "stringified browser_chatgpt_request_envelope_v1",
                "task_id": DEFAULT_REQUEST_ID,
                "request_fingerprint": "sha256:<prompt>",
            },
            "native_request": "browser_chatgpt_request_envelope_v1",
        },
        "expected_response_shape": {
            "legacy_result": {"response": "JSON string containing browser_chatgpt_response_envelope_v1"},
            "native_response": "browser_chatgpt_response_envelope_v1",
        },
        "current_prompt658_adapter_matches": True,
        "compatibility_server_can_be_implemented_safely": True,
        "evidence": evidence,
    }


def build_bridge_analysis_request(request_id: str = DEFAULT_REQUEST_ID) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "project_goal": "Verify ChatGPT Runner Bridge local server compatibility for external analysis handoff.",
        "current_capability_boundary": "browser_chatgpt_operator_adapter_added_to_external_analysis_handoff",
        "questions": [
            "Confirm the local bridge server compatibility path.",
            "Return one safe next prompt for the browser-to-Codex full cycle.",
        ],
        "required_output_schema": "analysis_artifact_v1",
        "allowed_next_actions": ["generate_prompt_batch", "manual_review_required"],
        "context_files": [
            "artifacts/autonomous_runtime/prompt658_summary.md",
            "artifacts/autonomous_runtime/prompt659_summary.md",
        ],
    }


def _append_output_contract(envelope: dict[str, Any], request_id: str) -> dict[str, Any]:
    envelope = dict(envelope)
    prompt_text = _txt(envelope.get("prompt_text"))
    envelope["prompt_text"] = prompt_text + f"""

STRICT BRIDGE SERVER ACCEPTANCE OUTPUT:
- Return only one JSON object.
- schema_version must be "analysis_artifact_v1".
- request_id must be "{request_id}".
- source must be "chatgpt_browser".
- status must be "success".
- recommended_next_action must be "generate_prompt_batch".
- recommended_prompts must contain exactly one safe prompt.
- The prompt must be a bounded report/acceptance follow-up and must not ask for credentials, browser profiles, remote pushes, PRs, merges, daemon execution, or arbitrary prompt execution.
"""
    envelope["status"] = "request_loaded"
    return envelope


def prepare_bridge_work(
    *,
    repo_root: str | Path = ".",
    work_root: str | Path = DEFAULT_WORK_ROOT,
    request_id: str = DEFAULT_REQUEST_ID,
    request_envelope_path: str | Path | None = None,
) -> dict[str, Any]:
    work = Path(work_root)
    paths = bridge_paths(work)
    explicit_path = Path(request_envelope_path) if request_envelope_path else None
    if explicit_path:
        envelope, envelope_errors = _load_request_envelope_file(explicit_path)
        if envelope_errors:
            return {"status": "blocked", "errors": envelope_errors, "request_envelope_path": explicit_path.as_posix()}
        _write_prepared_request(paths, envelope)
    elif paths["request_envelope"].is_file():
        envelope, envelope_errors = _load_request_envelope_file(paths["request_envelope"])
        if envelope_errors:
            return {
                "status": "blocked",
                "errors": envelope_errors,
                "request_envelope_path": paths["request_envelope"].as_posix(),
            }
        _write_prepared_request(paths, envelope)
    else:
        request = build_bridge_analysis_request(request_id)
        created = create_browser_request_envelope(request)
        if created.get("status") != "success":
            return {"status": "blocked", "errors": created.get("errors", []), "request_envelope_path": ""}
        envelope = _append_output_contract(created["envelope"], request_id)
        _write_prepared_request(paths, envelope)
    protocol = inspect_protocol(repo_root)
    prepared_request_id = _txt(envelope.get("request_id"), default=request_id)
    return {
        "status": "success" if protocol["old_endpoints_found"] else "partial",
        "errors": protocol.get("errors", []),
        "request_id": prepared_request_id,
        "work_root": work.as_posix(),
        "request_envelope_path": paths["request_envelope"].as_posix(),
        "legacy_request_path": paths["legacy_request"].as_posix(),
        "response_envelope_path": paths["response_envelope"].as_posix(),
        "analysis_artifact_path": paths["analysis_artifact"].as_posix(),
        "batch_dir": paths["batch_dir"].as_posix(),
        "old_protocol_classification": protocol["old_protocol_classification"],
        "old_endpoints_found": protocol["old_endpoints_found"],
        "host": DEFAULT_HOST,
        "port": DEFAULT_PORT,
    }


def bridge_paths(work_root: str | Path) -> dict[str, Path]:
    work = Path(work_root)
    return {
        "work_root": work,
        "request_envelope": work / "request_envelope.json",
        "legacy_request": work / "request.md",
        "response_envelope": work / "response_envelope.json",
        "legacy_response": work / "response.md",
        "analysis_artifact": work / "analysis_artifact.json",
        "batch_dir": work / "prompt_batch",
        "status": work / "status.json",
    }


def load_prepared_request(work_root: str | Path = DEFAULT_WORK_ROOT) -> tuple[dict[str, Any], list[str]]:
    paths = bridge_paths(work_root)
    return _read_json(paths["request_envelope"])


def active_request_id(work_root: str | Path = DEFAULT_WORK_ROOT, fallback: str = DEFAULT_REQUEST_ID) -> str:
    envelope, errors = load_prepared_request(work_root)
    if errors:
        return fallback
    return _txt(envelope.get("request_id"), default=fallback)


def _coerce_legacy_result_payload(payload: Mapping[str, Any], request_id: str) -> tuple[dict[str, Any], list[str]]:
    response = payload.get("response")
    if not isinstance(response, str) or not response.strip():
        return {}, ["response string required"]
    try:
        parsed = json.loads(response)
    except json.JSONDecodeError:
        parsed = {
            "schema_version": BROWSER_RESPONSE_ENVELOPE_SCHEMA,
            "adapter": BROWSER_OPERATOR_ADAPTER_NAME,
            "request_id": request_id,
            "status": "response_captured",
            "chatgpt_output": response,
            "require_structured_artifact": True,
            "metadata": payload.get("metadata", {}) if isinstance(payload.get("metadata"), Mapping) else {},
            "errors": [],
        }
    if not isinstance(parsed, Mapping):
        return {}, ["response JSON must be an object"]
    return dict(parsed), []


def accept_response_envelope(
    payload: Mapping[str, Any],
    *,
    repo_root: str | Path = ".",
    work_root: str | Path = DEFAULT_WORK_ROOT,
    request_id: str = DEFAULT_REQUEST_ID,
    legacy_result_payload: bool = False,
) -> dict[str, Any]:
    paths = bridge_paths(work_root)
    if legacy_result_payload:
        envelope_payload, coerce_errors = _coerce_legacy_result_payload(payload, request_id)
    else:
        envelope_payload, coerce_errors = dict(payload), []
    if coerce_errors:
        return _write_status_result(paths, "blocked", coerce_errors)
    envelope, envelope_errors = validate_browser_response_envelope(
        envelope_payload,
        expected_request_id=request_id,
    )
    if envelope_errors:
        return _write_status_result(paths, "blocked", envelope_errors)
    _write_json(paths["response_envelope"], envelope_payload)
    paths["legacy_response"].write_text(envelope["chatgpt_output"], encoding="utf-8")
    normalized = normalize_browser_response_to_analysis_artifact(envelope_payload, expected_request_id=request_id)
    if normalized.get("status") != "success":
        return _write_status_result(paths, "blocked", list(normalized.get("errors", [])))
    artifact = normalized["artifact"]
    _, artifact_errors = validate_analysis_artifact(artifact)
    if artifact_errors:
        return _write_status_result(paths, "blocked", artifact_errors)
    _write_json(paths["analysis_artifact"], artifact)
    batch_result = analysis_artifact_to_prompt_batch(artifact, paths["batch_dir"])
    _, batch_errors = load_and_validate(paths["batch_dir"])
    if batch_result.get("status") != "success" or batch_errors:
        return _write_status_result(paths, "blocked", list(batch_result.get("errors", [])) + batch_errors)
    batch_analysis = analyze_prompt_batch(paths["batch_dir"], repo_root=Path(repo_root).as_posix())
    next_prompt = determine_next_prompt(paths["batch_dir"], repo_root=Path(repo_root).as_posix())
    success = next_prompt.get("status") == "ok" and bool(next_prompt.get("next_prompt"))
    result = {
        "status": "success" if success else "blocked",
        "errors": [] if success else list(next_prompt.get("errors", [])),
        "request_id": request_id,
        "response_envelope_validated": True,
        "analysis_artifact_normalized": True,
        "prompt657_validation_compatibility_verified": True,
        "prompt655_batch_conversion_compatibility_verified": True,
        "next_prompt_selection_verified": success,
        "response_envelope_path": paths["response_envelope"].as_posix(),
        "analysis_artifact_path": paths["analysis_artifact"].as_posix(),
        "batch_dir": paths["batch_dir"].as_posix(),
        "batch_result": batch_result,
        "batch_analysis": batch_analysis,
        "next_prompt": next_prompt,
        "updated_at": _now_iso(),
    }
    _write_json(paths["status"], result)
    return result


def _write_status_result(paths: Mapping[str, Path], status: str, errors: list[str]) -> dict[str, Any]:
    result = {
        "status": status,
        "errors": errors,
        "response_envelope_validated": False,
        "analysis_artifact_normalized": False,
        "prompt657_validation_compatibility_verified": False,
        "prompt655_batch_conversion_compatibility_verified": False,
        "next_prompt_selection_verified": False,
        "updated_at": _now_iso(),
    }
    _write_json(paths["status"], result)
    return result


def current_status(work_root: str | Path = DEFAULT_WORK_ROOT) -> dict[str, Any]:
    paths = bridge_paths(work_root)
    status, errors = _read_json(paths["status"])
    if errors:
        return {"status": "idle", "errors": [], "request_prepared": paths["request_envelope"].is_file()}
    status["request_prepared"] = paths["request_envelope"].is_file()
    status["response_present"] = paths["response_envelope"].is_file()
    return status


def dispatch_local_request(
    *,
    method: str,
    path: str,
    body: Mapping[str, Any] | None = None,
    repo_root: str | Path = ".",
    work_root: str | Path = DEFAULT_WORK_ROOT,
    request_id: str = DEFAULT_REQUEST_ID,
) -> tuple[int, dict[str, Any]]:
    """Pure endpoint dispatcher used by tests when sockets are sandboxed."""
    method = method.upper()
    work = Path(work_root)
    repo = Path(repo_root)
    payload = dict(body or {})
    if method == "GET" and path == "/health":
        return 200, {"status": "ok", "host": DEFAULT_HOST, "request_id": active_request_id(work, request_id)}
    if method == "GET" and path in {"/request", "/next-task"}:
        envelope, errors = load_prepared_request(work)
        if errors:
            prepared = prepare_bridge_work(repo_root=repo, work_root=work, request_id=request_id)
            envelope, errors = load_prepared_request(work)
            if errors:
                return 404, {"has_task": False, "errors": errors + list(prepared.get("errors", []))}
        if path == "/request":
            return 200, envelope
        prompt = json.dumps(envelope, ensure_ascii=False, indent=2, sort_keys=True)
        return 200, {
            "has_task": True,
            "status": "accepted",
            "task_id": envelope.get("request_id", request_id),
            "prompt": prompt,
            "request_fingerprint": envelope.get("prompt_fingerprint") or _fingerprint(prompt),
        }
    if method == "GET" and path == "/status":
        return 200, current_status(work)
    if method == "POST" and path == "/request":
        envelope, errors = validate_browser_request_envelope(payload)
        if errors:
            return 400, {"status": "blocked", "errors": errors}
        paths = bridge_paths(work)
        _write_prepared_request(paths, envelope)
        return 200, {
            "status": "success",
            "request_id": envelope["request_id"],
            "request_envelope_path": paths["request_envelope"].as_posix(),
        }
    if method == "POST" and path == "/status":
        paths = bridge_paths(work)
        existing = current_status(work)
        existing.update(payload)
        existing["updated_at"] = _now_iso()
        _write_json(paths["status"], existing)
        return 200, {"ok": True, "status": existing}
    if method == "POST" and path == "/response":
        result = accept_response_envelope(payload, repo_root=repo, work_root=work, request_id=active_request_id(work, request_id))
        return (200 if result.get("status") == "success" else 400), result
    if method == "POST" and path == "/result":
        result = accept_response_envelope(
            payload,
            repo_root=repo,
            work_root=work,
            request_id=active_request_id(work, request_id),
            legacy_result_payload=True,
        )
        return (200 if result.get("status") == "success" else 400), {
            "ok": result.get("status") == "success",
            "status": result,
        }
    return 404, {"error": "not_found"}


def dispatch_raw_local_request(
    *,
    method: str,
    path: str,
    raw_body: str | bytes = b"",
    repo_root: str | Path = ".",
    work_root: str | Path = DEFAULT_WORK_ROOT,
    request_id: str = DEFAULT_REQUEST_ID,
) -> tuple[int, dict[str, Any]]:
    raw = raw_body.decode("utf-8") if isinstance(raw_body, bytes) else str(raw_body or "")
    if raw.strip():
        try:
            loaded = json.loads(raw)
        except json.JSONDecodeError as exc:
            return 400, {"status": "blocked", "errors": [f"malformed JSON: {exc}"]}
        if not isinstance(loaded, Mapping):
            return 400, {"status": "blocked", "errors": ["JSON body must be an object"]}
        body = dict(loaded)
    else:
        body = {}
    return dispatch_local_request(
        method=method,
        path=path,
        body=body,
        repo_root=repo_root,
        work_root=work_root,
        request_id=request_id,
    )


def run_once_if_response_present(
    *,
    repo_root: str | Path = ".",
    work_root: str | Path = DEFAULT_WORK_ROOT,
    request_id: str = DEFAULT_REQUEST_ID,
) -> dict[str, Any]:
    paths = bridge_paths(work_root)
    if not paths["response_envelope"].is_file():
        prepared = prepare_bridge_work(repo_root=repo_root, work_root=work_root, request_id=request_id)
        return {
            "status": "partial",
            "reason": "not_ready_response_envelope_not_present",
            "errors": [f"response envelope not found: {paths['response_envelope'].as_posix()}"],
            "prepare": prepared,
        }
    payload, errors = _read_json(paths["response_envelope"])
    if errors:
        return _write_status_result(paths, "blocked", errors)
    return accept_response_envelope(
        payload,
        repo_root=repo_root,
        work_root=work_root,
        request_id=active_request_id(work_root, request_id),
    )


def extension_steps(
    *,
    repo_root: str | Path = ".",
    work_root: str | Path = DEFAULT_WORK_ROOT,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
) -> list[str]:
    extension_dir = Path(repo_root) / "browser_extension" / "chatgpt_runner_bridge"
    return [
        f"Start the local bridge server on http://{host}:{port} with mode=serve.",
        "For Windows/WSL, discover the WSL IP with: hostname -I | awk '{print $1}'",
        f"Use: python scripts/run_chatgpt_runner_bridge_server.py serve --repo-root {Path(repo_root).as_posix()} --work-root {Path(work_root).as_posix()} --host <WSL_IP> --port {port} --allow-private-host-bind",
        f"From PowerShell, test: curl.exe http://<WSL_IP>:{port}/health",
        f"Configure the extension bridge URL to: http://<WSL_IP>:{port}",
        f"Load the unpacked extension from: {extension_dir.as_posix()}",
        "Open ChatGPT in a normal browser tab using an already logged-in operator session.",
        "Click the ChatGPT Runner Bridge extension action on the visible ChatGPT tab.",
        f"The extension fetches GET http://{host}:{port}/next-task and posts status/result back to the same local server.",
        f"Inspect validation output under: {Path(work_root).as_posix()}",
    ]


def make_handler(
    *,
    repo_root: str | Path,
    work_root: str | Path,
    request_id: str = DEFAULT_REQUEST_ID,
) -> type[BaseHTTPRequestHandler]:
    repo = Path(repo_root)
    work = Path(work_root)

    class ChatgptRunnerBridgeHandler(BaseHTTPRequestHandler):
        server_version = "chatgpt-runner-bridge/0.2"

        def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
            return

        def _cors(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

        def _send_json(self, payload: Mapping[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(dict(payload), ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self._cors()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_body_json(self) -> tuple[dict[str, Any], list[str]]:
            raw_size = self.headers.get("Content-Length", "0")
            try:
                size = max(0, int(raw_size))
            except ValueError:
                return {}, ["invalid content length"]
            raw = self.rfile.read(size) if size else b""
            if not raw:
                return {}, []
            try:
                loaded = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError as exc:
                return {}, [f"malformed JSON: {exc}"]
            if not isinstance(loaded, Mapping):
                return {}, ["JSON body must be an object"]
            return dict(loaded), []

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(HTTPStatus.NO_CONTENT)
            self._cors()
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            code, payload = dispatch_local_request(
                method="GET",
                path=self.path,
                repo_root=repo,
                work_root=work,
                request_id=request_id,
            )
            self._send_json(payload, HTTPStatus(code))

        def do_POST(self) -> None:  # noqa: N802
            payload, errors = self._read_body_json()
            if errors:
                self._send_json({"status": "blocked", "errors": errors}, HTTPStatus.BAD_REQUEST)
                return
            code, result = dispatch_local_request(
                method="POST",
                path=self.path,
                body=payload,
                repo_root=repo,
                work_root=work,
                request_id=request_id,
            )
            self._send_json(result, HTTPStatus(code))

    return ChatgptRunnerBridgeHandler


def create_server(
    *,
    repo_root: str | Path = ".",
    work_root: str | Path = DEFAULT_WORK_ROOT,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    request_id: str = DEFAULT_REQUEST_ID,
    request_envelope_path: str | Path | None = None,
    allow_private_host_bind: bool = False,
) -> ThreadingHTTPServer:
    if not is_safe_bridge_bind_host(host, allow_private_host_bind=allow_private_host_bind):
        raise ValueError(
            "bridge server host must be loopback by default; private IPv4 WSL binds require --allow-private-host-bind"
        )
    prepared = prepare_bridge_work(
        repo_root=repo_root,
        work_root=work_root,
        request_id=request_id,
        request_envelope_path=request_envelope_path,
    )
    if prepared.get("status") == "blocked":
        raise ValueError("; ".join(str(e) for e in prepared.get("errors", [])) or "request preparation failed")
    handler = make_handler(repo_root=repo_root, work_root=work_root, request_id=request_id)
    return ThreadingHTTPServer((host, port), handler)


__all__ = [
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "DEFAULT_REQUEST_ID",
    "DEFAULT_WORK_ROOT",
    "PROTOCOL_CLASSIFICATION",
    "is_safe_bridge_bind_host",
    "inspect_protocol",
    "prepare_bridge_work",
    "build_prompt_text_from_instruction_request",
    "normalize_bridge_request_envelope",
    "validate_browser_request_envelope",
    "load_prepared_request",
    "active_request_id",
    "accept_response_envelope",
    "current_status",
    "dispatch_local_request",
    "dispatch_raw_local_request",
    "run_once_if_response_present",
    "extension_steps",
    "make_handler",
    "create_server",
]
