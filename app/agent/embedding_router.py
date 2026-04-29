from openai import OpenAI

from app.core.settings import get_settings


class EmbeddingRouter:
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)

    def embed_text(self, text: str) -> list[float]:
        response = self.client.embeddings.create(model=self.settings.embedding_model, input=text[:8000])
        return response.data[0].embedding
