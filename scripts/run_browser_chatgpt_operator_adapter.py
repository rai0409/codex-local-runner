#!/usr/bin/env python3
"""CLI for Prompt658 browser ChatGPT operator adapter.

Safe by default: no browser launch, no network calls, no JS execution, no credential
storage. This CLI creates and validates local JSON envelopes only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if REPO_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, REPO_ROOT.as_posix())

from automation.orchestration.planned_runner.browser_chatgpt_operator_adapter import (  # noqa: E402
    create_browser_request_envelope_from_file,
    inspect_extension_files,
    manual_acceptance_steps,
    normalize_browser_response_file_to_analysis_artifact,
    validate_browser_response_envelope,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safe browser ChatGPT operator adapter")
    parser.add_argument(
        "mode",
        choices=[
            "create-request-envelope",
            "validate-response-envelope",
            "normalize-to-analysis-artifact",
            "inspect-extension",
            "print-manual-steps",
        ],
    )
    parser.add_argument("--request", default="")
    parser.add_argument("--response", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--expected-request-id", default="")
    parser.add_argument("--allow-raw-text", action="store_true")
    parser.add_argument("--extension-dir", default="browser_extension/chatgpt_runner_bridge")
    return parser


def _write_json_if_requested(result: dict, output: str) -> dict:
    if not output:
        return result
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = result.get("envelope") or result.get("artifact") or result
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    result = dict(result)
    result["output_path"] = out.as_posix()
    return result


def _load_response(path: str) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("response envelope must be a JSON object")
    return payload


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.mode == "create-request-envelope":
            if not args.request:
                result = {"status": "blocked", "errors": ["--request required"]}
            else:
                result = create_browser_request_envelope_from_file(
                    args.request,
                    require_structured_artifact=not args.allow_raw_text,
                )
                result = _write_json_if_requested(result, args.output)
        elif args.mode == "validate-response-envelope":
            if not args.response:
                result = {"status": "blocked", "errors": ["--response required"]}
            else:
                envelope, errors = validate_browser_response_envelope(
                    _load_response(args.response),
                    expected_request_id=args.expected_request_id,
                )
                result = {
                    "status": "ok" if not errors else "blocked",
                    "errors": errors,
                    "envelope": envelope,
                }
        elif args.mode == "normalize-to-analysis-artifact":
            if not args.response:
                result = {"status": "blocked", "errors": ["--response required"]}
            else:
                result = normalize_browser_response_file_to_analysis_artifact(
                    args.response,
                    expected_request_id=args.expected_request_id,
                )
                result = _write_json_if_requested(result, args.output)
        elif args.mode == "inspect-extension":
            result = inspect_extension_files(args.extension_dir)
        else:
            result = {"status": "ok", "manual_steps": manual_acceptance_steps()}
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        result = {"status": "blocked", "errors": [str(exc)]}

    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if str(result.get("status")) in {"ok", "success"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
