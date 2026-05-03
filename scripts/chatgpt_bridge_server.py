#!/usr/bin/env python3
"""Local-only ChatGPT bridge server for Chrome extension handoff MVP."""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

BASE_DIR = Path("/tmp/codex-local-runner-chatgpt-bridge")
REQUEST_PATH = BASE_DIR / "request.md"
RESPONSE_PATH = BASE_DIR / "response.md"
STATUS_PATH = BASE_DIR / "status.json"
HOST = "0.0.0.0"
PORT = 8765


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _ensure_base_dir() -> None:
    BASE_DIR.mkdir(parents=True, exist_ok=True)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _normalize_text(value: str) -> str:
    return " ".join(str(value or "").split()).strip()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _compute_request_fingerprint(prompt: str) -> str:
    normalized = _normalize_text(prompt)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"sha256:{digest}:{len(normalized)}"


def _request_created_at(path: Path) -> str:
    try:
        stat = path.stat()
    except FileNotFoundError:
        return ""
    created = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    return created.replace(microsecond=0).isoformat()


def _request_mtime_ns(path: Path) -> int:
    try:
        stat = path.stat()
    except FileNotFoundError:
        return 0
    return int(getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000)))


def _build_task_identity(prompt: str) -> dict[str, Any]:
    fingerprint = _compute_request_fingerprint(prompt)
    created_at = _request_created_at(REQUEST_PATH)
    mtime_ns = _request_mtime_ns(REQUEST_PATH)
    task_id = f"task-{fingerprint.split(':', 1)[1][:16]}-{mtime_ns}"
    return {
        "task_id": task_id,
        "request_fingerprint": fingerprint,
        "created_at": created_at,
    }


def _map_runtime_status_to_task_status(status: str, reason: str) -> str:
    normalized_status = str(status or "").strip().lower()
    normalized_reason = str(reason or "").strip().lower()

    if normalized_status in {"response_saved", "result_saved"} or normalized_reason == "result_saved":
        return "response_saved"
    if normalized_status == "blocked":
        return "blocked"
    if normalized_status in {"running", "sent"}:
        return "in_progress"
    if normalized_status == "consumed":
        return "consumed"
    return "ready"


def _build_next_task_payload() -> dict[str, Any]:
    prompt = _read_text(REQUEST_PATH)
    if not prompt.strip():
        return {
            "has_task": False,
            "prompt": "",
            "task_id": "",
            "request_fingerprint": "",
            "created_at": "",
            "attempt_count": 0,
            "status": "consumed",
        }

    identity = _build_task_identity(prompt)
    existing = _read_status()
    existing_task_id = str(existing.get("task_id") or "")
    existing_fingerprint = str(existing.get("request_fingerprint") or existing.get("task_fingerprint") or "")
    is_same_task = (
        existing_task_id == identity["task_id"]
        and existing_fingerprint == identity["request_fingerprint"]
    )

    if is_same_task:
        raw_task_status = str(existing.get("task_status") or "")
        task_status = raw_task_status if raw_task_status in {
            "ready",
            "in_progress",
            "response_saved",
            "blocked",
            "consumed",
        } else _map_runtime_status_to_task_status(
            str(existing.get("status") or ""),
            str(existing.get("reason") or ""),
        )
        attempt_count = _safe_int(existing.get("attempt_count"), 0)
    else:
        task_status = "ready"
        attempt_count = 0

    has_task = task_status == "ready"
    return {
        "has_task": has_task,
        "prompt": prompt if has_task else "",
        "task_id": identity["task_id"],
        "request_fingerprint": identity["request_fingerprint"],
        "created_at": identity["created_at"],
        "attempt_count": attempt_count,
        "status": task_status,
    }


def _read_status() -> dict[str, Any]:
    if not STATUS_PATH.exists():
        return {"status": "idle"}
    try:
        loaded = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"status": "idle"}
    if isinstance(loaded, dict):
        return loaded
    return {"status": "idle"}


def _write_status(payload: dict[str, Any]) -> None:
    _ensure_base_dir()
    STATUS_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _merge_status(update: dict[str, Any]) -> dict[str, Any]:
    existing = _read_status()
    existing.update(update)
    existing["updated_at"] = _now_iso()
    _write_status(existing)
    return existing


