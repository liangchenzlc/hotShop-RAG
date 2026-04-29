from app.sources.newsapi import NewsAPISource
from app.sources.registry import SourceRegistry


def init_sources() -> None:
    SourceRegistry.register(NewsAPISource)
