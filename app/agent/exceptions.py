class MiniRAGError(Exception):
    pass


class StorageNotInitializedError(MiniRAGError):
    pass


class LLMError(MiniRAGError):
    pass


class EmbeddingError(MiniRAGError):
    pass


class ChunkError(MiniRAGError):
    pass


class ExtractionError(MiniRAGError):
    pass


class QueryError(MiniRAGError):
    pass
