from __future__ import annotations

from ..state import QueryState


async def merge_results(state: QueryState) -> dict:
    merged_entities = []
    seen_entities = set()
    local_e = state.get("local_entities", [])
    global_e = state.get("global_entities", [])
    max_e = max(len(local_e), len(global_e))

    for i in range(max_e):
        for e in ([local_e[i]] if i < len(local_e) else []):
            name = e.get("entity_name")
            if name and name not in seen_entities:
                seen_entities.add(name)
                merged_entities.append(e)
        for e in ([global_e[i]] if i < len(global_e) else []):
            name = e.get("entity_name")
            if name and name not in seen_entities:
                seen_entities.add(name)
                merged_entities.append(e)

    merged_relations = []
    seen_relations = set()
    local_r = state.get("local_relations", [])
    global_r = state.get("global_relations", [])
    max_r = max(len(local_r), len(global_r))

    for i in range(max_r):
        for r in ([local_r[i]] if i < len(local_r) else []):
            key = tuple(sorted([r.get("src_id", ""), r.get("tgt_id", "")]))
            if key not in seen_relations:
                seen_relations.add(key)
                merged_relations.append(r)
        for r in ([global_r[i]] if i < len(global_r) else []):
            key = tuple(sorted([r.get("src_id", ""), r.get("tgt_id", "")]))
            if key not in seen_relations:
                seen_relations.add(key)
                merged_relations.append(r)

    return {
        "merged_entities": merged_entities,
        "merged_relations": merged_relations,
    }