class BridgeHandler(BaseHTTPRequestHandler):
    server_version = "chatgpt-bridge/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
        # Keep logs concise and free of request content.
        super().log_message(fmt, *args)

    def _set_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._set_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _parse_json_body(self) -> tuple[dict[str, Any] | None, str | None]:
        content_length = self.headers.get("Content-Length", "0")
        try:
            size = max(0, int(content_length))
        except ValueError:
            return None, "invalid_content_length"
        raw = self.rfile.read(size) if size else b""
        if not raw:
            return {}, None
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except Exception:
            return None, "invalid_json"
        if not isinstance(parsed, dict):
            return None, "json_object_required"
        return parsed, None

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self._set_cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        _ensure_base_dir()
        if self.path == "/next-task":
            self._send_json(_build_next_task_payload())
            return

        if self.path == "/status":
            self._send_json(_read_status())
            return

        self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        _ensure_base_dir()

        if self.path == "/result":
            payload, error = self._parse_json_body()
            if error:
                self._send_json({"error": error}, status=HTTPStatus.BAD_REQUEST)
                return
            response_text = payload.get("response") if isinstance(payload, dict) else None
            if not isinstance(response_text, str):
                self._send_json({"error": "response_string_required"}, status=HTTPStatus.BAD_REQUEST)
                return

            RESPONSE_PATH.write_text(response_text, encoding="utf-8")
            metadata = payload.get("metadata") if isinstance(payload, dict) else None
            next_task = _build_next_task_payload()
            task_id = str(payload.get("task_id") or next_task.get("task_id") or "")
            request_fingerprint = str(
                payload.get("request_fingerprint")
                or payload.get("task_fingerprint")
                or next_task.get("request_fingerprint")
                or ""
            )
            created_at = str(payload.get("created_at") or next_task.get("created_at") or "")
            attempt_count = _safe_int(next_task.get("attempt_count"), 0)
            status_payload = {
                "status": "response_saved",
                "reason": "result_received",
                "task_status": "response_saved",
                "task_id": task_id,
                "request_fingerprint": request_fingerprint,
                "created_at": created_at,
                "attempt_count": attempt_count,
                "response_path": str(RESPONSE_PATH),
                "response_length": len(response_text),
                "result_received_at": _now_iso(),
            }
            if isinstance(metadata, dict):
                status_payload["metadata"] = metadata

            merged = _merge_status(status_payload)
            self._send_json({"ok": True, "status": merged})
            return

        if self.path == "/status":
            payload, error = self._parse_json_body()
            if error:
                self._send_json({"error": error}, status=HTTPStatus.BAD_REQUEST)
                return
            if payload is None:
                payload = {}
            next_task = _build_next_task_payload()
            task_id = str(payload.get("task_id") or next_task.get("task_id") or "")
            request_fingerprint = str(
                payload.get("request_fingerprint")
                or payload.get("task_fingerprint")
                or next_task.get("request_fingerprint")
                or ""
            )
            created_at = str(payload.get("created_at") or next_task.get("created_at") or "")
            status_value = str(payload.get("status") or "")
            reason_value = str(payload.get("reason") or "")

            existing = _read_status()
            same_task = (
                str(existing.get("task_id") or "") == task_id
                and str(existing.get("request_fingerprint") or existing.get("task_fingerprint") or "") == request_fingerprint
            )
            attempt_count = _safe_int(existing.get("attempt_count"), 0) if same_task else 0
            if status_value.lower() == "running" and reason_value == "task_fetched":
                attempt_count += 1

            merged = _merge_status(payload)
            merged["task_id"] = task_id
            merged["request_fingerprint"] = request_fingerprint
            merged["created_at"] = created_at
            merged["attempt_count"] = attempt_count
            merged["task_status"] = _map_runtime_status_to_task_status(status_value, reason_value)
            _write_status(merged)
            self._send_json({"ok": True, "status": merged})
            return

        self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)


def main() -> int:
    _ensure_base_dir()
    with ThreadingHTTPServer((HOST, PORT), BridgeHandler) as server:
        print(f"ChatGPT bridge server listening on http://{HOST}:{PORT}")
        print(f"request.md: {REQUEST_PATH}")
        print(f"response.md: {RESPONSE_PATH}")
        print(f"status.json: {STATUS_PATH}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
