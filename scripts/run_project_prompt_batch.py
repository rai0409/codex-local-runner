#!/usr/bin/env python3
"""CLI for the project prompt-batch controller (Prompt655).

Safe by default: NO arbitrary prompt execution, NO test command execution, NO git
mutation. Reads a batch manifest and verifies operator-produced evidence; writes
receipts/evaluations/reports only under
artifacts/autonomous_runtime/prompt_batches/<batch_id>/ when a writing mode is used.

Modes: analyze | next | record-receipt | evaluate | advance
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if REPO_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, REPO_ROOT.as_posix())

from automation.orchestration.planned_runner.project_prompt_batch_controller import (  # noqa: E402
    advance_prompt_batch,
    analyze_prompt_batch,
    determine_next_prompt,
    evaluate_prompt_result,
    record_prompt_receipt,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Project prompt-batch controller (safe, offline)")
    p.add_argument("mode", choices=["analyze", "next", "record-receipt", "evaluate", "advance"])
    p.add_argument("--batch-dir", required=True)
    p.add_argument("--repo-root", default=REPO_ROOT.as_posix())
    p.add_argument("--prompt-id", default="")
    p.add_argument("--receipt-json", default="", help="JSON string for record-receipt mode")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.mode == "analyze":
        result = analyze_prompt_batch(args.batch_dir, repo_root=args.repo_root)
    elif args.mode == "next":
        result = determine_next_prompt(args.batch_dir, repo_root=args.repo_root)
    elif args.mode == "record-receipt":
        if not args.prompt_id:
            result = {"status": "blocked", "errors": ["--prompt-id required for record-receipt"]}
        else:
            try:
                receipt = json.loads(args.receipt_json) if args.receipt_json else {}
            except json.JSONDecodeError as exc:
                receipt = {}
                print(json.dumps({"status": "blocked", "errors": [f"invalid --receipt-json: {exc}"]}))
                return 1
            result = record_prompt_receipt(args.batch_dir, args.prompt_id, receipt, repo_root=args.repo_root)
    elif args.mode == "evaluate":
        if not args.prompt_id:
            result = {"status": "blocked", "errors": ["--prompt-id required for evaluate"]}
        else:
            result = evaluate_prompt_result(args.batch_dir, args.prompt_id, repo_root=args.repo_root)
    else:  # advance
        result = advance_prompt_batch(args.batch_dir, repo_root=args.repo_root)

    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    status = str(result.get("status", ""))
    return 0 if status in ("ok", "ready", "complete", "pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
