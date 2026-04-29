import pytest

from app.sources.base import BaseSource, SearchParams, SourceArticle


class FakeSource(BaseSource):
    source_type = "fake"

    def __init__(self, val: str = "default"):
        self.val = val

    async def search(self, params: SearchParams) -> list[SourceArticle]:
        return [SourceArticle(title=params.keywords[0])]

    @classmethod
    def from_config(cls, config: dict) -> "FakeSource":
        return cls(val=config.get("val", "default"))


class AnotherSource(BaseSource):
    source_type = "another"

    async def search(self, params: SearchParams) -> list[SourceArticle]:
        return []

    @classmethod
    def from_config(cls, config: dict) -> "AnotherSource":
        return cls()


def test_register_and_create():
    from app.sources.registry import SourceRegistry

    SourceRegistry.register(FakeSource)
    SourceRegistry.register(AnotherSource)

    assert "fake" in SourceRegistry.registered_types()
    assert "another" in SourceRegistry.registered_types()

    source = SourceRegistry.create("fake", {"val": "hello"})
    assert isinstance(source, FakeSource)
    assert source.val == "hello"

    source2 = SourceRegistry.create("another", {})
    assert isinstance(source2, AnotherSource)


def test_get_class():
    from app.sources.registry import SourceRegistry

    cls = SourceRegistry.get_class("fake")
    assert cls is FakeSource

    with pytest.raises(ValueError, match="Unknown source type"):
        SourceRegistry.get_class("nonexistent")


def test_create_nonexistent():
    from app.sources.registry import SourceRegistry

    with pytest.raises(ValueError, match="Unknown source type"):
        SourceRegistry.create("nonexistent", {})


def test_register_empty_source_type_raises():
    from app.sources.registry import SourceRegistry

    class BadSource(BaseSource):
        source_type = ""

        async def search(self, params):
            return []

        @classmethod
        def from_config(cls, config):
            return cls()

    with pytest.raises(ValueError, match="must be a non-empty string"):
        SourceRegistry.register(BadSource)
