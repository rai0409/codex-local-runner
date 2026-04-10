from __future__ import annotations

from typing import Any

from adapters.base import ProviderAdapter


class LocalLlmAdapter(ProviderAdapter):
    def __init__(self) -> None:
        super().__init__(name="local_llm")

    def dispatch(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("local_llm provider execution is not implemented in Phase 1")
