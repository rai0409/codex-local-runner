from __future__ import annotations

from typing import Any

from adapters.base import ProviderAdapter


class ChatgptTasksAdapter(ProviderAdapter):
    def __init__(self) -> None:
        super().__init__(name="chatgpt_tasks")

    def dispatch(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("chatgpt_tasks provider execution is not implemented in Phase 1")
