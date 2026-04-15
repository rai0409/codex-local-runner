from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from orchestrator.codex_execution import RunCodexArtifact
from orchestrator.codex_execution import RunCodexResult
from orchestrator.codex_execution import RunCodexStatus
from orchestrator.codex_execution import execute_codex_cli


def run_codex(task: dict, prompt: str, work_root: str = "tasks/runs") -> RunCodexResult:
    return execute_codex_cli(
        task=task,
        prompt=prompt,
        work_root=work_root,
        which=shutil.which,
        run_subprocess=subprocess.run,
        now=datetime.now,
    )
