import asyncio
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmbeddingService:
    def __init__(self):
        self.enabled = getattr(settings, "rag_enabled", True)
        self.provider = getattr(settings, "rag_embedding_provider", "local")
        self.model_name = getattr(
            settings, "rag_embedding_model", "sentence-transformers/all-MiniLM-L6-v2"
        )
        self._model = None
        self._lock = asyncio.Lock()

    async def _get_model(self):
        if self._model is not None:
            return self._model

        async with self._lock:
            # Double check after acquiring lock
            if self._model is not None:
                return self._model

            if self.provider == "local":
                try:
                    from sentence_transformers import SentenceTransformer

                    logger.info(f"Lazy loading embedding model: {self.model_name}")
                    # Run model loading in a thread to not block event loop
                    loop = asyncio.get_event_loop()
                    self._model = await loop.run_in_executor(
                        None, SentenceTransformer, self.model_name
                    )
                    logger.info(f"Embedding model {self.model_name} loaded successfully")
                except Exception as e:
                    logger.error(f"Failed to load embedding model {self.model_name}: {e}")
                    raise RuntimeError(f"Embedding model load failure: {e}")
            else:
                raise ValueError(f"Unsupported embedding provider: {self.provider}")
        return self._model

    async def embed_text(self, text: str) -> list[float]:
        if not self.enabled:
            raise RuntimeError("RAG/Embeddings are disabled")

        model = await self._get_model()
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(None, model.encode, [text])
        return embeddings[0].tolist()

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not self.enabled:
            raise RuntimeError("RAG/Embeddings are disabled")
        if not texts:
            return []

        model = await self._get_model()
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(None, model.encode, texts)
        return embeddings.tolist()


_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
