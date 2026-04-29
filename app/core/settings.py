from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "HotSpotRAG"
    app_version: str = "0.1.0"
    app_env: str = "dev"

    mysql_url: str = Field(
        default="mysql+pymysql://root:root@127.0.0.1:3306/hotspot_rag?charset=utf8mb4"
    )
    redis_url: str = "redis://localhost:6379/0"

    minirag_working_dir: str = "./minirag_data"
    minirag_chunk_size: int = 1200
    minirag_chunk_overlap: int = 100
    minirag_top_k: int = 40
    minirag_chunk_top_k: int = 20
    minirag_max_tokens: int = 30000
    minirag_max_gleaning: int = 1
    minirag_embedding_dim: int = 1024

    embedding_provider: str = "aliyun_compatible"
    embedding_model: str = "text-embedding-v4"
    chat_provider: str = "aliyun_compatible"
    chat_model: str = "deepseek-v4-flash"
    openai_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    openai_api_key: str = "sk-6ee96c290a8c401283595520104bbe99"

    scheduler_enabled: bool = True
    search_enabled: bool = True
    scheduler_cron: str = "*/30 * * * *"

    fetch_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    bing_search_api_key: str = ""
    bing_search_endpoint: str = "https://api.bing.microsoft.com/v7.0/search"
    bing_search_market: str = "zh-CN"
    bing_search_page_size: int = 20
    workflow_max_retries: int = 2
    workflow_chat_score_threshold: int = 7
    workflow_qa_retrieval_score_threshold: int = 6
    workflow_qa_answer_score_threshold: int = 7
    workflow_intent_low_confidence_threshold: float = 0.65
    workflow_block_malicious_input: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
