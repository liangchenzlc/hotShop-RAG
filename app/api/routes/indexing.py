from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.schemas import RebuildIndexRequest
from app.services.indexing_service import IndexingService

router = APIRouter()


@router.post("/rebuild")
def rebuild_index(payload: RebuildIndexRequest, db: Session = Depends(get_db)) -> dict:
    service = IndexingService(db)
    return service.rebuild(article_ids=payload.article_ids or None)
