from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from orchestrator.codex_execution import RunCodexArtifact
from orchestrator.codex_execution import RunCodexResult
from orchestrator.codex_execution import RunCodexStatus
from orchestrator.codex_execution import DEFAULT_CODEX_EXECUTION_TIMEOUT_SECONDS
from orchestrator.codex_execution import execute_codex_cli


def run_codex(
    task: dict,
    prompt: str,
    work_root: str = "tasks/runs",
    *,
    timeout_seconds: object | None = None,
    persist_prompt: bool = True,
    return_transient_stdout: bool = False,
    model: str | None = None,
    model_reasoning_effort: str | None = None,
    emit_json: bool = False,
) -> RunCodexResult:
    configured_timeout = timeout_seconds
    if configured_timeout is None and "execution_timeout_seconds" in task:
        configured_timeout = task["execution_timeout_seconds"]
    if configured_timeout is None:
        configured_timeout = DEFAULT_CODEX_EXECUTION_TIMEOUT_SECONDS
    return execute_codex_cli(
        task=task,
        prompt=prompt,
        work_root=work_root,
        which=shutil.which,
        run_subprocess=subprocess.run,
        now=datetime.now,
        timeout_seconds=configured_timeout,
        persist_prompt=persist_prompt,
        return_transient_stdout=return_transient_stdout,
        model=model,
        model_reasoning_effort=model_reasoning_effort,
        emit_json=emit_json,
    )
