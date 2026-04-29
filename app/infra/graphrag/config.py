from app.agent import MiniRAGConfig

from app.core.settings import Settings


def build_minirag_config(settings: Settings) -> MiniRAGConfig:
    return MiniRAGConfig(
        working_dir=settings.minirag_working_dir,
        chunk_size=settings.minirag_chunk_size,
        chunk_overlap=settings.minirag_chunk_overlap,
        top_k=settings.minirag_top_k,
        chunk_top_k=settings.minirag_chunk_top_k,
        max_tokens=settings.minirag_max_tokens,
        max_gleaning=settings.minirag_max_gleaning,
        llm_binding="openai",
        llm_model=settings.chat_model,
        llm_base_url=settings.openai_base_url,
        llm_api_key=settings.openai_api_key,
        embedding_binding="openai",
        embedding_model=settings.embedding_model,
        embedding_base_url=settings.openai_base_url,
        embedding_api_key=settings.openai_api_key,
        embedding_dim=settings.minirag_embedding_dim,
        enable_rerank=False,
    )
