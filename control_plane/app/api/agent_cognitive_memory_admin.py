# Owner: agent-platform
from app.api.deps import get_db, require_admin
from app.core.config import Settings, get_settings
from app.models.agents import AgentMemoryItem
from app.services.agents.cognitive_memory.episodic_memory import EpisodicMemoryService
from app.services.agents.cognitive_memory.memory_explainability import MemoryExplainabilityService
from app.services.agents.cognitive_memory.memory_summarizer import MemorySummarizer
from app.services.agents.cognitive_memory.semantic_memory import SemanticMemoryService
from app.services.agents.cognitive_memory.working_memory import WorkingMemoryService
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/agents/memory", tags=["agent-cognitive-memory"])


class SummarizeRequest(BaseModel):
    texts: list[str]


class SearchRequest(BaseModel):
    tenant_id: str
    query: str
    limit: int = 10


@router.get("/cognitive")
async def get_cognitive_memory(
    tenant_id: str,
    agent_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: dict = Depends(require_admin),
):
    if not settings.agent_cognitive_memory_enabled:
        raise HTTPException(status_code=400, detail="Cognitive memory is disabled")
    episodic = await EpisodicMemoryService(db).list(tenant_id, agent_id=agent_id)
    working = []
    if agent_id:
        working = await WorkingMemoryService(db).active(tenant_id, agent_id)
    return {
        "episodic_count": len(episodic),
        "working_count": len(working),
    }


@router.post("/summarize")
async def summarize_memory(
    req: SummarizeRequest,
    settings: Settings = Depends(get_settings),
    _: dict = Depends(require_admin),
):
    if not settings.agent_cognitive_memory_enabled:
        raise HTTPException(status_code=400, detail="Cognitive memory is disabled")
    return {"summary": MemorySummarizer().summarize(req.texts)}


@router.post("/search")
async def search_memory(
    req: SearchRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: dict = Depends(require_admin),
):
    if not settings.agent_cognitive_memory_enabled:
        raise HTTPException(status_code=400, detail="Cognitive memory is disabled")
    items = await SemanticMemoryService(db).search(req.tenant_id, req.query, req.limit)
    return [{"id": str(item.id), "summary": item.summary, "memory_type": item.memory_type} for item in items]


@router.get("/explain/{memory_id}")
async def explain_memory(
    memory_id: str,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: dict = Depends(require_admin),
):
    if not settings.agent_cognitive_memory_enabled:
        raise HTTPException(status_code=400, detail="Cognitive memory is disabled")
    item = await db.get(AgentMemoryItem, memory_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    return MemoryExplainabilityService().build(item, "matched semantic search or episodic recall")
