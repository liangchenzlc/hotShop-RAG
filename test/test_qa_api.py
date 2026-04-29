from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from test.mock_utils import MockDB


@pytest.fixture
def mock_db():
    return MockDB()


@pytest.fixture
def client(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    yield TestClient(app)
    app.dependency_overrides.clear()


class DummyChat:
    def compress_history(self, text): return text
    def build_chat_context(self, question): return f"ctx: {question}"
    def chat_answer(self, question, context): return f"ans: {question}"
    def chat_answer_stream(self, question, context):
        yield "token1"
        yield "token2"
    def answer_stream(self, question, context):
        yield "rag_token1"
        yield "rag_token2"
    def detect_malicious_input(self, question): return []


class DummyMemory:
    def get_or_create_session(self, session_id=None):
        return MagicMock(id=1)
    def get_messages(self, session_id): return []
    def add_message(self, *args, **kwargs): pass
    def build_history_text(self, messages): return ""


@pytest.fixture(autouse=True)
def patch_deps():
    with patch("app.services.qa_service.ChatRouter", return_value=DummyChat()):
        with patch("app.services.qa_service.ChatMemoryService", return_value=DummyMemory()):
            yield


class TestAsk:
    @patch("app.services.qa_service.MiniRAGAdapter.query")
    def test_ask_retrieval_200(self, mock_query, client, mock_db):
        mock_query.return_value = {
            "answer": "RAG is a retrieval augmented generation technique.",
            "raw_data": {"chunks": []},
        }
        resp = client.post("/qa/ask", json={
            "question": "What is RAG?",
            "top_k": 5,
            "use_retrieval": True,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "RAG" in data["answer"]
        assert data["intent"] == "qa"
        assert isinstance(data["session_id"], int)

    def test_ask_chat_200(self, client, mock_db):
        resp = client.post("/qa/ask", json={
            "question": "Hello",
            "top_k": 5,
            "use_retrieval": False,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "chat"
        assert data["answer"] != ""

    def test_ask_422(self, client, mock_db):
        resp = client.post("/qa/ask", json={})
        assert resp.status_code == 422


class TestAskStream:
    @patch("app.services.qa_service.MiniRAGStreamer.retrieve_context")
    def test_ask_stream_retrieval(self, mock_retrieve, client, mock_db):
        mock_retrieve.return_value = {
            "context": "Some context about RAG",
            "raw_data": {"chunks": []},
        }
        resp = client.post("/qa/ask/stream", json={
            "question": "What is RAG?",
            "top_k": 5,
            "use_retrieval": True,
        })
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        body = resp.text
        assert "data:" in body
        assert "rag_token1" in body or "token1" in body or "done" in body

    def test_ask_stream_chat(self, client, mock_db):
        resp = client.post("/qa/ask/stream", json={
            "question": "Hello",
            "top_k": 5,
            "use_retrieval": False,
        })
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        body = resp.text
        assert "data:" in body
