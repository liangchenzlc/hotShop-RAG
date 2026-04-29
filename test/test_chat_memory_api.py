import pytest
from fastapi.testclient import TestClient

from app.db.models import ChatMessage, ChatSession
from app.db.session import get_db
from app.main import app
from test.mock_utils import MockDB, make_mock_model


# --- Tests using MockDB (for data seeding + mocking) ---

@pytest.fixture
def mock_db():
    return MockDB()


@pytest.fixture
def client(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestListSessions:
    def test_list_empty(self, client, mock_db):
        resp = client.get("/chat/sessions")
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    def test_list_200(self, client, mock_db):
        from datetime import datetime
        now = datetime(2026, 4, 29, 10, 0, 0)
        session = make_mock_model(
            id=1, title="新对话", message_count=0,
            created_at=now, updated_at=now,
        )
        mock_db.seed(ChatSession, [session])
        resp = client.get("/chat/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data


class TestDeleteSession:
    def test_delete_200(self, client, mock_db):
        from datetime import datetime
        session = make_mock_model(id=1, title="test")
        mock_db.seed(ChatSession, [session])
        resp = client.delete("/chat/sessions/1")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_delete_404(self, client, mock_db):
        resp = client.delete("/chat/sessions/999")
        assert resp.status_code == 404


class TestListMessages:
    def test_list_messages_200(self, client, mock_db):
        from datetime import datetime
        now = datetime(2026, 4, 29, 10, 0, 0)
        msg = make_mock_model(
            id=1, session_id=1, role="user",
            content="Hello", citations=None, intent=None,
            created_at=now,
        )
        mock_db.seed(ChatMessage, [msg])
        resp = client.get("/chat/sessions/1/messages")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["role"] == "user"
        assert data["items"][0]["content"] == "Hello"

    def test_list_messages_empty(self, client, mock_db):
        resp = client.get("/chat/sessions/1/messages")
        assert resp.status_code == 200
        assert resp.json()["items"] == []


# --- Tests using real SQLite DB (for endpoints that create real model instances) ---

class TestCreateSession:
    def test_create_200(self, db_session):
        """Use real SQLite to test session creation with proper model defaults."""
        app.dependency_overrides[get_db] = lambda: db_session
        client = TestClient(app)
        resp = client.post("/chat/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "新对话"
        assert data["message_count"] == 0
        assert isinstance(data["id"], int)
        app.dependency_overrides.clear()
