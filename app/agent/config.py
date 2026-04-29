from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class MiniRAGConfig:
    working_dir: str = "./minirag_lang_data"

    chunk_size: int = 1200
    chunk_overlap: int = 100
    top_k: int = 40
    chunk_top_k: int = 20
    max_tokens: int = 30000
    max_gleaning: int = 1

    llm_binding: str = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_timeout: int = 180

    embedding_binding: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_base_url: str = ""
    embedding_api_key: str = ""
    embedding_dim: int = 1536
    embedding_max_token_size: int = 8192
    embedding_timeout: int = 30

    rerank_binding: str = ""
    rerank_model: str = ""
    rerank_base_url: str = ""
    rerank_api_key: str = ""
    enable_rerank: bool = False

    @classmethod
    def from_env(cls) -> MiniRAGConfig:
        return cls(
            working_dir=os.getenv("MINIRAG_WORKING_DIR", "./minirag_lang_data"),
            chunk_size=int(os.getenv("MINIRAG_CHUNK_SIZE", "1200")),
            chunk_overlap=int(os.getenv("MINIRAG_CHUNK_OVERLAP", "100")),
            top_k=int(os.getenv("MINIRAG_TOP_K", "40")),
            chunk_top_k=int(os.getenv("MINIRAG_CHUNK_TOP_K", "20")),
            max_tokens=int(os.getenv("MINIRAG_MAX_TOKENS", "30000")),
            llm_binding=os.getenv("MINIRAG_LLM_BINDING", "openai"),
            llm_model=os.getenv("MINIRAG_LLM_MODEL", "gpt-4o-mini"),
            llm_base_url=os.getenv("MINIRAG_LLM_BASE_URL", ""),
            llm_api_key=os.getenv("MINIRAG_LLM_API_KEY", ""),
            embedding_binding=os.getenv("MINIRAG_EMBEDDING_BINDING", "openai"),
            embedding_model=os.getenv("MINIRAG_EMBEDDING_MODEL", "text-embedding-3-small"),
            embedding_dim=int(os.getenv("MINIRAG_EMBEDDING_DIM", "1536")),
            rerank_binding=os.getenv("MINIRAG_RERANK_BINDING", ""),
            rerank_model=os.getenv("MINIRAG_RERANK_MODEL", ""),
            rerank_base_url=os.getenv("MINIRAG_RERANK_BASE_URL", ""),
            rerank_api_key=os.getenv("MINIRAG_RERANK_API_KEY", ""),
        )


@dataclass
class QueryParam:
    mode: Literal["local", "global", "hybrid", "naive"] = "hybrid"
    top_k: int = 40
    chunk_top_k: int = 20
    max_tokens: int = 30000
    stream: bool = False
    enable_rerank: bool = True
    response_type: str = "Multiple Paragraphs"
    hl_keywords: list[str] = field(default_factory=list)
    ll_keywords: list[str] = field(default_factory=list)
    conversation_history: list[dict] = field(default_factory=list)
    user_prompt: str | None = None
    retrieve_only: bool = False
