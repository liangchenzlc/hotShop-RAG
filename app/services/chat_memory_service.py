import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import ChatMessage, ChatSession

logger = logging.getLogger(__name__)


class ChatMemoryService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_session(self, session_id: int | None) -> ChatSession:
        if session_id is not None:
            session = self.db.get(ChatSession, session_id)
            if session:
                return session
        session = ChatSession()
        self.db.add(session)
        self.db.commit()
        return session

    def list_sessions(self) -> list[dict]:
        rows = (
            self.db.query(
                ChatSession.id,
                ChatSession.title,
                ChatSession.created_at,
                ChatSession.updated_at,
            )
            .order_by(ChatSession.updated_at.desc())
            .all()
        )
        result = []
        for r in rows:
            count = self.db.query(ChatMessage).filter(
                ChatMessage.session_id == r.id
            ).count()
            last_msg = (
                self.db.query(ChatMessage.content)
                .filter(ChatMessage.session_id == r.id, ChatMessage.role == "user")
                .order_by(ChatMessage.created_at.desc())
                .first()
            )
            result.append({
                "id": r.id,
                "title": r.title,
                "message_count": count,
                "last_preview": last_msg[0][:60] if last_msg else None,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
            })
        return result

    def delete_session(self, session_id: int) -> bool:
        session = self.db.get(ChatSession, session_id)
        if not session:
            return False
        self.db.delete(session)
        self.db.commit()
        return True

    def get_messages(self, session_id: int) -> list[ChatMessage]:
        return (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )

    def add_message(
        self,
        session_id: int,
        role: str,
        content: str,
        citations: dict | None = None,
        intent: str | None = None,
    ) -> ChatMessage:
        msg = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            citations=citations,
            intent=intent,
        )
        self.db.add(msg)

        session = self.db.get(ChatSession, session_id)
        if session:
            session.updated_at = datetime.utcnow()
            if role == "user" and session.title == "新对话":
                session.title = content[:30]

        self.db.commit()
        return msg

    @staticmethod
    def build_history_text(messages: list[ChatMessage]) -> str:
        lines = []
        for m in messages:
            prefix = "user" if m.role == "user" else "assistant"
            lines.append(f"{prefix}: {m.content}")
        return "\n".join(lines)
