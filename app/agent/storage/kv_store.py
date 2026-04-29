from __future__ import annotations

import json
import os
from typing import Any, Iterator, Sequence

from langchain_core.stores import BaseStore

from ..utils import logger


class JsonKVStore(BaseStore[str, str]):

    def __init__(self, namespace: str, working_dir: str):
        self.namespace = namespace
        self.file_path = os.path.join(working_dir, f"{namespace}.json")
        self.working_dir = working_dir
        self._data: dict[str, str] = {}

    async def initialize(self) -> None:
        os.makedirs(self.working_dir, exist_ok=True)
        if os.path.exists(self.file_path):
            with open(self.file_path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        logger.debug(f"JsonKVStore loaded: {self.file_path} ({len(self._data)} keys)")

    async def finalize(self) -> None:
        os.makedirs(self.working_dir, exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def mget(self, keys: Sequence[str]) -> list[str | None]:
        return [self._data.get(k) for k in keys]

    def mset(self, key_value_pairs: Sequence[tuple[str, str]]) -> None:
        for k, v in key_value_pairs:
            self._data[k] = v

    def mdelete(self, keys: Sequence[str]) -> None:
        for k in keys:
            self._data.pop(k, None)

    def yield_keys(self, *, prefix: str | None = None) -> Iterator[str]:
        for k in self._data:
            if prefix is None or k.startswith(prefix):
                yield k

    async def filter_keys(self, keys: set[str]) -> set[str]:
        return {k for k in keys if k not in self._data}

    async def get_by_id(self, id: str) -> dict | None:
        raw = self._data.get(id)
        if raw is None:
            return None
        return json.loads(raw)

    async def upsert(self, data: dict[str, Any]) -> None:
        for k, v in data.items():
            self._data[k] = json.dumps(v, ensure_ascii=False)

    async def drop(self) -> None:
        self._data.clear()
        if os.path.exists(self.file_path):
            os.remove(self.file_path)
