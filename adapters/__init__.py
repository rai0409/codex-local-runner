from __future__ import annotations

from adapters.base import ProviderAdapter
from adapters.chatgpt_tasks import ChatgptTasksAdapter
from adapters.codex_cli import CodexCliAdapter
from adapters.local_llm import LocalLlmAdapter

ADAPTER_CLASS_BY_PATH = {
    "adapters.codex_cli.CodexCliAdapter": CodexCliAdapter,
    "adapters.chatgpt_tasks.ChatgptTasksAdapter": ChatgptTasksAdapter,
    "adapters.local_llm.LocalLlmAdapter": LocalLlmAdapter,
}


def get_registered_adapters() -> dict[str, ProviderAdapter]:
    return {
        "codex_cli": CodexCliAdapter(),
        "chatgpt_tasks": ChatgptTasksAdapter(),
        "local_llm": LocalLlmAdapter(),
    }


def resolve_adapter(provider_name: str, providers_config: dict) -> ProviderAdapter:
    providers = providers_config.get("providers")
    if not isinstance(providers, list):
        raise ValueError("providers config must contain a 'providers' list")

    provider_entry = next(
        (
            item
            for item in providers
            if isinstance(item, dict) and str(item.get("name", "")).strip() == provider_name
        ),
        None,
    )
    if provider_entry is None:
        raise ValueError(f"provider '{provider_name}' is not configured")

    if provider_entry.get("enabled") is False:
        raise ValueError(f"provider '{provider_name}' is disabled")

    adapter_path = str(provider_entry.get("adapter", "")).strip()
    if not adapter_path:
        raise ValueError(f"provider '{provider_name}' is missing adapter path")

    adapter_cls = ADAPTER_CLASS_BY_PATH.get(adapter_path)
    if adapter_cls is None:
        raise ValueError(
            f"provider '{provider_name}' references unsupported adapter '{adapter_path}'"
        )

    return adapter_cls()
