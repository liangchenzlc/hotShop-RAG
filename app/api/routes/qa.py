import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.schemas import AskRequest, AskResponse
from app.services.qa_service import QAService

router = APIRouter()


@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest, db: Session = Depends(get_db)) -> AskResponse:
    service = QAService(db)
    return service.ask(payload.question, payload.top_k, payload.use_retrieval, payload.session_id)


@router.post("/ask/stream")
def ask_stream(payload: AskRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    service = QAService(db)
    stream_payload = service.ask_stream(
        payload.question, payload.top_k, payload.use_retrieval, payload.session_id
    )

    def event_stream():
        answer_parts: list[str] = []
        for token in stream_payload["stream"]:
            answer_parts.append(token)
            yield f'data: {json.dumps({"type": "token", "token": token}, ensure_ascii=False)}\n\n'
        final_answer = "".join(answer_parts)
        done = {
            "type": "done",
            "session_id": stream_payload.get("session_id"),
            "answer": final_answer,
            "intent": stream_payload["intent"],
            "evaluation": stream_payload["evaluation"],
            "citations": [c.model_dump() for c in stream_payload["citations"]],
        }
        yield "data: " + json.dumps(done, ensure_ascii=False) + "\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
