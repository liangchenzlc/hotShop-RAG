from __future__ import annotations

import json
import os
from typing import Any, Iterable, List, Optional

import faiss
import numpy as np
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore
from langchain_core.embeddings import Embeddings

from ..utils import logger


class FAISSStore(VectorStore):

    def __init__(
        self,
        namespace: str,
        working_dir: str,
        embedding_dim: int = 1536,
        cosine_threshold: float = 0.4,
        embeddings: Embeddings | None = None,
    ):
        self.namespace = namespace
        self.working_dir = working_dir
        self.embedding_dim = embedding_dim
        self.cosine_threshold = cosine_threshold
        self.meta_file = os.path.join(working_dir, f"{namespace}_meta.json")
        self.index_file = os.path.join(working_dir, f"{namespace}.faiss")
        self._embeddings = embeddings

        self._index: faiss.Index | None = None
        self._id_list: list[str] = []
        self._meta: dict[str, dict[str, Any]] = {}

    @property
    def embeddings(self) -> Embeddings | None:
        return self._embeddings

    def _build_index(self, embeddings_2d: np.ndarray) -> None:
        dim = embeddings_2d.shape[1]
        self._index = faiss.IndexFlatIP(dim)
        faiss.normalize_L2(embeddings_2d)
        self._index.add(embeddings_2d)

    async def initialize(self) -> None:
        os.makedirs(self.working_dir, exist_ok=True)
        if os.path.exists(self.meta_file):
            with open(self.meta_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._id_list = data.get("ids", [])
                self._meta = data.get("meta", {})
            if os.path.exists(self.index_file):
                self._index = faiss.read_index(self.index_file)
            logger.debug(f"FAISSStore loaded: {self.meta_file} ({len(self._id_list)} vectors)")

    async def finalize(self) -> None:
        self._persist()

    def _persist(self) -> None:
        os.makedirs(self.working_dir, exist_ok=True)
        with open(self.meta_file, "w", encoding="utf-8") as f:
            json.dump({"ids": self._id_list, "meta": self._meta}, f, ensure_ascii=False, indent=2)
        if self._index is not None:
            faiss.write_index(self._index, self.index_file)

    async def add_texts(
        self,
        texts: Iterable[str],
        metadatas: list[dict] | None = None,
        *,
        ids: list[str] | None = None,
        embeddings: list[list[float]] | None = None,
        **kwargs: Any,
    ) -> list[str]:
        text_list = list(texts)
        if ids is None:
            import hashlib
            ids = [hashlib.md5(t.encode()).hexdigest() for t in text_list]

        for i, tid in enumerate(ids):
            meta = metadatas[i] if metadatas and i < len(metadatas) else {}
            meta["text"] = text_list[i]
            self._meta[tid] = meta

        for tid in ids:
            if tid not in self._id_list:
                self._id_list.append(tid)

        all_embs = []
        for tid in self._id_list:
            idx_in_batch = ids.index(tid) if tid in ids else -1
            if idx_in_batch >= 0 and embeddings is not None:
                all_embs.append(embeddings[idx_in_batch])
            else:
                all_embs.append(self._meta[tid].get("__embedding__", [0.0] * self.embedding_dim))

        emb_array = np.array(all_embs, dtype=np.float32)
        if emb_array.shape[0] > 0:
            self._build_index(emb_array)
        self._persist()

        return ids

    def similarity_search(
        self, query: str, k: int = 4, **kwargs: Any
    ) -> list[Document]:
        if self._embeddings is None:
            raise ValueError("Embeddings not set on FAISSStore, use similarity_search_by_vector instead")
        emb = self._embeddings.embed_query(query)
        return self.similarity_search_by_vector(emb, k, **kwargs)

    def similarity_search_by_vector(
        self, embedding: list[float], k: int = 40, **kwargs: Any
    ) -> list[Document]:
        threshold = kwargs.get("threshold", self.cosine_threshold)
        if self._index is None or self._index.ntotal == 0:
            return []

        query_vec = np.array([embedding], dtype=np.float32)
        faiss.normalize_L2(query_vec)
        distances, indices = self._index.search(query_vec, min(k, self._index.ntotal))

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self._id_list):
                continue
            if dist < threshold:
                continue
            doc_id = self._id_list[idx]
            meta = dict(self._meta.get(doc_id, {}))
            text = meta.pop("text", "")
            doc = Document(page_content=text, metadata=meta)
            doc.metadata["id"] = doc_id
            doc.metadata["distance"] = float(dist)
            results.append(doc)

        return results

    @classmethod
    def from_texts(
        cls,
        texts: list[str],
        embedding: Embeddings,
        metadatas: list[dict] | None = None,
        **kwargs: Any,
    ) -> FAISSStore:
        return cls.__new__(cls)

    async def delete(self, ids: list[str] | None = None, **kwargs: Any) -> bool | None:
        if ids is None:
            self._id_list.clear()
            self._meta.clear()
            self._index = None
            if os.path.exists(self.index_file):
                os.remove(self.index_file)
            if os.path.exists(self.meta_file):
                os.remove(self.meta_file)
            return True

        for tid in ids:
            self._meta.pop(tid, None)
            if tid in self._id_list:
                self._id_list.remove(tid)

        if self._id_list:
            embs = [
                self._meta[tid].get("__embedding__", [0.0] * self.embedding_dim)
                for tid in self._id_list
            ]
            emb_array = np.array(embs, dtype=np.float32)
            if emb_array.shape[0] > 0:
                self._build_index(emb_array)
        else:
            self._index = None

        self._persist()
        return True
