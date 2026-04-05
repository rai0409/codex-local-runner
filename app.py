from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, render_template, request

from prompt_builder import build_prompt
from run_codex import run_codex

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
TASKS_DIR = BASE_DIR / "tasks"
PROMPTS_DIR = BASE_DIR / "prompts"
BASE_RULES_PATH = PROMPTS_DIR / "base_rules.txt"
LATEST_TASK_PATH = TASKS_DIR / "latest_task.json"
LATEST_PROMPT_PATH = TASKS_DIR / "latest_prompt.txt"

LIST_FIELDS = ("allowed_files", "forbidden_files", "validation_commands")
TEXT_FIELDS = ("repo_path", "goal", "notes")


def _split_lines(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


def _normalize_form(form_data: dict[str, str]) -> dict:
    task: dict[str, object] = {}
    for key in TEXT_FIELDS:
        task[key] = form_data.get(key, "").strip()
    for key in LIST_FIELDS:
        task[key] = _split_lines(form_data.get(key, ""))
    return task


def _validate_task(task: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    repo_path_raw = str(task.get("repo_path", "")).strip()
    goal = str(task.get("goal", "")).strip()

    if not repo_path_raw:
        errors.append("repo_path is required.")
    if not goal:
        errors.append("goal is required.")

    if repo_path_raw:
        repo_path = Path(repo_path_raw).expanduser()
        task["repo_path"] = str(repo_path)
        if not repo_path.exists():
            errors.append("repo_path does not exist.")
        elif not (repo_path / ".git").exists():
            warnings.append("Warning: .git was not found in repo_path.")

    return errors, warnings


def _task_to_form_data(task: dict) -> dict[str, str]:
    return {
        "repo_path": str(task.get("repo_path", "")),
        "goal": str(task.get("goal", "")),
        "notes": str(task.get("notes", "")),
        "allowed_files": "\n".join(task.get("allowed_files", [])),
        "forbidden_files": "\n".join(task.get("forbidden_files", [])),
        "validation_commands": "\n".join(task.get("validation_commands", [])),
    }


@app.get("/")
def index():
    form_data = {
        "repo_path": "",
        "goal": "",
        "allowed_files": "",
        "forbidden_files": "",
        "validation_commands": "",
        "notes": "",
    }
    return render_template("index.html", form_data=form_data)


@app.post("/run")
def run():
    form_data = {
        "repo_path": request.form.get("repo_path", ""),
        "goal": request.form.get("goal", ""),
        "allowed_files": request.form.get("allowed_files", ""),
        "forbidden_files": request.form.get("forbidden_files", ""),
        "validation_commands": request.form.get("validation_commands", ""),
        "notes": request.form.get("notes", ""),
    }

    task = _normalize_form(form_data)
    errors, warnings = _validate_task(task)

    if errors:
        return render_template(
            "index.html",
            form_data=form_data,
            errors=errors,
            warnings=warnings,
        )

    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    prompt = build_prompt(task, str(BASE_RULES_PATH))

    LATEST_TASK_PATH.write_text(
        json.dumps(task, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    LATEST_PROMPT_PATH.write_text(prompt, encoding="utf-8")

    result = run_codex(task=task, prompt=prompt, work_root=str(TASKS_DIR / "runs"))

    return render_template(
        "index.html",
        form_data=_task_to_form_data(task),
        warnings=warnings,
        result=result,
        latest_prompt=prompt,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8765)
