from __future__ import annotations

from ..state import QueryState
from ..retrieval.context_builder import build_context


async def build_context_node(state: QueryState) -> dict:
    ctx = _get_context()
    rerank_func = None

    context, raw_data = await build_context(
        query=state["question"],
        entities=state.get("merged_entities", []) + state.get("local_entities", []) + state.get("global_entities", []),
        relations=state.get("merged_relations", []) + state.get("local_relations", []) + state.get("global_relations", []),
        vector_chunks=state.get("vector_chunks", []),
        text_chunks_store=ctx["text_chunks"],
        enable_rerank=state["param"].get("enable_rerank", True) and rerank_func is not None,
        rerank_func=rerank_func,
        chunk_top_k=state["param"].get("chunk_top_k") or state["param"].get("top_k", 20),
    )

    return {"context": context, "raw_data": raw_data}


def _get_context():
    import app.agent.graph as g
    return g._STORAGE_CTX
