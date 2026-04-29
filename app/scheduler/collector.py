from datetime import datetime

from app.db.models import DataSource
from app.db.session import SessionLocal
from app.services.ingestion_service import IngestionService
from app.sources.base import SearchParams
from app.sources.registry import SourceRegistry


async def run_collection(source_record: DataSource) -> dict:
    """Collect articles from a single data source and persist them."""
    source = SourceRegistry.create(source_record.source_type, source_record.config)

    params = SearchParams(
        keywords=source_record.keywords or [],
        max_results=source_record.config.get("max_results", 20),
        language=source_record.config.get("language", "en"),
        sort_by=source_record.config.get("sort_by", "popularity"),
    )

    articles = await source.search(params)

    db = SessionLocal()
    try:
        svc = IngestionService(db)
        result = await svc.ingest_articles(
            articles=articles,
            source_type=source_record.source_type,
            trigger_mode="scheduled",
        )

        # Update last run time for this source
        db_ref = db.query(DataSource).filter(DataSource.id == source_record.id).first()
        if db_ref:
            db_ref.last_run_at = datetime.utcnow()
        db.commit()
        return result
    finally:
        db.close()
