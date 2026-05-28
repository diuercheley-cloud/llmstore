import uuid
import hashlib
import json
from datetime import datetime
from sqlalchemy import String, DateTime, JSON, Boolean, Integer, Float, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.time import utc_now
from app.db.base import Base


def compute_deterministic_hash(*, fields: dict, version: str = "v1") -> str:
    raw = json.dumps(fields, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(f"{version}:{raw}".encode("utf-8")).hexdigest()


class FailureSignal(Base):
    __tablename__ = "operations_failure_signals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    signal_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_domain: Mapped[str] = mapped_column(String(64), nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    immutable_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class FailureForecast(Base):
    __tablename__ = "operations_failure_forecasts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    forecast_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    forecast_window_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    advisory_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deterministic_version: Mapped[str | None] = mapped_column(String(16), nullable=True)
    input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    immutable_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class FailureRiskAssessment(Base):
    __tablename__ = "operations_failure_risk_assessments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    forecast_id: Mapped[str | None] = mapped_column(String, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False, default="low")
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    advisory_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    immutable_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
