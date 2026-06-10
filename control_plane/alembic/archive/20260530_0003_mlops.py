"""Add MLOps and Fine-tuning tables

Revision ID: 20260530_0003
Revises: 20260530_0002
Create Date: 2026-05-30 09:46:00.000000

"""
from typing import Optional, Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '20260530_0003'
down_revision: Optional[str] = '20260530_0001'  # Wait, is it 20260530_0002? Let's check: Yes, 20260530_0002.
down_revision = '20260530_0002'
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def upgrade() -> None:
    # 1. Create ml_datasets
    op.create_table(
        'ml_datasets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_production', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('is_approved', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_ml_datasets_created_at', 'ml_datasets', ['created_at'])

    # 2. Create ml_dataset_versions
    op.create_table(
        'ml_dataset_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ml_datasets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version', sa.String(length=100), nullable=False),
        sa.Column('checksum', sa.String(length=255), nullable=False),
        sa.Column('provenance', sa.Text(), nullable=False),
        sa.Column('redaction_status', sa.String(length=50), nullable=False, server_default='none'),
        sa.Column('consent_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_ml_dataset_versions_dataset_id', 'ml_dataset_versions', ['dataset_id'])
    op.create_index('ix_ml_dataset_versions_created_at', 'ml_dataset_versions', ['created_at'])

    # 3. Create ml_training_jobs
    op.create_table(
        'ml_training_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('model_name', sa.String(length=255), nullable=False),
        sa.Column('dataset_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ml_dataset_versions.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('provider', sa.String(length=100), nullable=False, server_default='mock'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='queued'),
        sa.Column('hyperparameters', sa.JSON(), nullable=True),
        sa.Column('logs', sa.Text(), nullable=True),
        sa.Column('output_model_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_ml_training_jobs_dataset_version_id', 'ml_training_jobs', ['dataset_version_id'])
    op.create_index('ix_ml_training_jobs_output_model_id', 'ml_training_jobs', ['output_model_id'])
    op.create_index('ix_ml_training_jobs_created_at', 'ml_training_jobs', ['created_at'])

    # 4. Create ml_experiments
    op.create_table(
        'ml_experiments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_ml_experiments_created_at', 'ml_experiments', ['created_at'])

    # 5. Create ml_experiment_runs
    op.create_table(
        'ml_experiment_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('experiment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ml_experiments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('training_job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ml_training_jobs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('metrics', sa.JSON(), nullable=True),
        sa.Column('params', sa.JSON(), nullable=True),
        sa.Column('artifacts', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_ml_experiment_runs_experiment_id', 'ml_experiment_runs', ['experiment_id'])
    op.create_index('ix_ml_experiment_runs_training_job_id', 'ml_experiment_runs', ['training_job_id'])
    op.create_index('ix_ml_experiment_runs_created_at', 'ml_experiment_runs', ['created_at'])

    # 6. Create ml_model_lineage
    op.create_table(
        'ml_model_lineage',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('model_id', sa.String(length=255), nullable=False),
        sa.Column('dataset_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ml_dataset_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('training_job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ml_training_jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('experiment_run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ml_experiment_runs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_ml_model_lineage_model_id', 'ml_model_lineage', ['model_id'])
    op.create_index('ix_ml_model_lineage_dataset_version_id', 'ml_model_lineage', ['dataset_version_id'])
    op.create_index('ix_ml_model_lineage_training_job_id', 'ml_model_lineage', ['training_job_id'])
    op.create_index('ix_ml_model_lineage_experiment_run_id', 'ml_model_lineage', ['experiment_run_id'])
    op.create_index('ix_ml_model_lineage_created_at', 'ml_model_lineage', ['created_at'])

    # 7. Create ml_eval_artifacts
    op.create_table(
        'ml_eval_artifacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ml_experiment_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('path', sa.String(length=512), nullable=False),
        sa.Column('redaction_policy', sa.String(length=100), nullable=True),
        sa.Column('is_redacted', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('contains_sensitive_data', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_ml_eval_artifacts_run_id', 'ml_eval_artifacts', ['run_id'])
    op.create_index('ix_ml_eval_artifacts_created_at', 'ml_eval_artifacts', ['created_at'])


def downgrade() -> None:
    op.drop_table('ml_eval_artifacts')
    op.drop_table('ml_model_lineage')
    op.drop_table('ml_experiment_runs')
    op.drop_table('ml_experiments')
    op.drop_table('ml_training_jobs')
    op.drop_table('ml_dataset_versions')
    op.drop_table('ml_datasets')
