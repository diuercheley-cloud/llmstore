from typing import Optional

from app.services.runtime_dependencies import get_db_session
from app.services.agents.tools.web_search_tool import WebSearchToolAdapter
from app.services.agents.web_search.search_audit import SearchAuditService
from app.services.agents.web_search.search_cache import SearchCacheService
from app.services.auth import require_admin
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["web-search-admin"])


class WebSearchTestRequest(BaseModel):
    query: str
    limit: Optional[int] = 5
    provider: Optional[str] = "local_tavily_real"


@router.post("/admin/agents/tools/web-search/test")
async def test_web_search(
    req: WebSearchTestRequest,
    db: AsyncSession = Depends(get_db_session),
    admin=Depends(require_admin),
):
    adapter = WebSearchToolAdapter()
    try:
        result = await adapter.execute(
            query=req.query,
            limit=req.limit,
            provider=req.provider,
            tenant_id="admin_test_tenant",
            agent_id=None,
            run_id=None,
            db=db,
        )
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/agents/web-search/audit")
async def get_search_audit(
    db: AsyncSession = Depends(get_db_session),
    admin=Depends(require_admin),
):
    service = SearchAuditService()
    try:
        trail = await service.get_audit_trail(db)
        return trail
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/agents/web-search/cache")
async def get_search_cache(
    db: AsyncSession = Depends(get_db_session),
    admin=Depends(require_admin),
):
    service = SearchCacheService()
    try:
        entries = await service.list_cache_entries(db)
        return entries
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
