from __future__ import annotations

from ..state import InsertState


async def embed_chunks(state: InsertState) -> dict:
    ctx = _get_context()
    texts = [c.page_content for c in state["chunks"]]
    ids = [c.id for c in state["chunks"]]

    embeddings = await _batch_embed(ctx["embeddings"], texts)

    metadatas = []
    for c in state["chunks"]:
        meta = dict(c.metadata)
        meta["full_doc_id"] = state["doc_id"]
        metadatas.append(meta)

    await ctx["chunks_vdb"].add_texts(
        texts=texts,
        metadatas=metadatas,
        ids=ids,
        embeddings=embeddings,
    )
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
