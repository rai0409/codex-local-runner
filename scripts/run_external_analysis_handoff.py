#!/usr/bin/env python3
"""CLI for the external analysis handoff controller (Prompt657).

Safe by default: NO browser automation, NO network, NO prompt execution, NO
Codex/daemon execution, NO git mutation. Artifact-based handoff only.

Modes: create-request | validate-artifact | to-batch | evaluate | next-instruction
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if REPO_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, REPO_ROOT.as_posix())

from automation.orchestration.planned_runner.external_analysis_handoff import (  # noqa: E402
    ALLOWED_NEXT_ACTIONS,
    analysis_artifact_to_prompt_batch,
    create_analysis_request,
    evaluate_analysis_artifact,
    load_analysis_artifact,
    prepare_next_chatgpt_instruction,
    validate_analysis_artifact,
    validate_analysis_request,
)


def _default_request(request_id: str) -> dict:
    return {
        "request_id": request_id,
        "project_goal": "Advance codex-local-runner toward project-level autonomous development",
        "current_capability_boundary": "two_executable_task_kinds_add_function_and_add_file_live_proven",
        "questions": ["What is complete?", "What is missing?", "What should be implemented next?"],
        "required_output_schema": "analysis_artifact_v1",
        "allowed_next_actions": list(ALLOWED_NEXT_ACTIONS),
        "context_files": ["artifacts/autonomous_runtime/prompt656_summary.md"],
    }


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="External analysis handoff controller (safe, offline)")
    p.add_argument("mode", choices=["create-request", "validate-artifact", "to-batch", "evaluate", "next-instruction"])
    p.add_argument("--output", default="")
    p.add_argument("--request-id", default="analysis001")
    p.add_argument("--request-json", default="", help="JSON string/path overriding the default request")
    p.add_argument("--artifact", default="")
    p.add_argument("--batch-dir", default="")
    return p


def _load_request(args) -> dict:
    if not args.request_json:
        return _default_request(args.request_id)
    text = args.request_json
    candidate = Path(text)
    if candidate.is_file():
        text = candidate.read_text(encoding="utf-8")
    return json.loads(text)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.mode == "create-request":
            if not args.output:
                result = {"status": "blocked", "errors": ["--output required for create-request"]}
            else:
                result = create_analysis_request(_load_request(args), args.output)
        elif args.mode == "next-instruction":
            request, errors = validate_analysis_request(_load_request(args))
            result = {"status": "blocked" if errors else "ok", "errors": errors,
                      "instruction": prepare_next_chatgpt_instruction(request) if not errors else ""}
        elif args.mode == "validate-artifact":
            loaded = load_analysis_artifact(args.artifact)
            if loaded["errors"]:
                result = {"status": "blocked", "errors": loaded["errors"]}
            else:
                artifact, errors = validate_analysis_artifact(loaded["payload"])
                result = {"status": "ok" if not errors else "blocked", "errors": errors, "artifact": artifact}
        elif args.mode == "evaluate":
            loaded = load_analysis_artifact(args.artifact)
            result = {"status": "blocked", "errors": loaded["errors"]} if loaded["errors"] else evaluate_analysis_artifact(loaded["payload"])
        else:  # to-batch
            if not args.batch_dir:
                result = {"status": "blocked", "errors": ["--batch-dir required for to-batch"]}
            else:
                loaded = load_analysis_artifact(args.artifact)
                result = {"status": "blocked", "errors": loaded["errors"]} if loaded["errors"] else analysis_artifact_to_prompt_batch(loaded["payload"], args.batch_dir)
    except json.JSONDecodeError as exc:
        result = {"status": "blocked", "errors": [f"invalid JSON input: {exc}"]}

    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if str(result.get("status", "")) in ("ok", "success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
