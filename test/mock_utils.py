"""Shared mock utilities for API tests."""

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock


def make_mock_model(**kwargs: Any) -> MagicMock:
    """Create a mock model instance with given attributes.

    Usage: make_mock_model(id=1, name="foo", spec=DataSource)
    """
    spec = kwargs.pop("spec", None)
    m = MagicMock(spec=spec) if spec else MagicMock()
    for k, v in kwargs.items():
        setattr(m, k, v)
    return m


class MockQuery:
    """Chainable mock for SQLAlchemy Query."""

    def __init__(self, db: "MockDB", model: type | None):
        self._db = db
        self._model = model

    def filter(self, *args: Any, **kwargs: Any) -> "MockQuery":
        return self

    def filter_by(self, **kwargs: Any) -> "MockQuery":
        return self

    def first(self) -> Any:
        items = self._db._get_items(self._model)
        return items[0] if items else None

    def all(self) -> list:
        return list(self._db._get_items(self._model))

    def count(self) -> int:
        return len(self._db._get_items(self._model))

    def order_by(self, *args: Any) -> "MockQuery":
        return self

    def offset(self, n: int) -> "MockQuery":
        return self

    def limit(self, n: int) -> "MockQuery":
        return self

    def delete(self, synchronize_session: bool = False) -> int:
        items = self._db._get_items(self._model)
        count = len(items)
        if self._model is not None:
            self._db._data[self._model] = []
        return count

    def __iter__(self):
        return iter(self._db._get_items(self._model))


class MockDB:
    """Mock SQLAlchemy Session for API testing."""

    def __init__(self):
        self._data: dict = {}
        self.added: list = []
        self.committed = False
        self.rolled_back = False
        self.flushed = False

    def _get_items(self, model: type | None) -> list:
        if model is None:
            return []
        return self._data.get(model, [])

    def seed(self, model: type, items: list) -> None:
        self._data[model] = list(items)

    def query(self, *args: Any) -> MockQuery:
        if len(args) == 1 and isinstance(args[0], type):
            return MockQuery(self, args[0])
        return MockQuery(self, None)

    def add(self, obj: Any) -> None:
        if not getattr(obj, "id", None):
            obj.id = len(self.added) + 1
        if not getattr(obj, "created_at", None):
            obj.created_at = datetime(2026, 4, 29, 10, 0, 0)
        if not getattr(obj, "updated_at", None):
            obj.updated_at = datetime(2026, 4, 29, 10, 0, 0)
        self.added.append(obj)

    def add_all(self, objs: list) -> None:
        for obj in objs:
            self.add(obj)

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def flush(self) -> None:
        self.flushed = True

    def refresh(self, obj: Any) -> None:
        if not getattr(obj, "id", None):
            obj.id = 1
        if not getattr(obj, "created_at", None):
            obj.created_at = datetime(2026, 4, 29, 10, 0, 0)
        if not getattr(obj, "updated_at", None):
            obj.updated_at = datetime(2026, 4, 29, 10, 0, 0)

    def delete(self, obj: Any) -> None:
        for model, items in list(self._data.items()):
            for i, item in enumerate(items):
                if item is obj or (hasattr(item, "id") and hasattr(obj, "id") and item.id == obj.id):
                    self._data[model].pop(i)
                    return

    def get(self, model: type, ident: Any) -> Any:
        for item in self._data.get(model, []):
            if getattr(item, "id", None) == ident:
                return item
        return None

    def close(self) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass
