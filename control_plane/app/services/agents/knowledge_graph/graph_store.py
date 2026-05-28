import hashlib
import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings

from .graph_models import Entity, GraphQueryRequest, GraphQueryResult, Relation
from .graph_policy import graph_policy
from .providers.falkordb_graph import FalkorDBGraphProvider
from .providers.internal_sql_graph import InternalSQLGraphProvider
from .providers.neo4j_graph import Neo4jGraphProvider


class GraphStore:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.provider = self._get_provider()

    def _get_provider(self):
        provider_name = self.settings.agent_kg_provider
        if provider_name == "neo4j":
            return Neo4jGraphProvider(enabled=self.settings.agent_kg_external_provider_enabled)
        if provider_name == "falkordb":
            return FalkorDBGraphProvider(enabled=self.settings.agent_kg_external_provider_enabled)
        return InternalSQLGraphProvider(self.db)

    async def add_entity(self, tenant_id: str, name: str, entity_type: str, source_id: uuid.UUID | None = None) -> Entity:
        graph_policy.require_writes_enabled(self.settings.agent_kg_write_enabled)
        record = await self.provider.upsert_entity(
            tenant_id=tenant_id,
            name=graph_policy.redact_secrets(name),
            entity_type=entity_type,
            source_id=source_id,
            provenance={"provider": self.settings.agent_kg_provider},
        )
        return self._entity_to_model(record)

    async def add_relation(
        self,
        tenant_id: str,
        src_id: str,
        tgt_id: str,
        relation_type: str,
        provenance: str,
        source_id: uuid.UUID | None = None,
    ) -> Relation:
        graph_policy.require_writes_enabled(self.settings.agent_kg_write_enabled)
        record = await self.provider.create_relation(
            tenant_id=tenant_id,
            source_entity_id=uuid.UUID(src_id),
            target_entity_id=uuid.UUID(tgt_id),
            relation_type=relation_type,
            provenance=provenance,
            source_id=source_id,
        )
        return self._relation_to_model(record)

    async def create_source(self, tenant_id: str, uri: str, raw_text: str) -> uuid.UUID:
        sanitized = graph_policy.redact_secrets(raw_text)
        source = await self.provider.create_source(
            tenant_id=tenant_id,
            uri=uri,
            content_hash=hashlib.sha256(sanitized.encode("utf-8")).hexdigest(),
        )
        return source.id

    async def get_entities(self, tenant_id: str, entity_name: str | None = None) -> list[Entity]:
        records = await self.provider.list_entities(tenant_id=tenant_id, entity_name=entity_name)
        return [self._entity_to_model(record) for record in records]

    async def get_relations(self, tenant_id: str, entity_id: str | None = None) -> list[Relation]:
        parsed_entity_id = uuid.UUID(entity_id) if entity_id else None
        records = await self.provider.list_relations(tenant_id=tenant_id, entity_id=parsed_entity_id)
        return [self._relation_to_model(record) for record in records]

    async def query(self, request: GraphQueryRequest) -> GraphQueryResult:
        graph_policy.validate_tenant(request.tenant_id)
        started_at = time.time()
        entities: list[Entity] = []
        relations: list[Relation] = []
        if request.query_type == "entity_search":
            entities = await self.get_entities(request.tenant_id, entity_name=request.entity_name or request.text)
        elif request.query_type in {"neighborhood", "dependencies", "owners"} and request.entity_id:
            records, record_relations = await self.provider.related_entities(request.tenant_id, uuid.UUID(request.entity_id))
            entities = [self._entity_to_model(record) for record in records]
            relations = [self._relation_to_model(record) for record in record_relations]
        elif request.query_type == "path" and request.entity_id and request.target_entity_id:
            records, record_relations = await self.provider.related_entities(request.tenant_id, uuid.UUID(request.entity_id))
            entities = [self._entity_to_model(record) for record in records if str(record.id) in {request.entity_id, request.target_entity_id}]
            relations = [self._relation_to_model(record) for record in record_relations]
        await self.provider.record_query(
            tenant_id=request.tenant_id,
            query=request.text or request.entity_name or request.query_type,
            execution_time_ms=(time.time() - started_at) * 1000,
        )
        provenance = [{"entity_id": entity.id, "source_id": entity.source_id, "provenance": entity.provenance} for entity in entities]
        return GraphQueryResult(entities=entities[: request.limit], relations=relations[: request.limit], provenance=provenance)

    def _entity_to_model(self, record) -> Entity:
        metadata = record.metadata_ or {}
        return Entity(
            id=str(record.id),
            tenant_id=record.tenant_id,
            source_id=metadata.get("source_id"),
            name=record.name,
            type=record.type,
            provenance=metadata.get("provenance", {}),
            confidence=metadata.get("confidence", 1.0),
            freshness=metadata.get("freshness"),
            created_at=record.created_at,
            updated_at=record.updated_at,
            metadata=metadata,
        )

    def _relation_to_model(self, record) -> Relation:
        metadata = getattr(record, "metadata", {}) or {}
        return Relation(
            id=str(record.id),
            tenant_id=record.tenant_id,
            source_id=metadata.get("source_id"),
            source_entity_id=str(record.source_entity_id),
            target_entity_id=str(record.target_entity_id),
            type=record.relation_type,
            provenance=record.source_provenance,
            confidence=metadata.get("confidence", 1.0),
            freshness=metadata.get("freshness"),
            created_at=record.created_at,
            updated_at=getattr(record, "updated_at", None),
            metadata=metadata,
        )
