from __future__ import annotations

from ..state import QueryState
from ..utils import logger


async def local_search_node(state: QueryState) -> dict:
    ctx = _get_context()
    ll_keywords = ", ".join(state["ll_keywords"])
    if not ll_keywords:
        return {"local_entities": [], "local_relations": []}

    ll_emb = await ctx["embeddings"].aembed_query(ll_keywords) if ll_keywords else None
    top_k = state["param"].get("top_k", 40)

    entity_docs = ctx["entities_vdb"].similarity_search_by_vector(ll_emb, k=top_k) if ll_emb else []

    entity_names = [d.metadata.get("entity_name") or d.id for d in entity_docs]
    nodes = await ctx["graph"].get_nodes_batch(entity_names)

    node_datas = []
    for name in entity_names:
        nd = nodes.get(name)
        if nd:
            node_datas.append({"entity_name": name, **nd})

    edges = []
    all_graph_edges = await ctx["graph"].get_all_edges()
    for edge in all_graph_edges:
        if edge["src"] in entity_names or edge["tgt"] in entity_names:
            edges.append(edge)

    return {"local_entities": node_datas, "local_relations": edges}


async def global_search_node(state: QueryState) -> dict:
    ctx = _get_context()
    hl_keywords = ", ".join(state["hl_keywords"])
    if not hl_keywords:
        return {"global_entities": [], "global_relations": []}

    hl_emb = await ctx["embeddings"].aembed_query(hl_keywords) if hl_keywords else None
    top_k = state["param"].get("top_k", 40)

    rel_docs = ctx["relationships_vdb"].similarity_search_by_vector(hl_emb, k=top_k) if hl_emb else []

    edge_datas = []
    for d in rel_docs:
        edge_datas.append({
            "src_id": d.metadata.get("src_id", ""),
            "tgt_id": d.metadata.get("tgt_id", ""),
            **d.metadata,
        })

    entity_names = []
    seen = set()
    for e in edge_datas:
        for name in [e.get("src_id", ""), e.get("tgt_id", "")]:
            if name and name not in seen:
                entity_names.append(name)
                seen.add(name)

    nodes = await ctx["graph"].get_nodes_batch(entity_names)
    node_datas = [{"entity_name": n, **nd} for n, nd in nodes.items() if nd]

    return {"global_entities": node_datas, "global_relations": edge_datas}


async def naive_search_node(state: QueryState) -> dict:
    ctx = _get_context()
    q_emb = await ctx["embeddings"].aembed_query(state["question"])
    top_k = state["param"].get("chunk_top_k") or state["param"].get("top_k", 40)

    docs = ctx["chunks_vdb"].similarity_search_by_vector(q_emb, k=top_k)

    chunks = []
    for d in docs:
        chunks.append({
            "content": d.page_content,
            "chunk_id": d.id,
            "source_type": "vector",
            **d.metadata,
        })

    return {"vector_chunks": chunks}


def _get_context():
    import app.agent.graph as g
    return g._STORAGE_CTX
