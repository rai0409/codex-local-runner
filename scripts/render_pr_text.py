from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automation.orchestration.pr_text_templates import render_pr_body  # noqa: E402
from automation.orchestration.pr_text_templates import render_pr_title  # noqa: E402


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
    parser = argparse.ArgumentParser(description="Render deterministic PR title/body text")
    parser.add_argument("--scope", default=None, help="Optional component/scope token")
    parser.add_argument("--summary", required=True, help="Compact PR summary")
    parser.add_argument("--change", action="append", default=[], help="What changed line (repeatable)")
    parser.add_argument("--validation", action="append", default=[], help="Validation line (repeatable)")
    parser.add_argument("--scope-note", action="append", default=[], help="Scope note line (repeatable)")
    parser.add_argument(
        "--out-of-scope",
        action="append",
        default=[],
        help="Out-of-scope line; rendered under Scope notes with deterministic prefix",
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    summary = " ".join(str(args.summary).strip().split())
    what_changed = _normalize_lines(args.change) or [summary]
    validation = _normalize_lines(args.validation)

    scope_notes = _normalize_lines(args.scope_note)
    scope_notes.extend(f"Out of scope: {item}" for item in _normalize_lines(args.out_of_scope))
    scope_notes = _normalize_lines(scope_notes)

    title = render_pr_title(summary=summary, scope=args.scope)
    body = render_pr_body(
        summary=summary,
        what_changed=what_changed,
        validation=validation,
        scope_notes=scope_notes,
    )
    payload = {
        "pr_title": title,
        "pr_body": body,
    }

    if args.as_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(f"pr_title={payload['pr_title']}")
        print("pr_body:")
        print(payload["pr_body"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
