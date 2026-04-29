import logging
from typing import Any

from app.agent import QueryParam

from app.infra.graphrag.adapter import MiniRAGAdapter

logger = logging.getLogger(__name__)


class MiniRAGStreamer:
    """Handles streaming for the MiniRAG-backed QA pipeline.

    Runs MiniRAG in retrieve-only mode (keywords extraction + search +
    context building, skipping answer generation), then returns the
    assembled context for downstream streaming generation.
    """

    @staticmethod
    def retrieve_context(question: str, top_k: int = 20, mode: str = "hybrid") -> dict:
        param = QueryParam(
            mode=mode,
            top_k=top_k + 20,
            chunk_top_k=top_k,
            retrieve_only=True,
        )
        result = MiniRAGAdapter.query(question, param)
        return {
            "context": result.get("answer", ""),
            "raw_data": result.get("raw_data", {}),
        }

    @staticmethod
    def extract_citations(raw_data: dict, top_k: int = 10) -> list[dict]:
        citations: list[dict] = []
        for i, chunk in enumerate(raw_data.get("chunks", [])[:top_k]):
            citations.append({
                "chunk_id": chunk.get("chunk_id", ""),
                "snippet": chunk.get("content", "")[:200],
                "score": float(chunk.get("distance", 0.0)),
                "source_type": chunk.get("source_type", "vector"),
            })
        return citations
