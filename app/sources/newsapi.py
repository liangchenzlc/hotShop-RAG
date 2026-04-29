from datetime import datetime

import httpx

from app.sources.base import BaseSource, SearchParams, SourceArticle


class NewsAPISource(BaseSource):
    source_type = "newsapi"

    def __init__(
        self,
        api_key: str,
        endpoint: str = "https://newsapi.org/v2",
        sort_by: str = "popularity",
        language: str = "en",
    ):
        self.api_key = api_key
        self.endpoint = endpoint.rstrip("/")
        self.default_sort_by = sort_by
        self.default_language = language

    async def search(self, params: SearchParams) -> list[SourceArticle]:
        query = " OR ".join(params.keywords)
        url = f"{self.endpoint}/everything"

        request_params: dict = {
            "q": query,
            "sortBy": params.sort_by or self.default_sort_by,
            "pageSize": min(params.max_results, 100),
            "language": params.language or self.default_language,
        }
        if params.start_date:
            request_params["from"] = params.start_date
        if params.end_date:
            request_params["to"] = params.end_date

        headers = {"X-Api-Key": self.api_key}

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, params=request_params, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != "ok":
            raise RuntimeError(f"NewsAPI error: {data.get('message', 'unknown')}")

        results: list[SourceArticle] = []
        for item in data.get("articles", []):
            source_name = (item.get("source") or {}).get("name", "") or ""
            published = self._parse_datetime(item.get("publishedAt"))
            results.append(
                SourceArticle(
                    source_type=self.source_type,
                    source_account=source_name or "newsapi",
                    title=(item.get("title") or "").strip() or "Untitled",
                    url=(item.get("url") or "").strip(),
                    published_at=published,
                    author=item.get("author"),
                    summary=item.get("description"),
                    content=item.get("content"),
                )
            )

        return results

    async def fetch(self, urls: list[str], accounts: list[str] | None = None) -> list[SourceArticle]:
        raise NotImplementedError("NewsAPI does not support URL-based fetch")

    @classmethod
    def from_config(cls, config: dict) -> "NewsAPISource":
        return cls(
            api_key=config["api_key"],
            endpoint=config.get("endpoint", "https://newsapi.org/v2"),
            sort_by=config.get("sort_by", "popularity"),
            language=config.get("language", "en"),
        )

    @staticmethod
    def _parse_datetime(raw: str | None) -> datetime | None:
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            return None
