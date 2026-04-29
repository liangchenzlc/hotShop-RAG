from __future__ import annotations

from ..constants import GRAPH_FIELD_SEP
from ..utils import split_string_by_multi_markers


def pick_by_weighted_polling(
    entities_or_relations: list[dict],
    max_related_chunks: int,
    min_related_chunks: int = 1,
) -> list[str]:
    if not entities_or_relations:
        return []

    n = len(entities_or_relations)
    if n == 1:
        chunks = entities_or_relations[0].get("sorted_chunks", [])
        return chunks[:max_related_chunks]

    expected_counts = []
    for i in range(n):
        ratio = i / (n - 1) if n > 1 else 0
        expected = max_related_chunks - ratio * (max_related_chunks - min_related_chunks)
        expected_counts.append(int(round(expected)))

    selected_chunks = []
    used_counts = []

    for i, item in enumerate(entities_or_relations):
        item_chunks = item.get("sorted_chunks", [])
        actual = min(expected_counts[i], len(item_chunks))
        selected_chunks.extend(item_chunks[:actual])
        used_counts.append(actual)

    total_remaining = sum(
        expected_counts[i] - used_counts[i]
        for i in range(n)
        if expected_counts[i] > used_counts[i]
    )

    for _ in range(total_remaining):
        allocated = False
        for i, item in enumerate(entities_or_relations):
            item_chunks = item.get("sorted_chunks", [])
            if used_counts[i] < len(item_chunks):
                selected_chunks.append(item_chunks[used_counts[i]])
                used_counts[i] += 1
                allocated = True
                break
        if not allocated:
            break

    return selected_chunks


def collect_chunks_from_entities(
    entities: list[dict],
    max_related_chunks: int = 5,
) -> list[str]:
    entities_with_chunks = []
    for ent in entities:
        source_id = ent.get("source_id", "")
        if source_id:
            chunks = split_string_by_multi_markers(source_id, [GRAPH_FIELD_SEP])
            if chunks:
                entities_with_chunks.append({
                    "entity_name": ent.get("entity_name"),
                    "chunks": chunks,
                })

    for item in entities_with_chunks:
        item["sorted_chunks"] = item["chunks"]

    return pick_by_weighted_polling(entities_with_chunks, max_related_chunks)


def collect_chunks_from_relations(
    relations: list[dict],
    max_related_chunks: int = 5,
) -> list[str]:
    relations_with_chunks = []
    for rel in relations:
        source_id = rel.get("source_id", "")
        if source_id:
            chunks = split_string_by_multi_markers(source_id, [GRAPH_FIELD_SEP])
            if chunks:
                relations_with_chunks.append({
                    "src": rel.get("src_id"),
                    "tgt": rel.get("tgt_id"),
                    "chunks": chunks,
                })

    for item in relations_with_chunks:
        item["sorted_chunks"] = item["chunks"]

    return pick_by_weighted_polling(relations_with_chunks, max_related_chunks)
