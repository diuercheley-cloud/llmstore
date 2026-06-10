import uuid
from datetime import datetime

from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class CommercialInferenceReceipt(Base):
    __tablename__ = "commercial_inference_receipts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    reproducibility_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_inference_reproducibility_records.id"),
        nullable=True,
        index=True,
    )
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    client_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    backend_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    provider: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    prompt_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    response_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    request_payload_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    response_payload_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    runtime_snapshot_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    routing_decision_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    receipt_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    previous_receipt_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    immutable_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    detached_signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    signature_algorithm: Mapped[str | None] = mapped_column(String(64), nullable=True)

    timestamp_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="local")
    timestamp_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    tamper_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class CommercialInferenceReceiptLedgerEvent(Base):
    __tablename__ = "commercial_inference_receipt_ledger_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    receipt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_inference_receipts.id"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    immutable_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class CommercialInferenceReceiptVerificationReport(Base):
    __tablename__ = "commercial_inference_receipt_verification_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    receipt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_inference_receipts.id"),
        nullable=False,
        index=True,
    )
    verification_result: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    chain_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    signature_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    timestamp_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    runtime_match: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    replay_match: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    drift_detected: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    report_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
