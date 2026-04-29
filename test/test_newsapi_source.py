from datetime import datetime

import pytest

from app.sources.base import SearchParams
from app.sources.newsapi import NewsAPISource


class FakeResponse:
    def __init__(self, data: dict, status: int = 200):
        self._data = data
        self.status_code = status

    def raise_for_status(self):
        if self.status_code != 200:
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        return self._data


@pytest.mark.asyncio
async def test_search_returns_articles(monkeypatch):
    async def fake_get(self, url, *, params=None, headers=None):
        assert "api.newsapi.org" not in url  # no real call
        return FakeResponse({
            "status": "ok",
            "totalResults": 2,
            "articles": [
                {
                    "source": {"id": "techcrunch", "name": "TechCrunch"},
                    "author": "John Doe",
                    "title": "Test Article",
                    "description": "A test article description",
                    "url": "https://techcrunch.com/test",
                    "urlToImage": "https://img.example.com/1.jpg",
                    "publishedAt": "2026-04-28T10:00:00Z",
                    "content": "Full content of the test article...",
                },
                {
                    "source": {"id": None, "name": "Unknown Blog"},
                    "author": None,
                    "title": "Second Article Title",
                    "description": "Short description",
                    "url": "https://example.com/article2",
                    "urlToImage": None,
                    "publishedAt": None,
                    "content": None,
                },
            ],
        })

    monkeypatch.setattr("httpx.AsyncClient.get", fake_get)

    source = NewsAPISource(api_key="test-key")
    params = SearchParams(keywords=["test"], max_results=10)
    articles = await source.search(params)

    assert len(articles) == 2

    # 验证第一个文章完整映射
    a1 = articles[0]
    assert a1.source_type == "newsapi"
    assert a1.source_account == "TechCrunch"
    assert a1.title == "Test Article"
    assert a1.url == "https://techcrunch.com/test"
    assert a1.author == "John Doe"
    assert a1.summary == "A test article description"
    assert a1.content == "Full content of the test article..."
    assert a1.published_at == datetime(2026, 4, 28, 10, 0, 0)

    # 验证第二个文章（缺失字段处理）
    a2 = articles[1]
    assert a2.source_account == "Unknown Blog"
    assert a2.title == "Second Article Title"
    assert a2.author is None
    assert a2.published_at is None
    assert a2.content is None


@pytest.mark.asyncio
async def test_search_empty_results(monkeypatch):
    async def fake_get(self, url, *, params=None, headers=None):
        return FakeResponse({
            "status": "ok",
            "totalResults": 0,
            "articles": [],
        })

    monkeypatch.setattr("httpx.AsyncClient.get", fake_get)

    source = NewsAPISource(api_key="test-key")
    articles = await source.search(SearchParams(keywords=["nothing"]))
    assert articles == []


@pytest.mark.asyncio
async def test_search_api_error(monkeypatch):
    async def fake_get(self, url, *, params=None, headers=None):
        return FakeResponse({
            "status": "error",
            "code": "rateLimited",
            "message": "You have made too many requests",
        })

    monkeypatch.setattr("httpx.AsyncClient.get", fake_get)

    source = NewsAPISource(api_key="test-key")
    with pytest.raises(RuntimeError, match="too many requests"):
        await source.search(SearchParams(keywords=["test"]))


@pytest.mark.asyncio
async def test_search_http_error(monkeypatch):
    async def fake_get(self, url, *, params=None, headers=None):
        raise Exception("HTTP 401")

    monkeypatch.setattr("httpx.AsyncClient.get", fake_get)

    source = NewsAPISource(api_key="bad-key")
    with pytest.raises(Exception, match="HTTP 401"):
        await source.search(SearchParams(keywords=["test"]))


def test_fetch_raises_not_implemented():
    source = NewsAPISource(api_key="test-key")
    with pytest.raises(NotImplementedError):
        import asyncio
        asyncio.run(source.fetch(urls=["https://example.com"]))


def test_from_config():
    config = {
        "api_key": "abc123",
        "endpoint": "https://custom.api.com/v2",
        "sort_by": "publishedAt",
        "language": "zh",
    }
    source = NewsAPISource.from_config(config)
    assert source.api_key == "abc123"
    assert source.endpoint == "https://custom.api.com/v2"
    assert source.default_sort_by == "publishedAt"
    assert source.default_language == "zh"


def test_source_type():
    assert NewsAPISource.source_type == "newsapi"
