import uuid
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Dict, List, Optional

from app.db.base import Base
from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class EvalDataset(Base):
    __tablename__ = "eval_datasets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
    
    cases = relationship("EvalCase", back_populates="dataset", cascade="all, delete-orphan")


class EvalCase(Base):
    __tablename__ = "eval_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("eval_datasets.id"), nullable=False)
    
    input_data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    expected_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expected_behavior: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scoring_rubric: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    
    dataset = relationship("EvalDataset", back_populates="cases")


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("eval_datasets.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    
    status: Mapped[str] = mapped_column(String(32), default="pending")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    results = relationship("EvalResult", back_populates="run", cascade="all, delete-orphan")


class EvalResult(Base):
    __tablename__ = "eval_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("eval_runs.id"), nullable=False)
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("eval_cases.id"), nullable=False)
    
    actual_output: Mapped[Text] = mapped_column(Text, nullable=True)
    scores: Mapped[Dict[str, float]] = mapped_column(JSON, nullable=False) # correctness, safety, etc.
    total_score: Mapped[float] = mapped_column(Float, default=0.0)
    
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    
    policy_compliance: Mapped[bool] = mapped_column(Boolean, default=True)
    audit_log: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    run = relationship("EvalRun", back_populates="results")


class ArenaMatch(Base):
    __tablename__ = "arena_matches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("eval_datasets.id"), nullable=False)
    
    model_a: Mapped[str] = mapped_column(String(128), nullable=False)
    model_b: Mapped[str] = mapped_column(String(128), nullable=False)
    
    winner: Mapped[Optional[str]] = mapped_column(String(128), nullable=True) # model_a, model_b, or draw
    score_a: Mapped[float] = mapped_column(Float, default=0.0)
    score_b: Mapped[float] = mapped_column(Float, default=0.0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EloRating(Base):
    __tablename__ = "elo_ratings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True) # model or agent name
    rating: Mapped[float] = mapped_column(Float, default=1200.0, nullable=False)
    matches_played: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class RedTeamFinding(Base):
    __tablename__ = "red_team_findings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("eval_runs.id"), nullable=False)
    
    finding_type: Mapped[str] = mapped_column(String(64), nullable=False) # injection, jailbreak, etc.
    severity: Mapped[str] = mapped_column(String(32), default="medium")
    description: Mapped[Text] = mapped_column(Text, nullable=False)
    payload_used: Mapped[Text] = mapped_column(Text, nullable=True)
    evidence: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
