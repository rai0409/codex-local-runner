from __future__ import annotations

from typing import Any

from automation.execution.codex_executor_adapter import CodexExecutorAdapter
from automation.orchestration.planned_runner.transports import DryRunCodexExecutionTransport


class PlannedExecutionRunner:
    """Compatibility runner entry point for planned execution orchestration."""

    def __init__(self, *, adapter: CodexExecutorAdapter | None = None) -> None:
        self.adapter = adapter or CodexExecutorAdapter(transport=DryRunCodexExecutionTransport())

    def run(self, **kwargs: Any) -> dict[str, Any]:
        raise RuntimeError(
            "PlannedExecutionRunner.run is unavailable after the mechanical module split; "
            "restore the previous runner class body before executing jobs."
        )


__all__ = ["PlannedExecutionRunner", "DryRunCodexExecutionTransport"]
