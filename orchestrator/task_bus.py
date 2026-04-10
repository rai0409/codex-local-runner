from __future__ import annotations

from datetime import datetime, timezone

from orchestrator.models import TASK_STATUS_ACCEPTED, TASK_STATUS_FAILED, DispatchRequest


def dispatch(request: DispatchRequest, providers_config: dict) -> dict:
    provider_names = {
        str(item.get("name", "")).strip()
        for item in providers_config.get("providers", [])
        if isinstance(item, dict)
    }

    if request.provider in provider_names:
        return {
            "status": TASK_STATUS_ACCEPTED,
            "accepted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "job_id": request.job_id,
            "repo": request.repo,
            "task_type": request.task_type,
            "provider": request.provider,
            "message": "orchestration intake accepted",
            "dispatcher": "orchestrator.task_bus.dispatch",
        }

    return {
        "status": TASK_STATUS_FAILED,
        "accepted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "job_id": request.job_id,
        "repo": request.repo,
        "task_type": request.task_type,
        "provider": request.provider,
        "message": "provider not registered",
        "dispatcher": "orchestrator.task_bus.dispatch",
    }
