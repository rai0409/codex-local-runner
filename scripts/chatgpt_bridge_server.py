#!/usr/bin/env python3
"""Local-only ChatGPT bridge server for Chrome extension handoff MVP."""

from __future__ import annotations

import json
import os
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
            prompt = _read_text(REQUEST_PATH)
            has_task = bool(prompt.strip())
            self._send_json({"has_task": has_task, "prompt": prompt if has_task else ""})
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
            status_payload = {
                "status": "response_saved",
                "reason": "result_received",
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
            merged = _merge_status(payload)
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
