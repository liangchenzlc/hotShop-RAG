import time
import logging
from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.db.models import Article, QALog
from app.domain.schemas import AskResponse, Citation
from app.infra.graphrag import MiniRAGAdapter, MiniRAGStreamer
from app.agent.chat_router import ChatRouter
from app.services.chat_memory_service import ChatMemoryService
from app.agent import QueryParam

logger = logging.getLogger(__name__)


class QAService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.memory = ChatMemoryService(db)
        self.chat = ChatRouter()

    def ask(
        self, question: str, top_k: int, use_retrieval: bool = False, session_id: int | None = None
    ) -> AskResponse:
        started = time.time()

        session = self.memory.get_or_create_session(session_id)
        messages = self.memory.get_messages(session.id)
        chat_history = ""
        if messages:
            turns = len(messages) // 2
            history_text = self.memory.build_history_text(messages)
            chat_history = (
                self.chat.compress_history(history_text) if turns > 4 else history_text
            )

        intent = "qa" if use_retrieval else "chat"
        answer = ""
        citations: list[Citation] = []

        if use_retrieval:
            param = QueryParam(
                mode="hybrid",
                top_k=top_k + 20,
                chunk_top_k=top_k,
            )
            result = MiniRAGAdapter.query(question, param)
            answer = result.get("answer", "")

            raw_data = result.get("raw_data", {})
            for chunk in raw_data.get("chunks", [])[:top_k]:
                doc_id = chunk.get("full_doc_id", "")
                article = None
                if doc_id:
                    article = (
                        self.db.query(Article)
                        .filter(Article.doc_id == doc_id)
                        .first()
                    )
                citations.append(
                    Citation(
                        article_id=article.id if article else 0,
                        url=article.url if article else "",
                        title=article.title if article else "",
                        chunk_no=int(chunk.get("chunk_order_index", 0)),
                    )
                )
        else:
            context = self.chat.build_chat_context(question)
            if chat_history:
                context = f"{context}\n\n对话历史：\n{chat_history}"
            answer = self.chat.chat_answer(question, context)

        latency_ms = int((time.time() - started) * 1000)

        self.memory.add_message(session.id, "user", question)
        self.memory.add_message(
            session.id,
            "assistant",
            answer,
            citations={"items": [c.model_dump() for c in citations]} if citations else None,
            intent=intent,
        )

        log = QALog(
            question=question,
            answer=answer,
            chat_provider=self.settings.chat_provider,
            chat_model=self.settings.chat_model,
            embedding_model=self.settings.embedding_model,
            topk=top_k,
            latency_ms=latency_ms,
            citations={"items": [c.model_dump() for c in citations]},
        )
        self.db.add(log)
        self.db.commit()

        return AskResponse(
            answer=answer,
            citations=citations,
            intent=intent,
            evaluation={"graphrag_mode": "hybrid"},
            session_id=session.id,
        )

    def ask_stream(
        self, question: str, top_k: int, use_retrieval: bool = False, session_id: int | None = None
    ) -> dict:
        try:
            cleaned_question = question.strip()
            if not cleaned_question:
                cleaned_question = "请帮我回答这个问题。"

            security_flags: list[str] = []
            if self.settings.workflow_block_malicious_input:
                security_flags = self.chat.detect_malicious_input(cleaned_question)
                if security_flags:
                    return {
                        "session_id": None,
                        "intent": "qa" if use_retrieval else "chat",
                        "citations": [],
                        "evaluation": {
                            "blocked": True,
                            "reason": "malicious_input",
                            "flags": security_flags,
                        },
                        "stream": iter(["检测到潜在恶意输入，已拒绝处理。请调整问题后重试。"]),
                    }

            session = self.memory.get_or_create_session(session_id)
            self.memory.add_message(session.id, "user", question)

            messages = self.memory.get_messages(session.id)
            chat_history = ""
            if len(messages) > 1:
                turns = len(messages) // 2
                history_text = self.memory.build_history_text(messages[:-1])
                chat_history = (
                    self.chat.compress_history(history_text) if turns > 4 else history_text
                )

            intent = "qa" if use_retrieval else "chat"
            context = ""
            citations: list[Citation] = []

            if use_retrieval:
                streamer = MiniRAGStreamer()
                result = streamer.retrieve_context(cleaned_question, top_k)
                context = result.get("context", "")

                raw_data = result.get("raw_data", {})
                for chunk in raw_data.get("chunks", [])[:top_k]:
                    doc_id = chunk.get("full_doc_id", "")
                    article = None
                    if doc_id:
                        article = (
                            self.db.query(Article)
                            .filter(Article.doc_id == doc_id)
                            .first()
                        )
                    citations.append(
                        Citation(
                            article_id=article.id if article else 0,
                            url=article.url if article else "",
                            title=article.title if article else "",
                            chunk_no=int(chunk.get("chunk_order_index", 0)),
                        )
                    )
            else:
                context = self.chat.build_chat_context(cleaned_question)

            if chat_history:
                context = f"{context}\n\n对话历史：\n{chat_history}"

            if use_retrieval:
                original_stream = self.chat.answer_stream(cleaned_question, context)
            else:
                original_stream = self.chat.chat_answer_stream(cleaned_question, context)

            def wrapped() -> Iterator[str]:
                parts = []
                for token in original_stream:
                    parts.append(token)
                    yield token
                answer = "".join(parts)
                self.memory.add_message(
                    session.id,
                    "assistant",
                    answer,
                    citations={"items": [c.model_dump() for c in citations]} if citations else None,
                    intent=intent,
                )

            return {
                "session_id": session.id,
                "intent": intent,
                "citations": citations,
                "evaluation": {"streaming": True, "mode": "graphrag_hybrid"},
                "stream": wrapped(),
            }
        except Exception as exc:
            logger.exception("ask_stream error")
            return {
                "session_id": None,
                "intent": "qa" if use_retrieval else "chat",
                "citations": [],
                "evaluation": {"streaming": False, "error": str(exc)},
                "stream": iter(["当前服务较忙或模型请求超时，请稍后重试。"]),
            }
