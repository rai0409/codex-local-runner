#!/usr/bin/env python3
"""CLI for Prompt659A ChatGPT Runner Bridge compatibility server."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if REPO_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, REPO_ROOT.as_posix())

from automation.orchestration.planned_runner.chatgpt_runner_bridge_server import (  # noqa: E402
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_REQUEST_ID,
    DEFAULT_WORK_ROOT,
    accept_response_envelope,
    create_server,
    extension_steps,
    inspect_protocol,
    is_safe_bridge_bind_host,
    prepare_bridge_work,
    run_once_if_response_present,
)


def _print_json(payload: MappingPayload) -> None:
    print(json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True))


MappingPayload = dict[str, Any]


def _read_json_file(path: str) -> tuple[MappingPayload, list[str]]:
    if not path:
        return {}, ["--response-envelope required"]
    p = Path(path)
    if not p.is_file():
        return {}, [f"response envelope not found: {p.as_posix()}"]
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, [f"response envelope unreadable/invalid JSON: {exc}"]
    if not isinstance(payload, dict):
        return {}, ["response envelope must be a JSON object"]
    return payload, []


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local-only ChatGPT Runner Bridge compatibility server")
    parser.add_argument(
        "mode",
        choices=[
            "inspect-protocol",
            "prepare",
            "serve",
            "validate-response",
            "run-once-if-response-present",
            "print-extension-steps",
            "diagnose-windows-wsl-reachability",
        ],
    )
    parser.add_argument("--repo-root", default=Path.cwd().as_posix())
    parser.add_argument("--work-root", default=DEFAULT_WORK_ROOT)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--request-id", default=DEFAULT_REQUEST_ID)
    parser.add_argument(
        "--request-envelope-path",
        default="",
        help="Use an existing browser_chatgpt_request_envelope_v1 JSON file instead of generating the default request.",
    )
    parser.add_argument("--response-envelope", default="")
    parser.add_argument(
        "--allow-private-host-bind",
        action="store_true",
        help="Allow binding to explicit RFC1918 private IPv4 addresses for Windows/WSL browser reachability.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.mode == "inspect-protocol":
        _print_json(inspect_protocol(args.repo_root))
        return 0
    if args.mode == "prepare":
        _print_json(
            prepare_bridge_work(
                repo_root=args.repo_root,
                work_root=args.work_root,
                request_id=args.request_id,
                request_envelope_path=args.request_envelope_path or None,
            )
        )
        return 0
    if args.mode == "validate-response":
        payload, errors = _read_json_file(args.response_envelope)
        if errors:
            _print_json({"status": "blocked", "errors": errors})
            return 0
        _print_json(
            accept_response_envelope(
                payload,
                repo_root=args.repo_root,
                work_root=args.work_root,
                request_id=args.request_id,
            )
        )
        return 0
    if args.mode == "run-once-if-response-present":
        _print_json(
            run_once_if_response_present(
                repo_root=args.repo_root,
                work_root=args.work_root,
                request_id=args.request_id,
            )
        )
        return 0
    if args.mode == "print-extension-steps":
        _print_json(
            {
                "status": "ok",
                "manual_steps": extension_steps(
                    repo_root=args.repo_root,
                    work_root=args.work_root,
                    host=args.host,
                    port=args.port,
                ),
            }
        )
        return 0
    if args.mode == "diagnose-windows-wsl-reachability":
        safe = is_safe_bridge_bind_host(args.host, allow_private_host_bind=args.allow_private_host_bind)
        _print_json(
            {
                "status": "ok",
                "host": args.host,
                "port": args.port,
                "host_allowed": safe,
                "allow_private_host_bind": bool(args.allow_private_host_bind),
                "loopback_default_preserved": is_safe_bridge_bind_host("127.0.0.1"),
                "zero_zero_zero_zero_rejected": not is_safe_bridge_bind_host(
                    "0.0.0.0",
                    allow_private_host_bind=True,
                ),
                "wsl_ip_detection_command": "hostname -I | awk '{print $1}'",
                "serve_private_wsl_command": (
                    "python scripts/run_chatgpt_runner_bridge_server.py serve "
                    "--repo-root /home/rai/codex-local-runner "
                    "--work-root /tmp/codex-local-runner-chatgpt-bridge "
                    "--host <WSL_IP> --port 8765 --allow-private-host-bind"
                ),
                "powershell_health_check": "curl.exe http://<WSL_IP>:8765/health",
                "extension_bridge_url": "http://<WSL_IP>:8765",
            }
        )
        return 0
    if args.mode == "serve":
        server = create_server(
            repo_root=args.repo_root,
            work_root=args.work_root,
            host=args.host,
            port=args.port,
            request_id=args.request_id,
            request_envelope_path=args.request_envelope_path or None,
            allow_private_host_bind=args.allow_private_host_bind,
        )
        print(f"ChatGPT Runner Bridge server listening on http://{args.host}:{args.port}")
        print(f"work_root={Path(args.work_root).as_posix()}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return 0
    raise AssertionError(f"unhandled mode: {args.mode}")


if __name__ == "__main__":
    raise SystemExit(main())
