from __future__ import annotations

from typing import Any

from ..utils import logger


async def apply_rerank(
    query: str,
    docs: list[dict],
    rerank_func: callable | None,
    top_n: int | None = None,
) -> list[dict[str, Any]]:
    if not rerank_func or not docs:
        return docs

    try:
        texts = [d.get("content") or d.get("text") or str(d) for d in docs]
        results = await rerank_func(query=query, documents=texts, top_n=top_n)

        if results and len(results) > 0 and isinstance(results[0], dict) and "index" in results[0]:
            reranked = []
            for r in results:
                idx = r["index"]
                score = r["relevance_score"]
                if 0 <= idx < len(docs):
                    doc = dict(docs[idx])
                    doc["rerank_score"] = score
                    reranked.append(doc)
            return reranked

        return docs
    except Exception as e:
        logger.warning(f"Rerank failed: {e}")
        return docs
