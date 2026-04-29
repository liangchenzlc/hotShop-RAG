from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db.models import DataSource
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


def _make_source(id: int, name: str = "test_source", **overrides) -> DataSource:
    now = datetime(2026, 4, 29, 10, 0, 0)
    kwargs = dict(
        id=id,
        name=name,
        source_type="newsapi",
        is_active=True,
        config={"api_key": "***", "language": "en"},
        keywords=["technology", "AI"],
        schedule_cron=None,
        max_workers=3,
        last_run_at=None,
        created_at=now,
        updated_at=now,
    )
    kwargs.update(overrides)
    return make_mock_model(**kwargs, spec=DataSource)


class TestCreateSource:
    def test_create_201(self, client, mock_db):
        payload = {
            "name": "newsapi_hot",
            "source_type": "newsapi",
            "keywords": ["technology", "AI"],
        }
        resp = client.post("/sources", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "newsapi_hot"
        assert data["source_type"] == "newsapi"
        assert data["is_active"] is True

    def test_create_409_duplicate(self, client, mock_db):
        source = _make_source(1, "dup_source")
        mock_db.seed(DataSource, [source])
        payload = {"name": "dup_source", "source_type": "newsapi"}
        resp = client.post("/sources", json=payload)
        assert resp.status_code == 409

    def test_create_422_missing_field(self, client, mock_db):
        resp = client.post("/sources", json={})
        assert resp.status_code == 422


class TestListSources:
    def test_list_empty(self, client, mock_db):
        resp = client.get("/sources")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_list_with_items(self, client, mock_db):
        now = datetime(2026, 4, 29, 10, 0, 0)
        s1 = _make_source(1, "src_a", created_at=now, updated_at=now)
        s2 = _make_source(2, "src_b", created_at=now, updated_at=now)
        mock_db.seed(DataSource, [s1, s2])
        resp = client.get("/sources")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2


class TestGetSource:
    def test_get_200(self, client, mock_db):
        source = _make_source(1, "test_source")
        mock_db.seed(DataSource, [source])
        resp = client.get("/sources/1")
        assert resp.status_code == 200
        assert resp.json()["name"] == "test_source"

    def test_get_404(self, client, mock_db):
        resp = client.get("/sources/999")
        assert resp.status_code == 404


class TestUpdateSource:
    def test_update_200(self, client, mock_db):
        source = _make_source(1, "old_name")
        mock_db.seed(DataSource, [source])
        resp = client.patch("/sources/1", json={"name": "new_name"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "new_name"

    def test_update_404(self, client, mock_db):
        resp = client.patch("/sources/999", json={"name": "nope"})
        assert resp.status_code == 404


class TestDeleteSource:
    def test_delete_204(self, client, mock_db):
        source = _make_source(1)
        mock_db.seed(DataSource, [source])
        resp = client.delete("/sources/1")
        assert resp.status_code == 204

    def test_delete_404(self, client, mock_db):
        resp = client.delete("/sources/999")
        assert resp.status_code == 404


class TestCollectAll:
    @patch("app.api.routes.source_management.run_collection")
    def test_collect_all_ok(self, mock_run, client, mock_db):
        from test.mock_utils import make_mock_model
        src1 = _make_source(1, "src_a", is_active=True)
        src2 = _make_source(2, "src_b", is_active=True)
        mock_db.seed(DataSource, [src1, src2])
        mock_run.return_value = {"job_id": 1, "status": "success", "fetched": 5, "new": 3, "dedup": 2, "errors": 0}
        resp = client.post("/sources/collect-all")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 2
        assert data["results"][0]["status"] == "ok"

    @patch("app.api.routes.source_management.run_collection")
    def test_collect_all_no_active(self, mock_run, client, mock_db):
        resp = client.post("/sources/collect-all")
        assert resp.status_code == 200
        assert resp.json()["results"] == []


class TestCollectSource:
    @patch("app.api.routes.source_management.run_collection")
    def test_collect_200(self, mock_run, client, mock_db):
        source = _make_source(1, "src_a")
        mock_db.seed(DataSource, [source])
        mock_run.return_value = {"job_id": 1, "status": "success", "fetched": 5, "new": 3, "dedup": 2, "errors": 0}
        resp = client.post("/sources/1/collect")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_collect_404(self, client, mock_db):
        resp = client.post("/sources/999/collect")
        assert resp.status_code == 404
