from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automation.planning.project_planner import generate_planning_artifacts  # noqa: E402
from automation.planning.project_planner import write_planning_artifacts  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate deterministic planning artifacts from project intake"
    )
    parser.add_argument("--intake", required=True, help="Path to project intake JSON")
    parser.add_argument("--out-dir", required=True, help="Output directory for planning artifacts")
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help="Repository root used for deterministic repo facts collection",
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def _read_intake(path: str) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("intake must be a JSON object")
    return payload


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    intake = _read_intake(args.intake)
    artifacts = generate_planning_artifacts(intake, repo_root=args.repo_root)
    written = write_planning_artifacts(artifacts, args.out_dir)

    report = {
        "project_id": artifacts.get("project_brief", {}).get("project_id"),
        "out_dir": str(Path(args.out_dir).resolve()),
        "written_files": list(written),
    }

    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print(f"project_id={report['project_id']}")
        print(f"out_dir={report['out_dir']}")
        print("written_files=" + ",".join(report["written_files"]))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
