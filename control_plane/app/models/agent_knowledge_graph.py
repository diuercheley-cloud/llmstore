# Owner: agent-platform
import uuid
from datetime import datetime
from typing import Any, Dict

from app.db.base import Base
from sqlalchemy import JSON, UUID, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship


class AgentKGEntity(Base):
    __tablename__ = "agent_kg_entities"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    metadata_: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sources: Mapped[list["AgentKGSource"]] = relationship("AgentKGSource", secondary="agent_kg_entity_sources", back_populates="entities")

    __table_args__ = (
        Index('ix_agent_kg_entities_tenant_type_name', 'tenant_id', 'type', 'name'),
    )

class AgentKGRelation(Base):
    __tablename__ = "agent_kg_relations"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    source_entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_kg_entities.id", ondelete="CASCADE"), nullable=False)
    target_entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_kg_entities.id", ondelete="CASCADE"), nullable=False)
    relation_type: Mapped[str] = mapped_column(String, nullable=False)
    source_provenance: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    source_entity: Mapped["AgentKGEntity"] = relationship("AgentKGEntity", foreign_keys=[source_entity_id])
    target_entity: Mapped["AgentKGEntity"] = relationship("AgentKGEntity", foreign_keys=[target_entity_id])
    
    __table_args__ = (
        Index('ix_agent_kg_relations_tenant_source', 'tenant_id', 'source_entity_id'),
        Index('ix_agent_kg_relations_tenant_target', 'tenant_id', 'target_entity_id'),
    )

class AgentKGSource(Base):
    __tablename__ = "agent_kg_sources"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    uri: Mapped[str] = mapped_column(String, nullable=False)
    content_hash: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    entities: Mapped[list["AgentKGEntity"]] = relationship("AgentKGEntity", secondary="agent_kg_entity_sources", back_populates="sources")
    
class AgentKGEntitySource(Base):
    __tablename__ = "agent_kg_entity_sources"
    
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_kg_entities.id", ondelete="CASCADE"), primary_key=True)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_kg_sources.id", ondelete="CASCADE"), primary_key=True)

class AgentKGExtractionRun(Base):
    __tablename__ = "agent_kg_extraction_runs"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    document_id: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

class AgentKGQueryEvent(Base):
    __tablename__ = "agent_kg_query_events"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    query: Mapped[str] = mapped_column(String, nullable=False)
    execution_time_ms: Mapped[float] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
