import redis as _redis

from app.core.settings import get_settings


class RedisStorage:
    """KV storage for article markdown content using Redis.

    Key format: article:{article_id} → markdown string
    """

    KEY_PREFIX = "article:"

    def __init__(self) -> None:
        settings = get_settings()
        self.client = _redis.from_url(settings.redis_url)

    def put_content(self, article_id: int, content: str) -> bool:
        key = f"{self.KEY_PREFIX}{article_id}"
        return bool(self.client.set(key, content.encode("utf-8")))

    def get_content(self, article_id: int) -> str | None:
        key = f"{self.KEY_PREFIX}{article_id}"
        val = self.client.get(key)
        return val.decode("utf-8") if val else None

    def delete_content(self, article_id: int) -> bool:
        key = f"{self.KEY_PREFIX}{article_id}"
        return bool(self.client.delete(key))
