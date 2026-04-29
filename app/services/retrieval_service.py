from sqlalchemy.orm import Session

from app.db.models import Article
from app.domain.schemas import SearchHit
from app.infra.graphrag.adapter import MiniRAGAdapter
from app.agent import QueryParam


class RetrievalService:
    def __init__(self, db: Session):
        self.db = db

    def search(self, query: str, top_k: int) -> list[SearchHit]:
        param = QueryParam(
            mode="naive",
            top_k=top_k * 2,
            chunk_top_k=top_k,
        )
        result = MiniRAGAdapter.query(query, param)
        raw_data = result.get("raw_data", {})
        chunks = raw_data.get("chunks", [])

        hits: list[SearchHit] = []
        for chunk in chunks[:top_k]:
            content = chunk.get("content", "")
            score = float(chunk.get("distance", 0.0))
            doc_id = chunk.get("full_doc_id", "")
            chunk_no = int(chunk.get("chunk_order_index", 0))

            article = None
            if doc_id:
                article = (
                    self.db.query(Article)
                    .filter(Article.doc_id == doc_id)
                    .first()
                )
            if not article:
                continue

            hits.append(
                SearchHit(
                    article_id=article.id,
                    title=article.title,
                    url=article.url,
                    score=score,
                    chunk_no=chunk_no,
                    snippet=content[:400],
                )
            )

        return hits
