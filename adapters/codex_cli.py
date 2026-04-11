from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from adapters.base import ProviderAdapter
from run_codex import run_codex


class CodexCliAdapter(ProviderAdapter):
    def __init__(self) -> None:
        super().__init__(name="codex_cli")

    def dispatch(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("codex_cli provider execution is not implemented in Phase 1")

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        prompt = str(payload.get("prompt", "")).strip()
        work_dir = Path(str(payload.get("work_dir", ".")).strip() or ".")
        repo_path = str(Path(str(payload.get("repo_path", ".")).strip() or ".").expanduser())

        execution_result = run_codex(
            task={"repo_path": repo_path},
            prompt=prompt,
            work_root=str(work_dir / "execution_runs"),
        )

        meta_path = str(execution_result.get("meta_path", "")).strip()
        started_at = None
        finished_at = None
        if meta_path:
            meta_file = Path(meta_path)
            if meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text(encoding="utf-8"))
                    started_at = meta.get("started_at")
                    finished_at = meta.get("finished_at")
                except Exception:
                    started_at = None
                    finished_at = None

        artifacts = [
            str(execution_result.get("stdout_path", "")),
            str(execution_result.get("stderr_path", "")),
            str(execution_result.get("meta_path", "")),
        ]
        artifacts = [item for item in artifacts if item]

        return {
            "adapter": self.name,
            "status": "completed" if execution_result.get("success") else "failed",
            "started_at": started_at,
            "finished_at": finished_at,
            "artifacts": artifacts,
            "error": execution_result.get("error") or None,
            "return_code": execution_result.get("return_code"),
        }
