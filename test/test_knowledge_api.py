from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.db.models import Article
from app.db.session import get_db
from app.main import app
from test.mock_utils import MockDB, make_mock_model


@pytest.fixture
def mock_db():
    return MockDB()


@pytest.fixture
def client(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _make_article(id: int = 1, **overrides) -> Article:
    kwargs = dict(
        id=id,
        title=f"Article {id}",
        source_account="TechCrunch",
        url=f"https://example.com/{id}",
        url_hash=f"hash{id}",
        content_hash=f"chash{id}",
        published_at=datetime(2026, 4, 28, 10, 0, 0),
        summary="A test summary",
        hot_score=5,
        status=1,
        doc_id=f"doc-{id}",
        created_at=datetime(2026, 4, 28, 10, 0, 0),
        updated_at=datetime(2026, 4, 28, 10, 0, 0),
    )
    kwargs.update(overrides)
    return make_mock_model(**kwargs, spec=Article)


class TestKnowledgeStats:
    def test_stats_200(self, client, mock_db):
        article = _make_article(1)
        mock_db.seed(Article, [article])
        resp = client.get("/knowledge/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_articles"] == 1
        assert isinstance(data["avg_hot_score"], float)
        assert data["last_sync_time"] is not None

    def test_stats_empty(self, client, mock_db):
        resp = client.get("/knowledge/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_articles"] == 0
        assert data["avg_hot_score"] == 0.0


class TestListArticles:
    def test_list_200(self, client, mock_db):
        article = _make_article(1)
        mock_db.seed(Article, [article])
        resp = client.get("/knowledge/articles")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Article 1"

    def test_list_empty(self, client, mock_db):
        resp = client.get("/knowledge/articles")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_with_keyword(self, client, mock_db):
        a1 = _make_article(1, title="AI Technology")
        a2 = _make_article(2, title="Climate Change")
        mock_db.seed(Article, [a1, a2])
        resp = client.get("/knowledge/articles", params={"keyword": "AI"})
        assert resp.status_code == 200

    def test_list_pagination(self, client, mock_db):
        articles = [_make_article(i) for i in range(1, 6)]
        mock_db.seed(Article, articles)
        resp = client.get("/knowledge/articles", params={"page": 1, "page_size": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["page_size"] == 2

    def test_list_invalid_sort(self, client, mock_db):
        resp = client.get("/knowledge/articles", params={"sort_by": "invalid"})
        assert resp.status_code == 422

    def test_list_invalid_order(self, client, mock_db):
        resp = client.get("/knowledge/articles", params={"order": "invalid"})
        assert resp.status_code == 422


class TestArticleDetail:
    @patch("app.services.knowledge_service.RedisStorage")
    def test_detail_200(self, mock_redis_cls, client, mock_db):
        mock_redis = mock_redis_cls.return_value
        mock_redis.get_content.return_value = "# Markdown Content"
        article = _make_article(1)
        mock_db.seed(Article, [article])
        resp = client.get("/knowledge/articles/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Article 1"
        assert data["content_markdown"] == "# Markdown Content"

    def test_detail_404(self, client, mock_db):
        resp = client.get("/knowledge/articles/999")
        assert resp.status_code == 404


class TestDeleteArticle:
    @patch("app.services.knowledge_service.MiniRAGAdapter.delete_document")
    @patch("app.services.knowledge_service.RedisStorage")
    def test_delete_200(self, mock_redis_cls, mock_minirag, client, mock_db):
        article = _make_article(1, doc_id="doc-1")
        mock_db.seed(Article, [article])
        resp = client.delete("/knowledge/articles/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted"] is True
        assert data["article_id"] == 1

    def test_delete_404(self, client, mock_db):
        resp = client.delete("/knowledge/articles/999")
        assert resp.status_code == 404


class TestBatchDelete:
    @patch("app.services.knowledge_service.MiniRAGAdapter.delete_document")
    @patch("app.services.knowledge_service.RedisStorage")
    def test_batch_delete_200(self, mock_redis_cls, mock_minirag, client, mock_db):
        articles = [_make_article(i, doc_id=f"doc-{i}") for i in range(1, 4)]
        mock_db.seed(Article, articles)
        resp = client.post("/knowledge/articles/batch-delete", json={"article_ids": [1, 2, 3]})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["deleted_count"], int)

    def test_batch_delete_empty(self, client, mock_db):
        resp = client.post("/knowledge/articles/batch-delete", json={"article_ids": []})
        assert resp.status_code == 200
        assert resp.json()["deleted_count"] == 0
