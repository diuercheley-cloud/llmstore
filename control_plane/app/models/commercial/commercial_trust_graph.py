import uuid
from datetime import datetime, UTC

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class CommercialTrustGraphNode(Base):
    __tablename__ = "commercial_trust_graph_nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_type = Column(String(50), nullable=False)  # governance|runtime|workflow|receipt|federation
    external_id = Column(String(255), nullable=True, index=True)
    label = Column(String(255), nullable=False)
    metadata_json = Column(JSON, nullable=True)
    hash = Column(String(128), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

class CommercialTrustGraphEdge(Base):
    __tablename__ = "commercial_trust_graph_edges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_node_id = Column(UUID(as_uuid=True), ForeignKey("commercial_trust_graph_nodes.id"), nullable=False)
    target_node_id = Column(UUID(as_uuid=True), ForeignKey("commercial_trust_graph_nodes.id"), nullable=False)
    edge_type = Column(String(50), nullable=False)  # lineage|dependency|propagation|mapping
    metadata_json = Column(JSON, nullable=True)
    hash = Column(String(128), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
