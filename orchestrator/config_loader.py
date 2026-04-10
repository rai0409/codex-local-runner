from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_yaml_file(path: str | Path) -> Any:
    text = Path(path).read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text)
    except ModuleNotFoundError:
        return json.loads(text)
