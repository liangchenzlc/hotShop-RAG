from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.schemas import (
    KnowledgeArticleDetailResponse,
    KnowledgeArticleListResponse,
    KnowledgeBatchDeleteRequest,
    KnowledgeStatsResponse,
)
from app.services.knowledge_service import KnowledgeService

router = APIRouter()


@router.get("/stats", response_model=KnowledgeStatsResponse)
def get_knowledge_stats(db: Session = Depends(get_db)) -> KnowledgeStatsResponse:
    service = KnowledgeService(db)
    return KnowledgeStatsResponse(**service.stats())


@router.get("/articles", response_model=KnowledgeArticleListResponse)
def list_knowledge_articles(
    keyword: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    sort_by: str = Query(default="time", pattern="^(time|hot)$"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
) -> KnowledgeArticleListResponse:
    service = KnowledgeService(db)
    result = service.list_articles(
        keyword=keyword,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        order=order,
        page=page,
        page_size=page_size,
    )
    return KnowledgeArticleListResponse(**result)


@router.get("/articles/{article_id}", response_model=KnowledgeArticleDetailResponse)
def get_knowledge_article_detail(
    article_id: int, db: Session = Depends(get_db)
) -> KnowledgeArticleDetailResponse:
    service = KnowledgeService(db)
    return KnowledgeArticleDetailResponse(**service.article_detail(article_id))


@router.delete("/articles/{article_id}")
def delete_knowledge_article(article_id: int, db: Session = Depends(get_db)) -> dict:
    service = KnowledgeService(db)
    return service.delete_one(article_id)


@router.post("/articles/batch-delete")
def batch_delete_knowledge_articles(
    payload: KnowledgeBatchDeleteRequest, db: Session = Depends(get_db)
) -> dict:
    service = KnowledgeService(db)
    return service.batch_delete(payload.article_ids)
