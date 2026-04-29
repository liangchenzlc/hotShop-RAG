from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import Article, IngestionJob
from app.infra.storage.redis_client import RedisStorage
from app.services.utils import sha256_text
from app.sources.base import SourceArticle


class IngestionService:
    def __init__(self, db: Session):
        self.db = db
        self.redis = RedisStorage()

    async def ingest_articles(
        self,
        articles: list[SourceArticle],
        source_type: str,
        trigger_mode: str = "manual",
    ) -> dict:
        job = IngestionJob(
            trigger_mode=trigger_mode,
            source_type=source_type,
            request_payload={"article_count": len(articles)},
            status="running",
            started_at=datetime.utcnow(),
        )
        self.db.add(job)
        self.db.flush()

        fetched = new = dedup = errors = 0
        error_msgs: list[str] = []

        for article in articles:
            fetched += 1
            existed = self.db.query(Article).filter(Article.url == article.url).first()
            if existed:
                dedup += 1
                continue

            try:
                content = article.content or article.summary or ""
                if not content.strip():
                    content = article.title

                db_article = Article(
                    source_type=source_type,
                    source_account=article.source_account,
                    title=article.title,
                    url=article.url,
                    url_hash=sha256_text(article.url),
                    published_at=article.published_at,
                    author=article.author,
                    summary=article.summary,
                    content_hash=sha256_text(content),
                    status=1,
                )
                self.db.add(db_article)
                self.db.flush()

                markdown_body = self._build_markdown(article)
                self.redis.put_content(db_article.id, markdown_body)
                new += 1
            except Exception as exc:
                errors += 1
                if len(error_msgs) < 5:
                    error_msgs.append(f"url={article.url}: {exc}")

        job.fetched_count = fetched
        job.new_count = new
        job.dedup_count = dedup
        job.error_count = errors
        job.status = "success" if errors == 0 else "partial_success"
        if error_msgs:
            job.error_message = "; ".join(error_msgs)
        job.finished_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(job)

        return {
            "job_id": job.id,
            "status": job.status,
            "fetched": fetched,
            "new": new,
            "dedup": dedup,
            "errors": errors,
        }

    @staticmethod
    def _build_markdown(article: SourceArticle) -> str:
        parts = [f"# {article.title}"]
        if article.author:
            parts.append(f"\n**Author**: {article.author}")
        if article.published_at:
            parts.append(f"\n**Published**: {article.published_at.isoformat()}")
        if article.summary:
            parts.append(f"\n\n{article.summary}")
        if article.content:
            parts.append(f"\n\n{article.content}")
        parts.append(f"\n\n---\nSource: {article.url}")
        return "".join(parts)
