from unittest.mock import patch

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


class TestRebuildIndex:
    @patch("app.services.indexing_service.RedisStorage.get_content")
    @patch("app.services.indexing_service.MiniRAGAdapter.insert_from_articles")
    def test_rebuild_all_200(self, mock_insert, mock_redis, client, mock_db):
        from app.db.models import Article
        from test.mock_utils import make_mock_model
        mock_redis.return_value = "Full article content..."
        mock_insert.return_value = "doc-abc123"
        articles = [
            make_mock_model(id=1, title="Article 1", status=1, doc_id=None, spec=Article),
            make_mock_model(id=2, title="Article 2", status=1, doc_id=None, spec=Article),
        ]
        mock_db.seed(Article, articles)
        resp = client.post("/index/rebuild", json={"article_ids": []})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_articles"] == 2
        assert data["indexed_articles"] == 2
        assert data["failed_articles"] == 0

    @patch("app.services.indexing_service.RedisStorage.get_content")
    @patch("app.services.indexing_service.MiniRAGAdapter.insert_from_articles")
    def test_rebuild_specific_ids(self, mock_insert, mock_redis, client, mock_db):
        from app.db.models import Article
        from test.mock_utils import make_mock_model
        mock_redis.return_value = "Content..."
        mock_insert.return_value = "doc-abc123"
        articles = [make_mock_model(id=1, title="Article 1", status=1, doc_id=None, spec=Article)]
        mock_db.seed(Article, articles)
        resp = client.post("/index/rebuild", json={"article_ids": [1]})
        assert resp.status_code == 200

    def test_rebuild_no_articles(self, client, mock_db):
        resp = client.post("/index/rebuild", json={"article_ids": []})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_articles"] == 0
