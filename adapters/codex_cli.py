from __future__ import annotations

from typing import Any

from adapters.base import ProviderAdapter


class CodexCliAdapter(ProviderAdapter):
    def __init__(self) -> None:
        super().__init__(name="codex_cli")

    def dispatch(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("codex_cli provider execution is not implemented in Phase 1")
