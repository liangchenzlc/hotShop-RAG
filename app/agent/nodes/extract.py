from __future__ import annotations

from ..state import InsertState
from ..retrieval.extractor import extract_entities as _extract_entities
from ..utils import compute_mdhash_id


async def extract_entities_node(state: InsertState) -> dict:
    ctx = _get_context()

    async def llm_call(prompt: str, system: str | None = None) -> str:
        messages = []
        if system:
            messages.append(("system", system))
        messages.append(("human", prompt))
        result = await ctx["llm"].ainvoke(messages)
        return result.content

    result = await _extract_entities(
        llm_invoke=llm_call,
        chunks=state["chunk_dict"],
    )
    return {"entities": result["entities"], "relationships": result["relationships"]}


async def store_chunks(state: InsertState) -> dict:
    ctx = _get_context()
    await ctx["text_chunks"].upsert(state["chunk_dict"])
    await ctx["doc_status"].upsert({
        state["doc_id"]: {"status": "processing", "chunks_count": len(state["chunks"])}
    })
    return {}


async def store_entities(state: InsertState) -> dict:
    ctx = _get_context()
    entities = state.get("entities", {})
    if not entities:
        return {}

    texts = [e["entity_name"] for e in entities.values()]
    ids = list(entities.keys())

    embeddings = await _batch_embed(ctx["embeddings"], texts)

    metadatas = list(entities.values())
    await ctx["entities_vdb"].add_texts(
        texts=texts,
        metadatas=metadatas,
        ids=ids,
        embeddings=embeddings,
    )

    for name, data in entities.items():
        await ctx["graph"].upsert_node(name, data)

    return {}


async def store_relationships(state: InsertState) -> dict:
    ctx = _get_context()
    relationships = state.get("relationships", [])
    if not relationships:
        return {}

    texts = [f"{r['src_id']} {r['tgt_id']} {r.get('description', '')}" for r in relationships]
    embeddings = await _batch_embed(ctx["embeddings"], texts)

    metadatas = list(relationships)
    ids = [compute_mdhash_id(f"{r['src_id']}-{r['tgt_id']}", prefix="rel-") for r in relationships]

    await ctx["relationships_vdb"].add_texts(
        texts=texts,
        metadatas=metadatas,
        ids=ids,
        embeddings=embeddings,
    )

    for r in relationships:
        await ctx["graph"].upsert_edge(r["src_id"], r["tgt_id"], r)

    return {}


async def mark_completed(state: InsertState) -> dict:
    ctx = _get_context()
    await ctx["doc_status"].upsert({state["doc_id"]: {"status": "processed"}})
    return {}


async def _batch_embed(embeddings, texts: list[str], batch_size: int = 10) -> list[list[float]]:
    results = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        chunk = await embeddings.aembed_documents(batch)
        results.extend(chunk)
    return results


def _get_context():
    import app.agent.graph as g
    return g._STORAGE_CTX
