from __future__ import annotations

from dataclasses import dataclass
from typing import Any

TASK_STATUS_PENDING = "pending"
TASK_STATUS_ACCEPTED = "accepted"
TASK_STATUS_FAILED = "failed"


@dataclass(frozen=True)
class DispatchRequest:
    job_id: str
    repo: str
    task_type: str
    goal: str
    provider: str
    metadata: dict[str, Any]
