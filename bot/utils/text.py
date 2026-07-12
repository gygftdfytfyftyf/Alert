from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from bot.config import LOCALES_DIR, DEFAULT_LOCALE


class Locale:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def get(self, key: str, **kwargs: Any) -> str:
        parts = key.split(".")
        node: Any = self._data
        for part in parts:
            if not isinstance(node, dict) or part not in node:
                raise KeyError(f"Missing locale key: {key}")
            node = node[part]
        if not isinstance(node, str):
            raise KeyError(f"Locale key is not a string: {key}")
        return node.format(**kwargs) if kwargs else node


@lru_cache(maxsize=4)
def load_locale(locale: str = DEFAULT_LOCALE) -> Locale:
    path = LOCALES_DIR / f"{locale}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Locale file not found: {path}")
    with path.open(encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    return Locale(data)
