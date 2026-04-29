from app.sources.base import BaseSource


class SourceRegistry:
    _sources: dict[str, type[BaseSource]] = {}

    @classmethod
    def register(cls, source_cls: type[BaseSource]) -> None:
        st = source_cls.source_type
        if not st:
            raise ValueError(f"{source_cls.__name__}.source_type must be a non-empty string")
        cls._sources[st] = source_cls

    @classmethod
    def get_class(cls, source_type: str) -> type[BaseSource]:
        if source_type not in cls._sources:
            raise ValueError(
                f"Unknown source type: {source_type}. Registered: {list(cls._sources)}"
            )
        return cls._sources[source_type]

    @classmethod
    def create(cls, source_type: str, config: dict) -> BaseSource:
        source_cls = cls.get_class(source_type)
        return source_cls.from_config(config)

    @classmethod
    def registered_types(cls) -> list[str]:
        return list(cls._sources.keys())
