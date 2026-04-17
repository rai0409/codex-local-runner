from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automation.control.next_action_controller import evaluate_next_action_from_run_dir  # noqa: E402
from automation.control.next_action_controller import load_json_file_if_present  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate deterministic next action from persisted run artifacts")
    parser.add_argument("--run-dir", required=True, help="Run artifact directory containing manifest.json")
    parser.add_argument("--retry-context", default=None, help="Optional retry context JSON path")
    parser.add_argument("--policy-snapshot", default=None, help="Optional policy snapshot JSON path")
    parser.add_argument("--pr-plan", default=None, help="Optional pr_plan.json path")
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        run_dir = Path(args.run_dir)
        retry_context = load_json_file_if_present(args.retry_context)
        policy_snapshot = load_json_file_if_present(args.policy_snapshot)
        pr_plan = load_json_file_if_present(args.pr_plan)

        decision = evaluate_next_action_from_run_dir(
            run_dir,
            retry_context=retry_context,
            policy_snapshot=policy_snapshot,
            pr_plan=pr_plan,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.as_json:
        print(json.dumps(decision, ensure_ascii=False, sort_keys=True))
    else:
        print(f"next_action={decision['next_action']}")
        print(f"reason={decision['reason']}")
        print(f"retry_budget_remaining={decision['retry_budget_remaining']}")
        print(f"whether_human_required={decision['whether_human_required']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
