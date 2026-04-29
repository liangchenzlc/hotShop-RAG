import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.settings import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app

SQLITE_URL = "sqlite:///./test.db?check_same_thread=false"


@pytest.fixture(scope="session")
def test_client():
    os.environ["SCHEDULER_ENABLED"] = "false"
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as client:
        yield client


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(SQLITE_URL, pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client_with_db(db_session):
    """TestClient with get_db overridden to use the test DB session."""
    from app.main import app as _app
    _app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(_app) as client:
        yield client
    _app.dependency_overrides.clear()
