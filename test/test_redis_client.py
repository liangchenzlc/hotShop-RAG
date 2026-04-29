import pytest

from app.infra.storage.redis_client import RedisStorage


@pytest.fixture
def storage():
    s = RedisStorage()
    # clean up before test
    s.client.delete("article:999", "article:1000")
    yield s
    s.client.delete("article:999", "article:1000")


def test_put_and_get_content(storage):
    assert storage.put_content(999, "# Hello Redis")
    content = storage.get_content(999)
    assert content == "# Hello Redis"


def test_get_nonexistent_returns_none(storage):
    content = storage.get_content(99999)
    assert content is None


def test_delete_content(storage):
    storage.put_content(1000, "data")
    assert storage.get_content(1000) == "data"
    assert storage.delete_content(1000)
    assert storage.get_content(1000) is None


def test_overwrite_content(storage):
    storage.put_content(999, "original")
    storage.put_content(999, "updated")
    assert storage.get_content(999) == "updated"


def test_unicode_content(storage):
    text = "# 中文标题\n\n这是正文内容。"
    storage.put_content(999, text)
    assert storage.get_content(999) == text
