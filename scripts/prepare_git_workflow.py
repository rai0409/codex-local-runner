from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automation.orchestration.git_workflow_templates import render_branch_name  # noqa: E402
from automation.orchestration.git_workflow_templates import render_cleanup_steps  # noqa: E402
from automation.orchestration.git_workflow_templates import render_commit_message  # noqa: E402
from automation.orchestration.git_workflow_templates import render_commit_subject  # noqa: E402


def _normalize_lines(values: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        compact = " ".join(str(value).strip().split())
        if not compact or compact in seen:
            continue
        normalized.append(compact)
        seen.add(compact)
    return normalized


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare deterministic local git workflow text")
    parser.add_argument("--prefix", default="", help="Branch prefix; defaults to the first configured policy prefix")
    parser.add_argument("--slug", default=None, help="Branch slug context; defaults to --summary when omitted")
    parser.add_argument("--issue-id", default=None, help="Optional issue token")
    parser.add_argument("--component", default=None, help="Optional commit component prefix")
    parser.add_argument("--summary", required=True, help="Short commit summary context")
    parser.add_argument("--body-line", action="append", default=[], help="Optional commit body line")
    parser.add_argument("--footer-line", action="append", default=[], help="Optional commit footer line")
    parser.add_argument("--include-cleanup", action="store_true", help="Include compact cleanup command hints")
    parser.add_argument(
        "--print-commit-message",
        action="store_true",
        help="Include full commit message in text output",
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    branch_slug = args.slug or args.summary
    body_lines = _normalize_lines(args.body_line)
    footer_lines = _normalize_lines(args.footer_line)

    branch_name = render_branch_name(prefix=args.prefix, slug=branch_slug, issue_id=args.issue_id)
    commit_subject = render_commit_subject(summary=args.summary, component=args.component)
    commit_message = render_commit_message(
        summary=args.summary,
        component=args.component,
        body_lines=body_lines,
        footer_lines=footer_lines,
    )
    suggested_commands = [
        "git checkout main",
        "git pull --ff-only",
        f"git checkout -b {branch_name}",
        "git add -A",
        f'git commit -m "{commit_subject}"',
    ]
    cleanup_steps = list(render_cleanup_steps()) if args.include_cleanup else []

    payload = {
        "branch_name": branch_name,
        "commit_subject": commit_subject,
        "commit_message": commit_message,
        "suggested_commands": suggested_commands,
        "cleanup_steps": cleanup_steps,
    }

    if args.as_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(f"branch_name={payload['branch_name']}")
        print(f"commit_subject={payload['commit_subject']}")
        if args.print_commit_message:
            print("commit_message:")
            print(payload["commit_message"])
        print("suggested_commands:")
        for command in payload["suggested_commands"]:
            print(f"- {command}")
        if cleanup_steps:
            print("cleanup_steps:")
            for step in cleanup_steps:
                print(f"- {step}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
