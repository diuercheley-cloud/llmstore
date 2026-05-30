import asyncio
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from .vectorstore_factory import VectorStoreFactory

async def get_all_vectorstores_health(session: AsyncSession) -> List[Dict[str, Any]]:
    """
    Check the health of all supported vector stores.
    """
    health_checks = []
    providers = ["pgvector", "qdrant", "milvus", "weaviate"]
    
    for provider in providers:
        try:
            store = VectorStoreFactory.get_instance(provider, session)
            health = await store.healthcheck()
            health_checks.append(health)
        except Exception as e:
            health_checks.append({
                "provider": provider,
                "status": "error",
                "error": str(e)
            })
            
    return health_checks

async def get_current_vectorstore_health(session: AsyncSession) -> Dict[str, Any]:
    """
    Check the health of the currently configured vector store.
    """
    try:
        store = VectorStoreFactory.get_instance(session=session)
        return await store.healthcheck()
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
