from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any


logger = logging.getLogger("minirag_lang")


def compute_mdhash_id(content: str, prefix: str = "") -> str:
    return prefix + hashlib.md5(content.encode("utf-8")).hexdigest()


def sanitize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def load_json(path: str) -> dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str, data: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def split_string_by_multi_markers(text: str, markers: list[str]) -> list[str]:
    import re
    pattern = "|".join(re.escape(m) for m in markers)
    parts = re.split(pattern, text)
    return [p.strip() for p in parts if p.strip()]
