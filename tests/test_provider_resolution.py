from __future__ import annotations

import unittest

from adapters import resolve_adapter
from adapters.chatgpt_tasks import ChatgptTasksAdapter
from adapters.codex_cli import CodexCliAdapter
from adapters.local_llm import LocalLlmAdapter
from orchestrator.config_loader import load_yaml_file


class ProviderResolutionTests(unittest.TestCase):
    def test_provider_config_loads(self) -> None:
        config = load_yaml_file("config/providers.yaml")
        self.assertIsInstance(config, dict)
        self.assertIsInstance(config.get("providers"), list)

    def test_resolve_codex_cli(self) -> None:
        config = load_yaml_file("config/providers.yaml")
        adapter = resolve_adapter("codex_cli", config)
        self.assertIsInstance(adapter, CodexCliAdapter)

    def test_resolve_chatgpt_tasks(self) -> None:
        config = load_yaml_file("config/providers.yaml")
        adapter = resolve_adapter("chatgpt_tasks", config)
        self.assertIsInstance(adapter, ChatgptTasksAdapter)

    def test_resolve_local_llm(self) -> None:
        config = load_yaml_file("config/providers.yaml")
        adapter = resolve_adapter("local_llm", config)
        self.assertIsInstance(adapter, LocalLlmAdapter)

    def test_unknown_provider_fails_clearly(self) -> None:
        config = load_yaml_file("config/providers.yaml")
        with self.assertRaisesRegex(ValueError, "is not configured"):
            resolve_adapter("unknown_provider", config)

    def test_disabled_provider_fails_clearly(self) -> None:
        config = {
            "providers": [
                {
                    "name": "codex_cli",
                    "adapter": "adapters.codex_cli.CodexCliAdapter",
                    "enabled": False,
                }
            ]
        }
        with self.assertRaisesRegex(ValueError, "is disabled"):
            resolve_adapter("codex_cli", config)


if __name__ == "__main__":
    unittest.main()
