from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from orchestrator.job_evaluator import evaluate_job_directory  # noqa: E402
from orchestrator.job_evaluator import format_human_summary  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate an existing orchestration job directory")
    parser.add_argument("--job-dir", required=True)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = evaluate_job_directory(args.job_dir)

    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print(format_human_summary(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
