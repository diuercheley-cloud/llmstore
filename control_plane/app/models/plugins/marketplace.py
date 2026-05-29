import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, String, DateTime, JSON, Boolean, Integer, ForeignKey, Float, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.core.time import utc_now

JSON_DOCUMENT = JSON().with_variant(JSONB(astext_type=Text()), "postgresql")

class PluginMarketplaceEntry(Base):
    __tablename__ = "plugin_marketplace_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    license: Mapped[str] = mapped_column(String(128), nullable=False)
    plugin_type: Mapped[str] = mapped_column(String(64), nullable=False) # provider_adapter, billing_adapter, etc.
    official: Mapped[bool] = mapped_column(Boolean, default=False)
    avg_rating: Mapped[float] = mapped_column(Float, default=0.0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

class PluginVersion(Base):
    __tablename__ = "plugin_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plugin_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("plugin_marketplace_entries.id"), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    release_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    download_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    manifest_json: Mapped[dict] = mapped_column(JSON_DOCUMENT, nullable=False)
    min_platform_version: Mapped[str] = mapped_column(String(64), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class PluginInstall(Base):
    __tablename__ = "plugin_installs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plugin_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("plugin_marketplace_entries.id"), nullable=False, index=True)
    current_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("plugin_versions.id"), nullable=False)
    install_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="installed") # installed, enabled, disabled, error
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    config_json: Mapped[dict] = mapped_column(JSON_DOCUMENT, default={})
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

class PluginPermission(Base):
    __tablename__ = "plugin_permissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plugin_install_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("plugin_installs.id"), nullable=False, index=True)
    permission_name: Mapped[str] = mapped_column(String(255), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, default=False)
    
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

class PluginTrustReport(Base):
    __tablename__ = "plugin_trust_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plugin_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("plugin_versions.id"), nullable=False, index=True)
    scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    vulnerabilities_found: Mapped[int] = mapped_column(Integer, default=0)
    trust_score: Mapped[float] = mapped_column(Float, default=1.0) # 0.0 to 1.0
    report_details: Mapped[dict] = mapped_column(JSON_DOCUMENT, default={})
    is_signed: Mapped[bool] = mapped_column(Boolean, default=False)
    signer_identity: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

class PluginReview(Base):
    __tablename__ = "plugin_reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plugin_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("plugin_marketplace_entries.id"), nullable=False, index=True)
    admin_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("admin_users.id"), nullable=True, index=True)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    review_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

class PluginExecutionRecord(Base):
    __tablename__ = "plugin_execution_records"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plugin_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False)
    invocation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON_DOCUMENT, default={})
    status: Mapped[str] = mapped_column(String(64), nullable=False) # success, error
    output: Mapped[Optional[dict]] = mapped_column(JSON_DOCUMENT, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

class PluginPermissionGrant(Base):
    __tablename__ = "plugin_permission_grants"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plugin_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False)
    permission_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_granted: Mapped[bool] = mapped_column(Boolean, default=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class PluginVerificationResult(Base):
    __tablename__ = "plugin_verification_results"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plugin_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    checksum_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    signature_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    manifest_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    details: Mapped[dict] = mapped_column(JSON_DOCUMENT, default={})

class PluginDryRunResult(Base):
    __tablename__ = "plugin_dry_run_results"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plugin_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    is_success: Mapped[bool] = mapped_column(Boolean, default=False)
    sandbox_type: Mapped[str] = mapped_column(String(64), nullable=False)
    output: Mapped[Optional[dict]] = mapped_column(JSON_DOCUMENT, nullable=True)
    logs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

class PluginExecutionReceipt(Base):
    __tablename__ = "plugin_execution_receipts"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("plugin_runtime_executions.id"), nullable=False, index=True)
    receipt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    signature: Mapped[str] = mapped_column(String(512), nullable=False)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON_DOCUMENT, nullable=False)
