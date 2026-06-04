# Owner: platform-ops
# Owner: platform-ops
import uuid
from datetime import datetime
from typing import Optional

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

JSON_DOCUMENT = JSON().with_variant(JSONB(astext_type=Text()), "postgresql")

class AgentCapabilityCatalogEntry(Base):
    __tablename__ = "agent_capability_catalog_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False) # connector, mcp, plugin
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    
    manifest: Mapped[dict] = mapped_column(JSON_DOCUMENT, nullable=False)
    permissions: Mapped[list] = mapped_column(JSON_DOCUMENT, nullable=False, default=[])
    
    risk_level: Mapped[str] = mapped_column(String(32), default="medium")
    side_effect_level: Mapped[str] = mapped_column(String(32), default="none") # none, read, write, destructive
    
    status: Mapped[str] = mapped_column(String(32), default="draft") # draft, pending_review, approved, disabled
    support_level: Mapped[str] = mapped_column(String(32), default="beta") # experimental, beta, production
    
    docs_url: Mapped[Optional[str]] = mapped_column(String(1024))
    test_status: Mapped[Optional[str]] = mapped_column(String(32))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class ConnectorCatalogEntry(Base):
    __tablename__ = "connector_catalog_entries"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    catalog_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_capability_catalog_entries.id"), nullable=False)
    connector_type: Mapped[str] = mapped_column(String(64), nullable=False)
    credential_references: Mapped[dict] = mapped_column(JSON_DOCUMENT, nullable=True) # References to secrets manager


class MCPCatalogEntry(Base):
    __tablename__ = "mcp_catalog_entries"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    catalog_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_capability_catalog_entries.id"), nullable=False)
    mcp_endpoint: Mapped[str] = mapped_column(String(1024), nullable=False)
    tools_sanitized: Mapped[bool] = mapped_column(Boolean, default=True)


class PluginCatalogEntry(Base):
    __tablename__ = "plugin_catalog_entries"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    catalog_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_capability_catalog_entries.id"), nullable=False)
    runtime_type: Mapped[str] = mapped_column(String(32), default="python")
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    is_signed: Mapped[bool] = mapped_column(Boolean, default=False)


class PluginSignature(Base):
    __tablename__ = "plugin_signatures"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plugin_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("plugin_catalog_entries.id"), nullable=False)
    signer_identity: Mapped[str] = mapped_column(String(255), nullable=False)
    signature_data: Mapped[str] = mapped_column(Text, nullable=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class PluginTrustReportGov(Base):
    __tablename__ = "gov_plugin_trust_reports"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    catalog_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_capability_catalog_entries.id"), nullable=False)
    scan_status: Mapped[str] = mapped_column(String(32), default="pending")
    trust_score: Mapped[float] = mapped_column(Float, default=0.0)
    findings: Mapped[dict] = mapped_column(JSON_DOCUMENT, default={})
    last_scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PluginInstallEvent(Base):
    __tablename__ = "plugin_install_events"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    catalog_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_capability_catalog_entries.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(32)) # install, uninstall, upgrade, rollback
    status: Mapped[str] = mapped_column(String(32))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CapabilityApprovalEvent(Base):
    __tablename__ = "capability_approval_events"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    catalog_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_capability_catalog_entries.id"), nullable=False)
    approver_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    previous_status: Mapped[str] = mapped_column(String(32))
    new_status: Mapped[str] = mapped_column(String(32))
    comment: Mapped[Optional[str]] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
