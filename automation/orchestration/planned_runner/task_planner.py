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


SUPPORTED_PLAN_KINDS = ("add_function", "add_file", "bounded_implementation")


def _build_add_file_prompt(spec: Mapping[str, Any]) -> str:
    repo_path = spec["repo_path"]
    content = spec["content"]
    parent = (
        "Create any parent directories required for the target file.\n"
        if spec.get("create_parent_dirs")
        else "Do not create directories other than what the target file strictly requires.\n"
    )
    overwrite = (
        ""
        if spec.get("allow_overwrite")
        else f"Do not overwrite any existing file; {spec['target_file']} must be a new file.\n"
    )
    return (
        f"You are operating only inside {repo_path}.\n"
        f"Create a new text file at {spec['target_file']} with EXACTLY the following content:\n"
        "--- BEGIN CONTENT ---\n"
        f"{content}\n"
        "--- END CONTENT ---\n"
        + parent
        + overwrite
        + "Do not modify any other file.\n"
        + "".join(
            f"Do not modify {rel}.\n" for rel in spec.get("expected_unmodified_files", [])
        )
        + "Do not commit.\n"
        "Do not tag.\n"
        "Do not push.\n"
        "After editing, reply only with:\n"
        f'{{"status":"success","summary":"{spec["task_id"]} applied"}}\n'
    )


def build_task_prompt(spec: Mapping[str, Any]) -> str:
    repo_path = spec["repo_path"]
    if spec.get("kind") == "add_file":
        return _build_add_file_prompt(spec)
    if spec.get("kind") == "bounded_implementation":
        allowed_files = "\n".join(f"- {path}" for path in spec["allowed_files"])
        required_behavior = "\n".join(
            f"- {item}" for item in spec.get("required_behavior", [])
        )
        prohibited_behavior = "\n".join(
            f"- {item}" for item in spec.get("prohibited_behavior", [])
        )
        return (
            f"You are operating only inside {repo_path}.\n"
            f"Goal: {spec['goal']}\n"
            "Modify only these allowed files:\n"
            f"{allowed_files}\n"
            "Required behavior:\n"
            f"{required_behavior}\n"
            "Prohibited behavior:\n"
            f"{prohibited_behavior}\n"
            "Do not modify, create, or delete files outside the allowed files.\n"
            "Do not commit.\n"
            "Do not tag.\n"
            "Do not push.\n"
            "After editing, reply only with:\n"
            f'{{"status":"success","summary":"{spec["task_id"]} applied"}}\n'
        )
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
    allowed_files = list(spec.get("allowed_files", [spec["target_file"]]))
    if spec.get("kind") == "bounded_implementation":
        return {
            "repo_path": spec["repo_path"],
            "allowed_files": allowed_files,
            "expected_modified_files": allowed_files,
            "expected_unmodified_files": list(spec.get("expected_unmodified_files", [])),
            "required_text": dict(spec.get("required_text", {})),
            "forbidden_paths": [],
            "allow_extra_files": False,
            "verify_commands": list(spec.get("verify_commands", [])),
        }
    if spec.get("kind") == "add_file":
        # Require the file to contain its content (trailing newline tolerated). The
        # strict effect gate verifies ONLY the target file is created/modified.
        required_snippet = str(spec["content"]).rstrip("\n")
        return {
            "repo_path": spec["repo_path"],
            "allowed_files": allowed_files,
            "expected_modified_files": [spec["target_file"]],
            "expected_unmodified_files": list(spec.get("expected_unmodified_files", [])),
            "required_text": {spec["target_file"]: [required_snippet]},
            "forbidden_paths": [],
            "allow_extra_files": bool(spec.get("allow_extra_files", False)),
            "verify_commands": list(spec.get("verify_commands", [])),
        }
    return {
        "repo_path": spec["repo_path"],
        "allowed_files": allowed_files,
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
    """Turn a validated task spec (add_function or add_file) into per-cycle
    prompt/effect-spec/manifest files."""
    if spec.get("kind") not in SUPPORTED_PLAN_KINDS:
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
