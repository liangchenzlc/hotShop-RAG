from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.domain.schemas import SearchHit
from test.mock_utils import MockDB


@pytest.fixture
def mock_db():
    return MockDB()


@pytest.fixture
def client(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestSearch:
    @patch("app.services.retrieval_service.MiniRAGAdapter.query")
    def test_search_200(self, mock_query, client, mock_db):
        mock_query.return_value = {
            "answer": "",
            "raw_data": {
                "chunks": [
                    {
                        "content": "RAG is retrieval augmented generation",
                        "distance": 0.92,
                        "full_doc_id": "doc-1",
                        "chunk_order_index": 0,
                    }
                ]
            },
        }
        from app.db.models import Article
        from test.mock_utils import make_mock_model
        article = make_mock_model(
            id=1, title="RAG Tech", url="https://example.com/rag",
            doc_id="doc-1", spec=Article,
        )
        mock_db.seed(Article, [article])
        resp = client.post("/search", json={"query": "RAG", "top_k": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["hits"]) == 1
        assert data["hits"][0]["article_id"] == 1
        assert data["hits"][0]["title"] == "RAG Tech"

    @patch("app.services.retrieval_service.MiniRAGAdapter.query")
    def test_search_no_results(self, mock_query, client, mock_db):
        mock_query.return_value = {"answer": "", "raw_data": {"chunks": []}}
        resp = client.post("/search", json={"query": "nothing", "top_k": 5})
        assert resp.status_code == 200
        assert resp.json()["hits"] == []

    def test_search_422_missing_query(self, client, mock_db):
        resp = client.post("/search", json={"top_k": 5})
        assert resp.status_code == 422
