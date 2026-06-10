import enum
import uuid
from datetime import datetime
from typing import Optional

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class CryptoProviderType(str, enum.Enum):
    LOCAL_KEYSTORE = "local_keystore"
    VAULT = "vault_placeholder"
    HSM = "hsm_placeholder"
    SOVEREIGN_OFFLINE = "sovereign_offline_store"

class CryptoOperationType(str, enum.Enum):
    ENCRYPT = "encrypt"
    DECRYPT = "decrypt"
    SIGN = "sign"
    VERIFY = "verify"

class KeyUsageStatus(str, enum.Enum):
    ACTIVE = "active"
    ROTATED = "rotated"
    REVOKED = "revoked"
    PENDING_ROTATION = "pending_rotation"


class CommercialKMSProvider(Base):
    __tablename__ = "commercial_kms_providers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_type: Mapped[CryptoProviderType] = mapped_column(String(50), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class CommercialKeyMaterial(Base):
    __tablename__ = "commercial_key_materials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("commercial_kms_providers.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True) # Null for system keys
    key_alias: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    key_type: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. RSA-2048, AES-256
    status: Mapped[KeyUsageStatus] = mapped_column(String(50), default=KeyUsageStatus.ACTIVE, nullable=False)
    # The actual key material should NOT be stored in plaintext. It's either a reference to Vault/HSM, or encrypted offline material
    encrypted_key_blob: Mapped[Optional[str]] = mapped_column(Text, nullable=True) 
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    provider: Mapped[CommercialKMSProvider] = relationship("CommercialKMSProvider")


class CommercialSigningProfile(Base):
    __tablename__ = "commercial_signing_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("commercial_key_materials.id", ondelete="RESTRICT"), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    key: Mapped[CommercialKeyMaterial] = relationship("CommercialKeyMaterial")


class CommercialCryptoOperation(Base):
    __tablename__ = "commercial_crypto_operations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("commercial_key_materials.id", ondelete="RESTRICT"), nullable=False)
    operation_type: Mapped[CryptoOperationType] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="success", nullable=False)
    audit_context: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class CommercialKeyRotationSchedule(Base):
    __tablename__ = "commercial_key_rotation_schedules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("commercial_key_materials.id", ondelete="CASCADE"), nullable=False)
    rotation_interval_days: Mapped[int] = mapped_column(nullable=False)
    next_rotation_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_rotated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    key: Mapped[CommercialKeyMaterial] = relationship("CommercialKeyMaterial")
