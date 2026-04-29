"""
端到端采集测试：创建数据源 → 触发采集 → 验证入库
运行: python test_e2e.py
"""
import asyncio
from app.core.settings import get_settings
from app.db.session import ensure_schema_compatibility
from app.db.models import DataSource, Article
from app.db.session import SessionLocal
from app.scheduler.collector import run_collection
from app.infra.storage.redis_client import RedisStorage
from app.sources import init_sources

init_sources()

settings = get_settings()
print(f"MySQL: {settings.mysql_url}")
print(f"Redis: {settings.redis_url}")

# 1. 建表
ensure_schema_compatibility()
print("\n[OK] Tables synced")

# 2. 创建数据源
db = SessionLocal()
try:
    existing = db.query(DataSource).filter(DataSource.name == "newsapi_test").first()
    if not existing:
        ds = DataSource(
            name="newsapi_test",
            source_type="newsapi",
            is_active=True,
            config={
                "api_key": "158ae2fdfcd24dd68f8ab0ab40868e73",
                "endpoint": "https://newsapi.org/v2",
                "sort_by": "popularity",
                "language": "en",
            },
            keywords=["agent"],
        )
        db.add(ds)
        db.commit()
        print("[OK] DataSource created")
    else:
        ds = existing
        print("[OK] DataSource already exists")
finally:
    db.close()

# 3. 运行采集
async def collect():
    db2 = SessionLocal()
    try:
        src = db2.query(DataSource).filter(DataSource.name == "newsapi_test").first()
        print(f"\nCollecting from '{src.name}' keywords={src.keywords} ...")
        result = await run_collection(src)
        print(f"[OK] Collection result: {result}")
        return result
    finally:
        db2.close()

result = asyncio.run(collect())

# 4. 验证入库
db3 = SessionLocal()
try:
    total = db3.query(Article).filter(Article.source_type == "newsapi").count()
    print(f"\nArticles in MySQL: {total}")

    redis = RedisStorage()
    for a in db3.query(Article).order_by(Article.id.desc()).limit(5).all():
        content = redis.get_content(a.id)
        has_content = len(content or "") > 0
        print(f"  article#{a.id}: {a.title[:50]:50s} | Redis content: {'yes' if has_content else 'no'}")
finally:
    db3.close()

print("\n[DONE] End-to-end test complete")
