import asyncio
import hashlib
import json
import logging
from typing import List, Optional

from app.core.config import get_settings
from app.services.rag_enterprise.schemas import EmbeddingRecord

logger = logging.getLogger(__name__)
settings = get_settings()

_embedding_records: List[EmbeddingRecord] = []


def _get_mock_embedding(text: str, dimensions: int = 384) -> List[float]:
    h = hashlib.sha256(text.encode("utf-8")).digest()
    vals = [(h[i % len(h)] / 255.0) * 2 - 1 for i in range(dimensions)]
    norm = sum(v * v for v in vals) ** 0.5
    if norm > 0:
        vals = [v / norm for v in vals]
    return vals


class EnterpriseEmbeddingService:
    def __init__(self):
        self.provider = settings.rag_embedding_provider
        self.model_name = settings.rag_embedding_model
        self._model = None
        self._lock = asyncio.Lock()
        self._records: List[EmbeddingRecord] = []

    @property
    def records(self) -> List[EmbeddingRecord]:
        return list(self._records)

    async def _get_model(self):
        if self._model is not None:
            return self._model

        async with self._lock:
            if self._model is not None:
                return self._model

            if self.provider == "local":
                try:
                    from sentence_transformers import SentenceTransformer
                    logger.info(f"Lazy loading embedding model: {self.model_name}")
                    loop = asyncio.get_event_loop()
                    self._model = await loop.run_in_executor(None, SentenceTransformer, self.model_name)
                    logger.info(f"Embedding model {self.model_name} loaded successfully")
                except Exception as e:
                    logger.warning(f"Failed to load embedding model {self.model_name}: {e}")
                    logger.info("Falling back to mock embeddings")
                    self.provider = "mock"
                    return None
            else:
                logger.info(f"Using mock embeddings (provider={self.provider})")
                return None
        return self._model

    async def embed_text(self, text: str, cloud_allowed: bool = False) -> List[float]:
        if not cloud_allowed:
            return _get_mock_embedding(text)

        model = await self._get_model()
        if model is None:
            emb = _get_mock_embedding(text)
            self._record_embedding("mock", "sha256-mock", 0.0, len(emb))
            return emb

        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(None, model.encode, [text])
        emb = embeddings[0].tolist()
        self._record_embedding(self.provider, self.model_name, 0.0, len(emb))
        return emb

    async def embed_batch(self, texts: List[str], cloud_allowed: bool = False) -> List[List[float]]:
        if not texts:
            return []

        if not cloud_allowed:
            embeddings = [_get_mock_embedding(t) for t in texts]
            if embeddings:
                self._record_embedding("mock", "sha256-mock", 0.0, len(embeddings[0]))
            return embeddings

        model = await self._get_model()
        if model is None:
            embeddings = [_get_mock_embedding(t) for t in texts]
            if embeddings:
                self._record_embedding("mock", "sha256-mock", 0.0, len(embeddings[0]))
            return embeddings

        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(None, model.encode, texts)
        self._record_embedding(self.provider, self.model_name, 0.0, embeddings.shape[1])
        return embeddings.tolist()

    def _record_embedding(self, provider: str, model: str, cost: float, dimensions: int):
        rec = EmbeddingRecord(provider=provider, model=model, cost=cost, dimensions=dimensions)
        self._records.append(rec)

    def get_records(self) -> List[EmbeddingRecord]:
        return self._records

    def clear_records(self):
        self._records.clear()


_enterprise_embedding_service = None


def get_enterprise_embedding_service() -> EnterpriseEmbeddingService:
    global _enterprise_embedding_service
    if _enterprise_embedding_service is None:
        _enterprise_embedding_service = EnterpriseEmbeddingService()
    return _enterprise_embedding_service
