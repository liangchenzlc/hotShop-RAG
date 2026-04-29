from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.base import SchedulerNotRunningError
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI

from app.core.settings import get_settings
from app.db.models import DataSource
from app.db.session import SessionLocal
from app.scheduler.collector import run_collection


async def scheduled_collect() -> None:
    db = SessionLocal()
    try:
        sources = db.query(DataSource).filter(DataSource.is_active == True).all()
    finally:
        db.close()

    for src in sources:
        try:
            result = await run_collection(src)
            print(f"[scheduler] {src.name}: {result}")
        except Exception as exc:
            print(f"[scheduler] {src.name} failed: {exc}")


@asynccontextmanager
async def scheduler_lifespan(app: FastAPI):
    settings = get_settings()
    scheduler = AsyncIOScheduler()
    if settings.scheduler_enabled:
        scheduler.add_job(
            scheduled_collect,
            CronTrigger.from_crontab(settings.scheduler_cron),
            id="collect_all",
        )
    if scheduler.get_jobs():
        scheduler.start()
    try:
        yield
    finally:
        try:
            scheduler.shutdown(wait=False)
        except SchedulerNotRunningError:
            pass
