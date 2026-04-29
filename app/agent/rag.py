from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .config import MiniRAGConfig, QueryParam
from .constants import DEFAULT_COSINE_THRESHOLD
from .utils import compute_mdhash_id, sanitize_text, logger

from .storage.kv_store import JsonKVStore
from .storage.graph_store import GraphStore
from .storage.vector_store import FAISSStore
from .llm.factory import create_llm, create_embeddings
from .graph import configure_graphs, get_insert_graph, get_query_graph


@dataclass
class QueryResult:
    content: str = ""
    raw_data: dict | None = None


@dataclass
class MiniRAG:
    config: MiniRAGConfig = field(default_factory=MiniRAGConfig)

    llm: Any = field(init=False, repr=False)
    embeddings: Any = field(init=False, repr=False)

    full_docs: JsonKVStore = field(init=False, repr=False)
    text_chunks: JsonKVStore = field(init=False, repr=False)
    doc_status: JsonKVStore = field(init=False, repr=False)
    graph: GraphStore = field(init=False, repr=False)
    entities_vdb: FAISSStore = field(init=False, repr=False)
    relationships_vdb: FAISSStore = field(init=False, repr=False)
    chunks_vdb: FAISSStore = field(init=False, repr=False)

    _initialized: bool = field(default=False, repr=False)

    async def initialize(self) -> None:
        if self._initialized:
            return

        wd = self.config.working_dir
        edim = self.config.embedding_dim
        ct = DEFAULT_COSINE_THRESHOLD

        self.full_docs = JsonKVStore("full_docs", wd)
        self.text_chunks = JsonKVStore("text_chunks", wd)
        self.doc_status = JsonKVStore("doc_status", wd)
        self.graph = GraphStore("graph", wd)
        self.entities_vdb = FAISSStore("entities_vdb", wd, edim, ct)
        self.relationships_vdb = FAISSStore("relationships_vdb", wd, edim, ct)
        self.chunks_vdb = FAISSStore("chunks_vdb", wd, edim, ct)

        for s in [self.full_docs, self.text_chunks, self.doc_status,
                  self.graph, self.entities_vdb, self.relationships_vdb, self.chunks_vdb]:
            await s.initialize()

        self.llm = create_llm(self.config)
        self.embeddings = create_embeddings(self.config)

        self.entities_vdb._embeddings = self.embeddings
        self.relationships_vdb._embeddings = self.embeddings
        self.chunks_vdb._embeddings = self.embeddings

        configure_graphs({
            "llm": self.llm,
            "embeddings": self.embeddings,
            "full_docs": self.full_docs,
            "text_chunks": self.text_chunks,
            "doc_status": self.doc_status,
            "graph": self.graph,
            "entities_vdb": self.entities_vdb,
            "relationships_vdb": self.relationships_vdb,
            "chunks_vdb": self.chunks_vdb,
        })

        self._initialized = True
        logger.info("MiniRAG-Lang initialized")

    async def finalize(self) -> None:
        for s in [self.full_docs, self.text_chunks, self.doc_status,
                  self.graph, self.entities_vdb, self.relationships_vdb, self.chunks_vdb]:
            await s.finalize()

    async def insert(self, text: str | list[str]) -> str:
        if isinstance(text, str):
            text = [text]

        insert_graph = get_insert_graph()

        for t in text:
            doc_id = compute_mdhash_id(t, prefix="doc-")

            existing = await self.doc_status.get_by_id(doc_id)
            if existing and existing.get("status") in ("processed", "processing"):
                logger.info(f"Document already processed: {doc_id}")
                continue

            await insert_graph.ainvoke({
                "raw_text": t,
                "doc_id": doc_id,
                "exists": False,
                "chunks": [],
                "chunk_dict": {},
                "entities": {},
                "relationships": [],
                "error": None,
            })

        return "ok"

    async def query(self, question: str, param: QueryParam | None = None) -> QueryResult:
        if param is None:
            param = QueryParam()

        query_graph = get_query_graph()

        result = await query_graph.ainvoke({
            "question": question,
            "param": {
                "mode": param.mode,
                "top_k": param.top_k,
                "chunk_top_k": param.chunk_top_k,
                "max_tokens": param.max_tokens,
                "stream": param.stream,
                "enable_rerank": param.enable_rerank,
                "response_type": param.response_type,
                "hl_keywords": param.hl_keywords,
                "ll_keywords": param.ll_keywords,
                "conversation_history": param.conversation_history,
                "user_prompt": param.user_prompt,
            },
            "hl_keywords": [],
            "ll_keywords": [],
            "local_entities": [],
            "local_relations": [],
            "global_entities": [],
            "global_relations": [],
            "vector_chunks": [],
            "context": "",
            "raw_data": {},
            "answer": "",
        })

        if param.retrieve_only:
            return QueryResult(
                content=result.get("context", ""),
                raw_data=result.get("raw_data"),
            )

        return QueryResult(
            content=result.get("answer", ""),
            raw_data=result.get("raw_data"),
        )
