from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SearchParams:
    keywords: list[str]
    max_results: int = 20
    language: str = "en"
    sort_by: str = "popularity"
    start_date: str | None = None
    end_date: str | None = None


@dataclass
class SourceArticle:
    source_type: str = ""
    source_account: str = ""
    title: str = ""
    url: str = ""
    published_at: datetime | None = None
    author: str | None = None
    summary: str | None = None
    content: str | None = None


class BaseSource(ABC):
    source_type: str = ""

    @abstractmethod
    async def search(self, params: SearchParams) -> list[SourceArticle]:
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def from_config(cls, config: dict) -> "BaseSource":
        raise NotImplementedError
