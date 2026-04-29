from __future__ import annotations

import json_repair
from typing import Any

from ..utils import logger
from ..constants import GRAPH_FIELD_SEP, DEFAULT_ENTITY_TYPES, DEFAULT_MAX_GLEANING


EXTRACT_SYSTEM_PROMPT = """You are a knowledge graph extractor. Identify all entities and their relationships from the given text.

Entity types: {entity_types}

For each entity:
- name: entity name (use the exact name from text)
- type: one of the entity types
- description: a concise description

For each relationship:
- src: source entity name
- tgt: target entity name
- description: relationship description
- keywords: comma-separated keywords describing the relationship
- weight: a number 1-10 indicating relationship strength

Output as JSON:
{{
  "entities": [{{"name": "...", "type": "...", "description": "..."}}],
  "relationships": [{{"src": "...", "tgt": "...", "description": "...", "keywords": "...", "weight": 5}}]
}}"""

EXTRACT_USER_PROMPT = """Extract entities and relationships from the following text:

{text}"""

GLEAN_PROMPT = """Look for missing entities in the previous text. Focus on entities you might have missed.
Previous entities: {existing_entities}
Text: {text}
Output any new entities and their relationships in the same JSON format."""


async def extract_entities(
    llm_invoke: callable,
    chunks: dict[str, dict[str, Any]],
    entity_types: list[str] | None = None,
    max_gleaning: int = DEFAULT_MAX_GLEANING,
) -> dict[str, dict[str, Any]]:
    if entity_types is None:
        entity_types = DEFAULT_ENTITY_TYPES

    system_prompt = EXTRACT_SYSTEM_PROMPT.format(entity_types=", ".join(entity_types))

    all_entities: dict[str, dict] = {}
    all_relationships: list[dict] = []

    for chunk_key, chunk_data in chunks.items():
        chunk_text = chunk_data["content"]
        user_prompt = EXTRACT_USER_PROMPT.format(text=chunk_text)

        result = await llm_invoke(user_prompt, system_prompt)
        parsed = _parse_extraction_result(result)

        _merge_entities(all_entities, parsed.get("entities", []), chunk_key)
        _merge_relationships(all_relationships, parsed.get("relationships", []), chunk_key)

        for glean_round in range(max_gleaning):
            existing_names = list(all_entities.keys())
            glean_prompt = GLEAN_PROMPT.format(
                existing_entities=", ".join(existing_names),
                text=chunk_text,
            )
            glean_result = await llm_invoke(glean_prompt, system_prompt)
            glean_parsed = _parse_extraction_result(glean_result)
            if not glean_parsed.get("entities") and not glean_parsed.get("relationships"):
                break
            _merge_entities(all_entities, glean_parsed.get("entities", []), chunk_key)
            _merge_relationships(all_relationships, glean_parsed.get("relationships", []), chunk_key)

    return {
        "entities": all_entities,
        "relationships": _deduplicate_relationships(all_relationships),
    }


def _parse_extraction_result(result: str) -> dict:
    try:
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1]
            result = result.rsplit("```", 1)[0]
        data = json_repair.loads(result)
        if isinstance(data, dict):
            return data
        return {"entities": [], "relationships": []}
    except Exception:
        return {"entities": [], "relationships": []}


def _merge_entities(
    storage: dict[str, dict],
    entities: list[dict],
    chunk_key: str,
) -> None:
    for e in entities:
        name = e.get("name", "").strip()
        if not name:
            continue
        if name in storage:
            existing = storage[name]
            descs = [existing.get("description", "")]
            if e.get("description") and e["description"] not in descs:
                descs.append(e["description"])
            existing["description"] = "; ".join(d for d in descs if d)
            existing["source_id"] = existing.get("source_id", "") + GRAPH_FIELD_SEP + chunk_key
        else:
            storage[name] = {
                "entity_name": name,
                "entity_type": e.get("type", "unknown"),
                "description": e.get("description", ""),
                "source_id": chunk_key,
            }


def _merge_relationships(
    storage: list[dict],
    relationships: list[dict],
    chunk_key: str,
) -> None:
    for r in relationships:
        src = r.get("src", "").strip()
        tgt = r.get("tgt", "").strip()
        if not src or not tgt or src == tgt:
            continue
        storage.append({
            "src_id": src,
            "tgt_id": tgt,
            "description": r.get("description", ""),
            "keywords": r.get("keywords", ""),
            "weight": r.get("weight", 1.0),
            "source_id": chunk_key,
        })


def _deduplicate_relationships(relationships: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for r in relationships:
        key = tuple(sorted([r["src_id"], r["tgt_id"]]))
        if key not in seen:
            seen.add(key)
            result.append(r)
    return result
