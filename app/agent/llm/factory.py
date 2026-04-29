from __future__ import annotations

from ..config import MiniRAGConfig
from ..exceptions import LLMError


def create_llm(config: MiniRAGConfig):
    binding = config.llm_binding.lower()

    if binding == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=config.llm_model,
            api_key=config.llm_api_key,
            base_url=config.llm_base_url or None,
            temperature=0,
            timeout=config.llm_timeout,
        )

    elif binding == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=config.llm_model,
            base_url=config.llm_base_url or "http://localhost:11434",
            temperature=0,
            num_predict=config.llm_timeout * 1000,
        )

    else:
        raise LLMError(f"Unsupported LLM binding: {binding}")


def create_embeddings(config: MiniRAGConfig):
    binding = config.embedding_binding.lower()

    if binding == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=config.embedding_model,
            api_key=config.embedding_api_key,
            base_url=config.embedding_base_url or None,
            dimensions=config.embedding_dim,
            check_embedding_ctx_length=False,
        )

    elif binding == "ollama":
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(
            model=config.embedding_model,
            base_url=config.embedding_base_url or "http://localhost:11434",
        )

    else:
        raise LLMError(f"Unsupported embedding binding: {binding}")
