from pydantic import BaseModel, Field


# ── Data Source Management ──

class DataSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    source_type: str = Field(min_length=1, max_length=32)
    is_active: bool = True
    config: dict = Field(default_factory=dict)
    keywords: list[str] = Field(default_factory=list)
    schedule_cron: str | None = None
    max_workers: int = Field(default=3, ge=1, le=10)


class DataSourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    is_active: bool | None = None
    config: dict | None = None
    keywords: list[str] | None = None
    schedule_cron: str | None = None
    max_workers: int | None = Field(default=None, ge=1, le=10)


class DataSourceResponse(BaseModel):
    id: int
    name: str
    source_type: str
    is_active: bool
    config: dict
    keywords: list
    schedule_cron: str | None = None
    max_workers: int
    last_run_at: str | None = None
    created_at: str
    updated_at: str


class DataSourceListResponse(BaseModel):
    total: int
    items: list[DataSourceResponse]


# ── Rebuild Index ──

class RebuildIndexRequest(BaseModel):
    article_ids: list[int] = Field(default_factory=list)


# ── Search ──

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class SearchHit(BaseModel):
    article_id: int
    title: str
    url: str
    score: float
    chunk_no: int
    snippet: str


class SearchResponse(BaseModel):
    hits: list[SearchHit]


# ── QA ──

class AskRequest(BaseModel):
    question: str
    top_k: int = 5
    use_retrieval: bool = False
    session_id: int | None = None


class Citation(BaseModel):
    article_id: int
    url: str
    title: str
    chunk_no: int


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    intent: str | None = None
    evaluation: dict | None = None
    session_id: int | None = None


# ── Knowledge Base ──

class KnowledgeStatsResponse(BaseModel):
    total_articles: int
    today_new: int
    last_sync_time: str | None = None
    avg_hot_score: float


class KnowledgeArticleItem(BaseModel):
    id: int
    title: str
    source_account: str
    url: str
    published_at: str | None = None
    hot_score: int


class KnowledgeArticleListResponse(BaseModel):
    items: list[KnowledgeArticleItem]
    total: int
    page: int
    page_size: int


class KnowledgeArticleDetailResponse(BaseModel):
    id: int
    title: str
    source_account: str
    url: str
    published_at: str | None = None
    hot_score: int
    summary: str | None = None
    content_markdown: str


class KnowledgeBatchDeleteRequest(BaseModel):
    article_ids: list[int] = Field(default_factory=list)


# ── Chat Memory ──

class ChatSessionResponse(BaseModel):
    id: int
    title: str
    message_count: int
    last_preview: str | None = None
    created_at: str
    updated_at: str


class ChatSessionListResponse(BaseModel):
    items: list[ChatSessionResponse]


class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    citations: dict | None = None
    intent: str | None = None
    created_at: str


class ChatMessageListResponse(BaseModel):
    items: list[ChatMessageResponse]
