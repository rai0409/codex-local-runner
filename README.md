# codex-local-runner

Minimal local-only Flask app to submit a Codex task from a phone or PC browser, build a prompt, and run Codex CLI inside a target repository.

## Purpose

- Personal local tool
- Single-user only
- No database, auth, Docker, or external integrations
- Easy to inspect and modify

## Prerequisites

- Python 3.11+
- Codex CLI installed and available as `codex` in your PATH

## Setup

```bash
cd codex-local-runner
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The app listens on `0.0.0.0:8765`.

## Access From Same LAN

Open from another device on the same LAN:

```text
http://<your-computer-ip>:8765
```

## What Happens On Submit

1. Validates `repo_path` and `goal`, checks repo path existence, and warns when `.git` is missing.
2. Saves latest task to `tasks/latest_task.json`.
3. Builds prompt and saves to `tasks/latest_prompt.txt`.
4. If `codex` is available in PATH, creates run artifacts under `tasks/runs/YYYYMMDD_HHMMSS/`.
5. Runs `codex exec` non-interactively using the generated prompt and `cwd=repo_path` (with a timeout).
6. Saves:
   - `task.json`
   - `prompt.txt`
   - `stdout.txt`
   - `stderr.txt`
   - `meta.json`

If `codex` is missing from PATH, the app shows an error and does not create a run directory.

## Verified Current Status

- Mobile and PC access confirmed
- Mobile form submission confirmed
- Non-interactive Codex execution confirmed via `codex exec`
- Per-run artifacts are saved under `tasks/runs/YYYYMMDD_.../`
