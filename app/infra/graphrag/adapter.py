import asyncio
import json
import logging
from typing import Any

from app.agent import MiniRAG, MiniRAGConfig, QueryParam
from app.agent.utils import compute_mdhash_id

logger = logging.getLogger(__name__)


class MiniRAGAdapter:
    """Singleton wrapper around MiniRAG, bridging async MiniRAG to sync hotSpot-RAG."""

    _instance: "MiniRAGAdapter | None" = None
    _rag: MiniRAG | None = None
    _config: MiniRAGConfig | None = None

    def __new__(cls, config: MiniRAGConfig | None = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._config = config
            cls._rag = MiniRAG(config=config) if config else None
        return cls._instance

    @classmethod
    def initialize(cls, config: MiniRAGConfig) -> None:
        if cls._instance is None or cls._config != config:
            cls._instance = cls.__new__(cls)
            cls._config = config
            cls._rag = MiniRAG(config=config)
        asyncio.run(cls._rag.initialize())
        logger.info("MiniRAGAdapter initialized, working_dir=%s", config.working_dir)

    @classmethod
    def _ensure(cls):
        if cls._rag is None:
            raise RuntimeError(
                "MiniRAGAdapter not initialized. Call MiniRAGAdapter.initialize() first."
            )

    @classmethod
    def insert(cls, text: str) -> str:
        cls._ensure()
        return asyncio.run(cls._rag.insert(text))

    @classmethod
    def query(cls, question: str, param: QueryParam | None = None) -> dict:
        cls._ensure()
        result = asyncio.run(cls._rag.query(question, param))
        return {
            "answer": result.content,
            "raw_data": result.raw_data or {},
        }

    @classmethod
    def delete_document(cls, doc_id: str) -> bool:
        cls._ensure()
        asyncio.run(_delete_document_async(cls._rag, doc_id))
        return True

    @classmethod
    def finalize(cls) -> None:
        if cls._rag is not None:
            asyncio.run(cls._rag.finalize())

    @classmethod
    def insert_from_articles(
        cls, article_id: int, content: str, title: str = "", summary: str = ""
    ) -> str:
        text = content or f"{title}\n\n{summary}".strip()
        if not text:
            return ""
        doc_id = compute_mdhash_id(text, prefix="doc-")
        cls.insert(text)
        return doc_id


async def _delete_document_async(rag: MiniRAG, doc_id: str) -> None:
    """Remove a document and all derived data from all MiniRAG stores."""
    chunk_ids_to_delete: list[str] = []
    for key in rag.text_chunks.yield_keys():
        raw = rag.text_chunks.mget([key])[0]
        if raw:
            try:
                data = json.loads(raw)
                if data.get("full_doc_id") == doc_id:
                    chunk_ids_to_delete.append(key)
            except Exception:
                continue

    entity_ids_to_delete: list[str] = []
    for eid, meta in rag.entities_vdb._meta.items():
        source = meta.get("source_id", "")
        if any(cid in source for cid in chunk_ids_to_delete):
            entity_ids_to_delete.append(eid)

    rel_ids_to_delete: list[str] = []
    for rid, meta in rag.relationships_vdb._meta.items():
        source = meta.get("source_id", "")
        if any(cid in source for cid in chunk_ids_to_delete):
            rel_ids_to_delete.append(rid)

    if chunk_ids_to_delete:
        await rag.chunks_vdb.delete(ids=chunk_ids_to_delete)
    if entity_ids_to_delete:
        await rag.entities_vdb.delete(ids=entity_ids_to_delete)
    if rel_ids_to_delete:
        await rag.relationships_vdb.delete(ids=rel_ids_to_delete)

    for eid in entity_ids_to_delete:
        await rag.graph.delete_node(eid)

    rag.text_chunks.mdelete(chunk_ids_to_delete)
    rag.full_docs.mdelete([doc_id])
    rag.doc_status.mdelete([doc_id])
    await rag.text_chunks.finalize()
    await rag.full_docs.finalize()
    await rag.doc_status.finalize()

    logger.info(
        "Deleted doc=%s: %d chunks, %d entities, %d relationships",
        doc_id,
        len(chunk_ids_to_delete),
        len(entity_ids_to_delete),
        len(rel_ids_to_delete),
    )
