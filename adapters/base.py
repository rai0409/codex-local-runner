from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ProviderAdapter:
    name: str

    def dispatch(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Phase 1 adapters are dispatch stubs")

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("provider execution is not implemented")
