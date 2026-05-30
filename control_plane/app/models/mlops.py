import uuid
from datetime import datetime

import sqlalchemy as sa
from app.core.time import utc_now
from app.db.base import Base
from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship


class MLDataset(Base):
    __tablename__ = "ml_datasets"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    is_production: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    is_approved: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    versions = relationship(
        "MLDatasetVersion",
        back_populates="dataset",
        cascade="all, delete-orphan",
    )


class MLDatasetVersion(Base):
    __tablename__ = "ml_dataset_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("ml_datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    checksum: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    provenance: Mapped[str] = mapped_column(sa.Text, nullable=False)
    redaction_status: Mapped[str] = mapped_column(sa.String(50), nullable=False, default="none")
    consent_metadata: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )

    dataset = relationship("MLDataset", back_populates="versions")
    training_jobs = relationship("MLTrainingJob", back_populates="dataset_version")


class MLTrainingJob(Base):
    __tablename__ = "ml_training_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    model_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("ml_dataset_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(sa.String(100), nullable=False, default="mock")
    status: Mapped[str] = mapped_column(sa.String(50), nullable=False, default="queued")
    hyperparameters: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    logs: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    output_model_id: Mapped[str | None] = mapped_column(sa.String(255), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    dataset_version = relationship("MLDatasetVersion", back_populates="training_jobs")
    experiment_runs = relationship("MLExperimentRun", back_populates="training_job")


class MLExperiment(Base):
    __tablename__ = "ml_experiments"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )

    runs = relationship("MLExperimentRun", back_populates="experiment", cascade="all, delete-orphan")


class MLExperimentRun(Base):
    __tablename__ = "ml_experiment_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("ml_experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    training_job_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("ml_training_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    metrics: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    params: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    artifacts: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )

    experiment = relationship("MLExperiment", back_populates="runs")
    training_job = relationship("MLTrainingJob", back_populates="experiment_runs")
    eval_artifacts = relationship("MLEvalArtifact", back_populates="run", cascade="all, delete-orphan")


class MLModelLineage(Base):
    __tablename__ = "ml_model_lineage"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    model_id: Mapped[str] = mapped_column(sa.String(255), nullable=False, index=True)
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("ml_dataset_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    training_job_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("ml_training_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    experiment_run_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("ml_experiment_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )

    dataset_version = relationship("MLDatasetVersion")
    training_job = relationship("MLTrainingJob")
    experiment_run = relationship("MLExperimentRun")


class MLEvalArtifact(Base):
    __tablename__ = "ml_eval_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("ml_experiment_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    path: Mapped[str] = mapped_column(sa.String(512), nullable=False)
    redaction_policy: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    is_redacted: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    contains_sensitive_data: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )

    run = relationship("MLExperimentRun", back_populates="eval_artifacts")
