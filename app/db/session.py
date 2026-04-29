import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.settings import get_settings
from app.db.base import Base

settings = get_settings()
engine = create_engine(settings.mysql_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def ensure_schema_compatibility() -> None:
    """Create all tables if they don't exist (non-fatal on failure)."""
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        logging.warning("schema sync skipped (DB not reachable): %s", exc)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
