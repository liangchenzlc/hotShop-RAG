from __future__ import annotations

from typing import Any

from .chunk_picker import collect_chunks_from_entities, collect_chunks_from_relations
from ..utils import logger


async def build_context(
    query: str,
    entities: list[dict],
    relations: list[dict],
    vector_chunks: list[dict],
    text_chunks_store: Any,
    enable_rerank: bool = True,
    rerank_func: callable | None = None,
    chunk_top_k: int = 20,
) -> tuple[str, dict]:
    entity_chunk_ids = collect_chunks_from_entities(entities, max_related_chunks=5)
    relation_chunk_ids = collect_chunks_from_relations(relations, max_related_chunks=5)

    all_chunks_raw = list(vector_chunks)
    seen_ids = set()
    for chunk in vector_chunks:
        cid = chunk.get("chunk_id") or chunk.get("id")
        if cid:
            seen_ids.add(cid)

    if entity_chunk_ids:
        for chunk_id in entity_chunk_ids:
            if chunk_id not in seen_ids:
                raw = text_chunks_store.mget([chunk_id])[0]
                if raw:
                    try:
                        import json
                        data = json.loads(raw)
                        if data.get("content"):
                            seen_ids.add(chunk_id)
                            all_chunks_raw.append({
                                "content": data["content"],
                                "chunk_id": chunk_id,
                                "source_type": "entity",
                            })
                    except Exception:
                        pass

    if relation_chunk_ids:
        for chunk_id in relation_chunk_ids:
            if chunk_id not in seen_ids:
                raw = text_chunks_store.mget([chunk_id])[0]
                if raw:
                    try:
                        import json
                        data = json.loads(raw)
                        if data.get("content"):
                            seen_ids.add(chunk_id)
                            all_chunks_raw.append({
                                "content": data["content"],
                                "chunk_id": chunk_id,
                                "source_type": "relation",
                            })
                    except Exception:
                        pass

    if enable_rerank and rerank_func and query and all_chunks_raw:
        from .reranker import apply_rerank
        all_chunks_raw = await apply_rerank(query, all_chunks_raw, rerank_func, top_n=chunk_top_k)

    if chunk_top_k and len(all_chunks_raw) > chunk_top_k:
        all_chunks_raw = all_chunks_raw[:chunk_top_k]

    entities_str = "\n".join(
        f"- {e.get('entity_name', '?')} ({e.get('entity_type', '?')}): {e.get('description', '')[:200]}"
        for e in entities
    )
    relations_str = "\n".join(
        f"- {r.get('src_id', '?')} → {r.get('tgt_id', '?')}: {r.get('description', '')[:200]}"
        for r in relations
    )
    chunks_str = "\n---\n".join(c.get("content", "") for c in all_chunks_raw)

    context_parts = []
    if entities_str:
        context_parts.append(f"## Related Entities\n{entities_str}")
    if relations_str:
        context_parts.append(f"## Related Relationships\n{relations_str}")
    if chunks_str:
        context_parts.append(f"## Related Text Chunks\n{chunks_str}")

    context = "\n\n".join(context_parts)
    raw_data = {"entities": entities, "relationships": relations, "chunks": all_chunks_raw}
    return context, raw_data
