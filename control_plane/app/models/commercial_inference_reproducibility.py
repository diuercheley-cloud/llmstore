import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base


class CommercialInferenceReproducibilityRecord(Base):
    __tablename__ = "commercial_inference_reproducibility_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    client_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    model_alias: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    provider: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    backend_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    tokenizer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tokenizer_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    chat_template_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    prompt_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    request_payload_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    response_payload_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    top_p: Mapped[float | None] = mapped_column(Float, nullable=True)
    top_k: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_p: Mapped[float | None] = mapped_column(Float, nullable=True)
    repetition_penalty: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

    runtime_engine: Mapped[str | None] = mapped_column(String(128), nullable=True)
    runtime_engine_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model_manifest_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    model_checksum: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    runtime_config_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    replay_supported: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    replay_status: Mapped[str] = mapped_column(String(32), nullable=False, default="original", index=True)
    replay_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    replay_distance: Mapped[float | None] = mapped_column(Float, nullable=True)

    immutable_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    replayed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CommercialInferenceReplayEvent(Base):
    __tablename__ = "commercial_inference_replay_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reproducibility_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commercial_inference_reproducibility_records.id"),
        nullable=False,
        index=True,
    )
    replay_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    replay_result: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    replay_output_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    replay_runtime_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class CommercialInferenceRuntimeSnapshot(Base):
    __tablename__ = "commercial_inference_runtime_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    backend_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    runtime_engine: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    runtime_engine_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    model_manifest_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    runtime_config_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tokenizer_info_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    snapshot_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
