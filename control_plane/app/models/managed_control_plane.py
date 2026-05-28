import uuid
from datetime import datetime
from typing import Optional, Any, List

from sqlalchemy import Column, String, DateTime, JSON, Boolean, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.core.time import utc_now

class ManagedOrganization(Base):
    __tablename__ = "managed_organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    
    status: Mapped[str] = mapped_column(String(32), default="active") # active, suspended, deleted
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    workspaces = relationship("ManagedWorkspace", back_populates="organization")

class ManagedWorkspace(Base):
    __tablename__ = "managed_workspaces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("managed_organizations.id"), nullable=False)
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    
    organization = relationship("ManagedOrganization", back_populates="workspaces")
    appliances = relationship("ManagedAppliance", back_populates="workspace")

class ManagedAppliance(Base):
    __tablename__ = "managed_appliances"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("managed_workspaces.id"), nullable=False)
    
    appliance_external_id: Mapped[str] = mapped_column(String(128), unique=True, index=True) # ID reported by the appliance
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    status: Mapped[str] = mapped_column(String(32), default="enrolled") # enrolled, online, offline, revoked
    
    # Sanitized status from heartbeats
    version: Mapped[Optional[str]] = mapped_column(String(64))
    health_status: Mapped[Optional[str]] = mapped_column(String(32)) # healthy, degraded, critical
    readiness: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    
    last_heartbeat_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    capacity_summary: Mapped[Optional[dict]] = mapped_column(JSON)
    enabled_providers: Mapped[Optional[list]] = mapped_column(JSON)
    available_models: Mapped[Optional[list]] = mapped_column(JSON)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    workspace = relationship("ManagedWorkspace", back_populates="appliances")
    heartbeats = relationship("ApplianceHeartbeat", back_populates="appliance")

class ApplianceEnrollment(Base):
    __tablename__ = "appliance_enrollments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("managed_workspaces.id"), nullable=False)
    
    enrollment_token: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    used_by_appliance_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("managed_appliances.id"))
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

class ApplianceHeartbeat(Base):
    __tablename__ = "appliance_heartbeats"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appliance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("managed_appliances.id"), nullable=False)
    
    # Payload details
    version: Mapped[str] = mapped_column(String(64))
    health_status: Mapped[str] = mapped_column(String(32))
    readiness: Mapped[bool] = mapped_column(Boolean)
    
    capacity_summary: Mapped[dict] = mapped_column(JSON)
    enabled_providers: Mapped[list] = mapped_column(JSON)
    available_models: Mapped[list] = mapped_column(JSON)
    
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    appliance = relationship("ManagedAppliance", back_populates="heartbeats")

class ManagedBillingAccount(Base):
    __tablename__ = "managed_billing_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("managed_organizations.id"), nullable=False)
    
    billing_email: Mapped[str] = mapped_column(String(255), nullable=False)
    payment_method: Mapped[Optional[str]] = mapped_column(String(64)) # stripe, bank_transfer, etc.
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    
    balance_cents: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

class ManagedSupportCase(Base):
    __tablename__ = "managed_support_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("managed_organizations.id"), nullable=False)
    workspace_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("managed_workspaces.id"))
    appliance_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("managed_appliances.id"))
    
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    status: Mapped[str] = mapped_column(String(32), default="open") # open, in_progress, resolved, closed
    priority: Mapped[str] = mapped_column(String(32), default="medium") # low, medium, high, urgent
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)
