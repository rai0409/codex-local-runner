from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_task_prompt(spec: Mapping[str, Any]) -> str:
    repo_path = spec["repo_path"]
    return (
        f"You are operating only inside {repo_path}.\n"
        f"Modify only {spec['target_file']}.\n"
        f"Add a function named {spec['function_name']}(a, b) that returns {spec['expression']}.\n"
        + "".join(
            f"Do not modify {rel}.\n" for rel in spec.get("expected_unmodified_files", [])
        )
        + "Do not create new files.\n"
        "Do not commit.\n"
        "Do not tag.\n"
        "Do not push.\n"
        "After editing, reply only with:\n"
        f'{{"status":"success","summary":"{spec["task_id"]} applied"}}\n'
    )


def build_task_effect_spec(spec: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "repo_path": spec["repo_path"],
        "expected_modified_files": [spec["target_file"]],
        "expected_unmodified_files": list(spec.get("expected_unmodified_files", [])),
        "required_text": {
            spec["target_file"]: [
                f"def {spec['function_name']}(a, b):",
                f"return {spec['expression']}",
            ]
        },
        "forbidden_paths": [],
        "allow_extra_files": bool(spec.get("allow_extra_files", False)),
        "verify_commands": list(spec.get("verify_commands", [])),
    }


def plan_task(spec: Mapping[str, Any], work_dir: str | Path) -> dict[str, Any]:
    """Turn a validated add_function task spec into per-cycle prompt/effect-spec/manifest files."""
    if spec.get("kind") != "add_function":
        return {
            "status": "blocked",
            "errors": [f"unsupported task kind: {spec.get('kind')}"],
            "codex_invoked": False,
        }
    plan_root = Path(work_dir)
    plan_root.mkdir(parents=True, exist_ok=True)
    task_id = spec["task_id"]

    prompt_path = plan_root / f"{task_id}_prompt.md"
    prompt_path.write_text(build_task_prompt(spec), encoding="utf-8")

    effect_spec_path = plan_root / f"{task_id}_effect_spec.json"
    _write_json(effect_spec_path, build_task_effect_spec(spec))

    manifest_path = plan_root / f"{task_id}_manifest.json"
    _write_json(
        manifest_path,
        {
            "cycles": [
                {
                    "generated_prompt_path": prompt_path.as_posix(),
                    "repo_path": spec["repo_path"],
                    "effect_spec_path": effect_spec_path.as_posix(),
                }
            ]
        },
    )

    return {
        "status": "success",
        "errors": [],
        "task_id": task_id,
        "generated_prompt_path": prompt_path.as_posix(),
        "effect_spec_path": effect_spec_path.as_posix(),
        "manifest_path": manifest_path.as_posix(),
        "cycle_count_planned": 1,
        "codex_invoked": False,
        "local_only": True,
        "generated_at": _utc_now(),
    }


__all__ = ["build_task_effect_spec", "build_task_prompt", "plan_task"]
