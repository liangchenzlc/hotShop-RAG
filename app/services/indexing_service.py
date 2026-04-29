from sqlalchemy.orm import Session

from app.db.models import Article
from app.infra.graphrag.adapter import MiniRAGAdapter
from app.infra.storage.redis_client import RedisStorage


class IndexingService:
    def __init__(self, db: Session):
        self.db = db
        self.redis = RedisStorage()

    def rebuild(self, article_ids: list[int] | None = None) -> dict:
        query = self.db.query(Article).filter(Article.status >= 1)
        if article_ids:
            query = query.filter(Article.id.in_(article_ids))
        articles = query.all()

        indexed = 0
        failed = 0
        error_samples: list[str] = []
        for article in articles:
            try:
                text = self.redis.get_content(article.id)
                if not text:
                    text = "\n".join(
                        filter(None, [article.title, article.summary, f"url: {article.url}"])
                    )

                doc_id = MiniRAGAdapter.insert_from_articles(
                    article.id, text, article.title, article.summary
                )
                if not doc_id:
                    raise ValueError("empty content, cannot index")

                article.doc_id = doc_id
                article.status = 2
                indexed += 1
                self.db.flush()
            except Exception as exc:
                failed += 1
                self.db.rollback()
                if len(error_samples) < 5:
                    error_samples.append(f"article_id={article.id} failed: {exc}")

        self.db.commit()
        return {
            "total_articles": len(articles),
            "indexed_articles": indexed,
            "failed_articles": failed,
            "error_samples": error_samples,
        }
