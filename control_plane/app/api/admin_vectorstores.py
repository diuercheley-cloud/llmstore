from app.core.config import get_settings
from app.services.runtime_dependencies import get_db_session
from app.services.auth import AdminRole, require_admin_role
from app.services.vectorstores.vectorstore_factory import VectorStoreFactory
from app.services.vectorstores.vectorstore_health import (
    get_all_vectorstores_health,
)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/vectorstores", tags=["admin_vectorstores"])
settings = get_settings()

@router.get("/health")
async def get_vectorstores_health(
    session: AsyncSession = Depends(get_db_session),
    _ = Depends(require_admin_role(AdminRole.READ))
):
    """
    Get health status of all vector store providers.
    """
    return await get_all_vectorstores_health(session)

@router.get("/provider")
async def get_current_provider(
    _ = Depends(require_admin_role(AdminRole.READ))
):
    """
    Get the currently configured vector store provider.
    """
    return {
        "provider": settings.vector_db_provider,
        "qdrant_enabled": settings.qdrant_enabled,
        "milvus_enabled": settings.milvus_enabled,
        "weaviate_enabled": settings.weaviate_enabled
    }

@router.post("/test")
async def test_vectorstore_connection(
    provider: str,
    session: AsyncSession = Depends(get_db_session),
    _ = Depends(require_admin_role(AdminRole.WRITE))
):
    """
    Test connection to a specific vector store provider.
    """
    try:
        store = VectorStoreFactory.get_instance(provider, session)
        health = await store.healthcheck()
        return health
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
