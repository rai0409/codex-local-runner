#!/usr/bin/env python3
"""CLI for Prompt659 operator-controlled browser live acceptance."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if REPO_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, REPO_ROOT.as_posix())

from automation.orchestration.planned_runner.browser_live_acceptance import (  # noqa: E402
    DEFAULT_REQUEST_ID,
    DEFAULT_WORK_ROOT,
    inspect_live_acceptance,
    operator_steps,
    prepare_live_acceptance,
    run_if_response_present,
    validate_live_response,
)


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare and validate operator-controlled ChatGPT browser live acceptance artifacts."
    )
    parser.add_argument(
        "mode",
        choices=["prepare", "print-steps", "validate-response", "run-if-response-present", "inspect"],
    )
    parser.add_argument(
        "--repo-root",
        default=Path.cwd().as_posix(),
        help="Repository root. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--work-root",
        default=DEFAULT_WORK_ROOT,
        help="Local work directory for request/response artifacts.",
    )
    parser.add_argument(
        "--request-id",
        default=DEFAULT_REQUEST_ID,
        help="Expected live acceptance request_id.",
    )
    parser.add_argument(
        "--response-envelope",
        default=None,
        help="Path to response envelope exported by the browser adapter.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.mode == "prepare":
        _print_json(
            prepare_live_acceptance(
                repo_root=args.repo_root,
                work_root=args.work_root,
                request_id=args.request_id,
            )
        )
        return 0
    if args.mode == "print-steps":
        prepared = prepare_live_acceptance(
            repo_root=args.repo_root,
            work_root=args.work_root,
            request_id=args.request_id,
        )
        _print_json(
            {
                "status": prepared.get("status", "blocked"),
                "request_id": args.request_id,
                "work_root": Path(args.work_root).as_posix(),
                "browser_extension_path": prepared.get("browser_extension_path", ""),
                "request_envelope_path": prepared.get("request_envelope_path", ""),
                "response_envelope_path": prepared.get("response_envelope_path", ""),
                "manual_steps": operator_steps(
                    repo_root=args.repo_root,
                    work_root=args.work_root,
                    request_id=args.request_id,
                ),
                "errors": prepared.get("errors", []),
            }
        )
        return 0
    if args.mode == "validate-response":
        _print_json(
            validate_live_response(
                repo_root=args.repo_root,
                work_root=args.work_root,
                response_envelope=args.response_envelope,
                request_id=args.request_id,
            )
        )
        return 0
    if args.mode == "run-if-response-present":
        _print_json(
            run_if_response_present(
                repo_root=args.repo_root,
                work_root=args.work_root,
                request_id=args.request_id,
            )
        )
        return 0
    if args.mode == "inspect":
        _print_json(
            inspect_live_acceptance(
                repo_root=args.repo_root,
                work_root=args.work_root,
                request_id=args.request_id,
            )
        )
        return 0
    raise AssertionError(f"unhandled mode: {args.mode}")


if __name__ == "__main__":
    raise SystemExit(main())
