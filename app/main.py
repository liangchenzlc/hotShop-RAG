from fastapi import FastAPI

from app.api.routes.chat_memory import router as chat_memory_router
from app.api.routes.health import router as health_router
from app.api.routes.indexing import router as indexing_router
from app.api.routes.knowledge import router as knowledge_router
from app.api.routes.qa import router as qa_router
from app.api.routes.search import router as search_router
from app.api.routes.source_management import router as source_management_router
from app.core.settings import get_settings
from app.db.session import ensure_schema_compatibility
from app.infra.graphrag import MiniRAGAdapter, build_minirag_config
from app.scheduler.jobs import scheduler_lifespan
from app.sources import init_sources


def create_app() -> FastAPI:
    init_sources()
    settings = get_settings()
    ensure_schema_compatibility()

    MiniRAGAdapter.initialize(build_minirag_config(settings))

    app = FastAPI(title=settings.app_name, version=settings.app_version)

    app.include_router(health_router, tags=["health"])
    app.include_router(source_management_router, prefix="/sources", tags=["sources"])
    app.include_router(indexing_router, prefix="/index", tags=["index"])
    app.include_router(knowledge_router, prefix="/knowledge", tags=["knowledge"])
    app.include_router(search_router, tags=["search"])
    app.include_router(qa_router, prefix="/qa", tags=["qa"])
    app.include_router(chat_memory_router, prefix="/chat", tags=["chat-memory"])

    app.router.lifespan_context = scheduler_lifespan
    return app


app = create_app()
