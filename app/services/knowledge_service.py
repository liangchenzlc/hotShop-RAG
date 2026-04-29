from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models import Article
from app.infra.graphrag.adapter import MiniRAGAdapter
from app.infra.storage.redis_client import RedisStorage


def _to_iso(dt: datetime | None) -> str | None:
    if not dt:
        return None
    return dt.replace(microsecond=0).isoformat() + "Z"


class KnowledgeService:
    def __init__(self, db: Session):
        self.db = db
        self.redis = RedisStorage()

    def stats(self) -> dict:
        total_articles = self.db.query(Article).count()
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_new = self.db.query(Article).filter(Article.created_at >= today_start).count()
        avg_hot_score = self.db.query(Article.hot_score).all()
        avg_val = 0.0
        if avg_hot_score:
            values = [row[0] for row in avg_hot_score if isinstance(row[0], (int, float))]
            avg_val = round(sum(values) / len(values), 1) if values else 0.0
        last_article = self.db.query(Article).order_by(Article.updated_at.desc()).first()
        return {
            "total_articles": total_articles,
            "today_new": today_new,
            "last_sync_time": _to_iso(last_article.updated_at if last_article else None),
            "avg_hot_score": avg_val,
        }

    def list_articles(
        self,
        keyword: str | None,
        date_from: str | None,
        date_to: str | None,
        sort_by: str,
        order: str,
        page: int,
        page_size: int,
    ) -> dict:
        query = self.db.query(Article)
        if keyword:
            like_kw = f"%{keyword}%"
            query = query.filter(
                (Article.title.like(like_kw)) | (Article.url.like(like_kw))
            )

        if date_from:
            query = query.filter(Article.published_at >= datetime.fromisoformat(date_from))
        if date_to:
            dt_to = datetime.fromisoformat(date_to)
            query = query.filter(Article.published_at < dt_to + timedelta(days=1))

        sort_col = Article.published_at if sort_by == "time" else Article.hot_score
        sort_expr = sort_col.asc() if order == "asc" else sort_col.desc()
        query = query.order_by(sort_expr, Article.id.desc())

        total = query.count()
        rows = query.offset((page - 1) * page_size).limit(page_size).all()
        items = [
            {
                "id": row.id,
                "title": row.title,
                "source_account": row.source_account,
                "url": row.url,
                "published_at": _to_iso(row.published_at),
                "hot_score": row.hot_score,
            }
            for row in rows
        ]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    def article_detail(self, article_id: int) -> dict:
        row = self.db.query(Article).filter(Article.id == article_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Article not found")
        content_markdown = self.redis.get_content(article_id) or ""
        return {
            "id": row.id,
            "title": row.title,
            "source_account": row.source_account,
            "url": row.url,
            "published_at": _to_iso(row.published_at),
            "hot_score": row.hot_score,
            "summary": row.summary,
            "content_markdown": content_markdown,
        }

    def delete_one(self, article_id: int) -> dict:
        row = self.db.query(Article).filter(Article.id == article_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Article not found")

        if row.doc_id:
            MiniRAGAdapter.delete_document(row.doc_id)

        self.redis.delete_content(article_id)
        self.db.query(Article).filter(Article.id == article_id).delete(
            synchronize_session=False
        )
        self.db.commit()
        return {"deleted": True, "article_id": article_id}

    def batch_delete(self, article_ids: list[int]) -> dict:
        if not article_ids:
            return {"deleted_count": 0}

        articles = (
            self.db.query(Article)
            .filter(Article.id.in_(article_ids))
            .all()
        )
        for article in articles:
            if article.doc_id:
                MiniRAGAdapter.delete_document(article.doc_id)
            self.redis.delete_content(article.id)

        deleted_count = (
            self.db.query(Article)
            .filter(Article.id.in_(article_ids))
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return {"deleted_count": deleted_count}
