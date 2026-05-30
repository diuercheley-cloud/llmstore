import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from .base import VectorStoreBase
from .pgvector_store import PGVectorStore
from .qdrant_store import QdrantStore
from .milvus_store import MilvusStore
from .weaviate_store import WeaviateStore

logger = logging.getLogger(__name__)
settings = get_settings()

class VectorStoreFactory:
    @staticmethod
    def get_instance(provider: Optional[str] = None, session: Optional[AsyncSession] = None) -> VectorStoreBase:
        provider = provider or settings.vector_db_provider
        
        if provider == "pgvector":
            if session is None:
                raise ValueError("pgvector provider requires an active DB session")
            return PGVectorStore(session)
        
        if provider == "qdrant":
            if not settings.qdrant_enabled:
                logger.warning("Qdrant provider requested but QDRANT_ENABLED is false")
            return QdrantStore()
            
        if provider == "milvus":
            if not settings.milvus_enabled:
                logger.warning("Milvus provider requested but MILVUS_ENABLED is false")
            return MilvusStore()
            
        if provider == "weaviate":
            if not settings.weaviate_enabled:
                logger.warning("Weaviate provider requested but WEAVIATE_ENABLED is false")
            return WeaviateStore()
            
        raise ValueError(f"Unsupported vector store provider: {provider}")
