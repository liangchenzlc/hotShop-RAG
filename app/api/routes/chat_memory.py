from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models import ChatMessage
from app.db.session import get_db
from app.domain.schemas import (
    ChatMessageListResponse,
    ChatMessageResponse,
    ChatSessionListResponse,
    ChatSessionResponse,
)
from app.services.chat_memory_service import ChatMemoryService

router = APIRouter()


@router.get("/sessions", response_model=ChatSessionListResponse)
def list_sessions(db: Session = Depends(get_db)) -> ChatSessionListResponse:
    service = ChatMemoryService(db)
    return ChatSessionListResponse(items=service.list_sessions())


@router.post("/sessions", response_model=ChatSessionResponse)
def create_session(db: Session = Depends(get_db)) -> ChatSessionResponse:
    service = ChatMemoryService(db)
    session = service.get_or_create_session(None)
    return ChatSessionResponse(
        id=session.id,
        title=session.title,
        message_count=0,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
    )


@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db)) -> dict:
    service = ChatMemoryService(db)
    ok = service.delete_session(session_id)
    if not ok:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session not found")
    return {"ok": True}


@router.get("/sessions/{session_id}/messages", response_model=ChatMessageListResponse)
def list_messages(session_id: int, db: Session = Depends(get_db)) -> ChatMessageListResponse:
    service = ChatMemoryService(db)
    messages = service.get_messages(session_id)
    items = [
        ChatMessageResponse(
            id=m.id,
            role=m.role,
            content=m.content,
            citations=m.citations,
            intent=m.intent,
            created_at=m.created_at.isoformat(),
        )
        for m in messages
    ]
    return ChatMessageListResponse(items=items)
