from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.schemas import SearchRequest, SearchResponse
from app.services.retrieval_service import RetrievalService

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
def search(payload: SearchRequest, db: Session = Depends(get_db)) -> SearchResponse:
    service = RetrievalService(db)
    return SearchResponse(hits=service.search(payload.query, payload.top_k))
