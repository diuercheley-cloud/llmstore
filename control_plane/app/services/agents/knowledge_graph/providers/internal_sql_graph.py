# Owner: agent-platform
import uuid
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_knowledge_graph import (
    AgentKGEntity,
    AgentKGExtractionRun,
    AgentKGQueryEvent,
    AgentKGRelation,
    AgentKGSource,
)


class InternalSQLGraphProvider:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_source(self, tenant_id: str, uri: str, content_hash: str | None = None) -> AgentKGSource:
        source = AgentKGSource(tenant_id=tenant_id, uri=uri, content_hash=content_hash)
        self.db.add(source)
        await self.db.commit()
        await self.db.refresh(source)
        return source

    async def create_extraction_run(self, tenant_id: str, document_id: str | None = None) -> AgentKGExtractionRun:
        run = AgentKGExtractionRun(tenant_id=tenant_id, status="completed", document_id=document_id)
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)
        return run

    async def upsert_entity(
        self,
        tenant_id: str,
        name: str,
        entity_type: str,
        source_id: uuid.UUID | None = None,
        provenance: dict[str, Any] | None = None,
        confidence: float = 1.0,
        freshness: str = "fresh",
    ) -> AgentKGEntity:
        stmt = select(AgentKGEntity).where(
            AgentKGEntity.tenant_id == tenant_id,
            AgentKGEntity.name == name,
            AgentKGEntity.type == entity_type,
        )
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        metadata = {
            "source_id": str(source_id) if source_id else None,
            "provenance": provenance or {},
            "confidence": confidence,
            "freshness": freshness,
        }
        if existing:
            existing.metadata_ = metadata
            await self.db.commit()
            await self.db.refresh(existing)
            return existing
        entity = AgentKGEntity(
            tenant_id=tenant_id,
            name=name,
            type=entity_type,
            metadata_=metadata,
        )
        self.db.add(entity)
        await self.db.commit()
        await self.db.refresh(entity)
        return entity

    async def create_relation(
        self,
        tenant_id: str,
        source_entity_id: uuid.UUID,
        target_entity_id: uuid.UUID,
        relation_type: str,
        provenance: str,
        source_id: uuid.UUID | None = None,
        confidence: float = 1.0,
        freshness: str = "fresh",
    ) -> AgentKGRelation:
        relation = AgentKGRelation(
            tenant_id=tenant_id,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relation_type=relation_type,
            source_provenance=provenance,
        )
        relation.__dict__["metadata"] = {
            "source_id": str(source_id) if source_id else None,
            "confidence": confidence,
            "freshness": freshness,
        }
        self.db.add(relation)
        await self.db.commit()
        await self.db.refresh(relation)
        return relation

    async def list_entities(self, tenant_id: str, entity_name: str | None = None) -> list[AgentKGEntity]:
        stmt = select(AgentKGEntity).where(AgentKGEntity.tenant_id == tenant_id)
        if entity_name:
            stmt = stmt.where(AgentKGEntity.name.ilike(f"%{entity_name}%"))
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_relations(self, tenant_id: str, entity_id: uuid.UUID | None = None) -> list[AgentKGRelation]:
        stmt = select(AgentKGRelation).where(AgentKGRelation.tenant_id == tenant_id)
        if entity_id:
            stmt = stmt.where(
                or_(
                    AgentKGRelation.source_entity_id == entity_id,
                    AgentKGRelation.target_entity_id == entity_id,
                )
            )
        return list((await self.db.execute(stmt)).scalars().all())

    async def related_entities(self, tenant_id: str, entity_id: uuid.UUID) -> tuple[list[AgentKGEntity], list[AgentKGRelation]]:
        relations = await self.list_relations(tenant_id, entity_id=entity_id)
        entity_ids = {entity_id}
        entity_ids.update(relation.source_entity_id for relation in relations)
        entity_ids.update(relation.target_entity_id for relation in relations)
        stmt = select(AgentKGEntity).where(AgentKGEntity.tenant_id == tenant_id, AgentKGEntity.id.in_(entity_ids))
        entities = list((await self.db.execute(stmt)).scalars().all())
        return entities, relations

    async def record_query(self, tenant_id: str, query: str, execution_time_ms: float) -> AgentKGQueryEvent:
        event = AgentKGQueryEvent(tenant_id=tenant_id, query=query, execution_time_ms=execution_time_ms)
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event
