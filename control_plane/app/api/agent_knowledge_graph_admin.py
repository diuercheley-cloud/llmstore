# Owner: agent-platform
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin
from app.core.config import Settings, get_settings
from app.services.agents.knowledge_graph.graph_extractor import graph_extractor
from app.services.agents.knowledge_graph.graph_models import Entity, GraphQueryRequest, GraphQueryResult, Relation
from app.services.agents.knowledge_graph.graph_policy import graph_policy
from app.services.agents.knowledge_graph.graph_rag import GraphRAG
from app.services.agents.knowledge_graph.graph_store import GraphStore

admin_router = APIRouter(prefix="/admin/agents/knowledge-graph", tags=["agent-knowledge-graph-admin"])
public_router = APIRouter(prefix="/agents", tags=["agent-knowledge-graph"])


class ExtractRequest(BaseModel):
    tenant_id: str
    text: str
    source_uri: str = "inline://extract"


class AgentQueryRequest(BaseModel):
    tenant_id: str = "default"
    text: str


@admin_router.post("/extract")
async def extract_knowledge(
    req: ExtractRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: dict = Depends(require_admin),
) -> dict[str, Any]:
    if not settings.agent_knowledge_graph_enabled:
        raise HTTPException(status_code=400, detail="Knowledge graph is not enabled")

    store = GraphStore(db)
    source_id = await store.create_source(req.tenant_id, req.source_uri, req.text)
    entities, relations = graph_extractor.extract_entities_and_relations(req.text, tenant_id=req.tenant_id, source_id=str(source_id))
    created_entities: list[Entity] = []
    entity_id_map: dict[str, str] = {}
    created_relations: list[Relation] = []
    for entity in entities:
        persisted = await store.add_entity(req.tenant_id, entity.name, entity.type, source_id=source_id)
        created_entities.append(persisted)
        entity_id_map[entity.id] = persisted.id
    for relation in relations:
        graph_policy.check_provenance(relation)
        created_relations.append(
            await store.add_relation(
                req.tenant_id,
                entity_id_map.get(relation.source_entity_id, relation.source_entity_id),
                entity_id_map.get(relation.target_entity_id, relation.target_entity_id),
                relation.type,
                relation.provenance,
                source_id=source_id,
            )
        )
    return {
        "entities_count": len(created_entities),
        "relations_count": len(created_relations),
        "source_id": str(source_id),
    }


@admin_router.get("/entities", response_model=list[Entity])
async def list_entities(
    tenant_id: str,
    entity_name: str | None = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: dict = Depends(require_admin),
):
    if not settings.agent_knowledge_graph_enabled:
        raise HTTPException(status_code=400, detail="Knowledge graph is not enabled")
    return await GraphStore(db).get_entities(tenant_id, entity_name=entity_name)


@admin_router.get("/relations", response_model=list[Relation])
async def list_relations(
    tenant_id: str,
    entity_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: dict = Depends(require_admin),
):
    if not settings.agent_knowledge_graph_enabled:
        raise HTTPException(status_code=400, detail="Knowledge graph is not enabled")
    return await GraphStore(db).get_relations(tenant_id, entity_id=entity_id)


@admin_router.post("/query", response_model=GraphQueryResult)
async def query_knowledge(
    req: GraphQueryRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: dict = Depends(require_admin),
):
    if not settings.agent_knowledge_graph_enabled:
        raise HTTPException(status_code=400, detail="Knowledge graph is not enabled")
    return await GraphStore(db).query(req)


@public_router.post("/{agent_id}/knowledge/query", response_model=GraphQueryResult)
async def agent_query_knowledge(
    agent_id: uuid.UUID,
    req: AgentQueryRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if not settings.agent_knowledge_graph_enabled:
        raise HTTPException(status_code=400, detail="Knowledge graph is not enabled")
    return await GraphRAG(db).query(req.tenant_id, req.text)
