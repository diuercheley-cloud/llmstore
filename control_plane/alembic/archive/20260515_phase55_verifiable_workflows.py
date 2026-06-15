"""phase55_verifiable_workflows

Revision ID: 20260515_phase55
Revises: e72a4c1b6d3f
Create Date: 2026-05-15 18:30:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260515_phase55"
down_revision = "e72a4c1b6d3f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "commercial_workflow_definitions",
        sa.Column("workflow_family", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "commercial_workflow_definitions", sa.Column("dag_json", sa.JSON(), nullable=True)
    )
    op.add_column(
        "commercial_workflow_definitions",
        sa.Column("entry_stage", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "commercial_workflow_definitions",
        sa.Column("definition_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "commercial_workflow_definitions",
        sa.Column("immutable_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "commercial_workflow_definitions",
        sa.Column("policy_bundle_ref", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "commercial_workflow_definitions",
        sa.Column("offline_compatible", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "commercial_workflow_definitions", sa.Column("sovereign_ready", sa.Boolean(), nullable=True)
    )
    op.create_index(
        "ix_commercial_workflow_definitions_definition_hash",
        "commercial_workflow_definitions",
        ["definition_hash"],
        unique=False,
    )

    op.add_column(
        "commercial_workflow_executions",
        sa.Column("replay_of_execution_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "commercial_workflow_executions",
        sa.Column("request_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "commercial_workflow_executions",
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "commercial_workflow_executions",
        sa.Column("execution_mode", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "commercial_workflow_executions", sa.Column("dag_hash", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "commercial_workflow_executions",
        sa.Column("provenance_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "commercial_workflow_executions",
        sa.Column("ledger_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "commercial_workflow_executions",
        sa.Column("resume_token_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "commercial_workflow_executions",
        sa.Column("last_checkpoint_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "commercial_workflow_executions",
        sa.Column("policy_gate_status", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "commercial_workflow_executions",
        sa.Column("determinism_status", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "commercial_workflow_executions", sa.Column("drift_detected", sa.Boolean(), nullable=True)
    )
    op.add_column(
        "commercial_workflow_executions",
        sa.Column("offline_bundle_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "commercial_workflow_executions", sa.Column("paused_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "commercial_workflow_executions", sa.Column("metadata_json", sa.JSON(), nullable=True)
    )
    op.create_foreign_key(
        "fk_workflow_executions_replay_of_execution",
        "commercial_workflow_executions",
        "commercial_workflow_executions",
        ["replay_of_execution_id"],
        ["id"],
    )
    op.create_index(
        "ix_commercial_workflow_executions_request_id",
        "commercial_workflow_executions",
        ["request_id"],
        unique=False,
    )
    op.create_index(
        "ix_commercial_workflow_executions_tenant_id",
        "commercial_workflow_executions",
        ["tenant_id"],
        unique=False,
    )

    op.create_table(
        "commercial_workflow_stages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("execution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("definition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
        sa.Column("stage_key", sa.String(length=128), nullable=False),
        sa.Column("stage_name", sa.String(length=128), nullable=True),
        sa.Column("stage_type", sa.String(length=64), nullable=True),
        sa.Column("stage_order", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("dependencies_json", sa.JSON(), nullable=True),
        sa.Column("policy_gate_status", sa.String(length=32), nullable=True),
        sa.Column("policy_decision_json", sa.JSON(), nullable=True),
        sa.Column("planned_input_hash", sa.String(length=64), nullable=True),
        sa.Column("input_hash", sa.String(length=64), nullable=True),
        sa.Column("output_hash", sa.String(length=64), nullable=True),
        sa.Column("stage_hash", sa.String(length=64), nullable=True),
        sa.Column("previous_stage_hash", sa.String(length=64), nullable=True),
        sa.Column("lineage_hash", sa.String(length=64), nullable=True),
        sa.Column("checkpoint_hash", sa.String(length=64), nullable=True),
        sa.Column("receipt_hash", sa.String(length=64), nullable=True),
        sa.Column("runtime_snapshot_hash", sa.String(length=64), nullable=True),
        sa.Column("confidential_audit_hash", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("executed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["definition_id"], ["commercial_workflow_definitions.id"]),
        sa.ForeignKeyConstraint(["execution_id"], ["commercial_workflow_executions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_commercial_workflow_stages_execution_id",
        "commercial_workflow_stages",
        ["execution_id"],
        unique=False,
    )
    op.create_index(
        "ix_commercial_workflow_stages_definition_id",
        "commercial_workflow_stages",
        ["definition_id"],
        unique=False,
    )
    op.create_index(
        "ix_commercial_workflow_stages_tenant_id",
        "commercial_workflow_stages",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_commercial_workflow_stages_stage_key",
        "commercial_workflow_stages",
        ["stage_key"],
        unique=False,
    )

    op.add_column(
        "commercial_workflow_checkpoints",
        sa.Column("stage_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "commercial_workflow_checkpoints",
        sa.Column("stage_key", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "commercial_workflow_checkpoints",
        sa.Column("snapshot_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "commercial_workflow_checkpoints",
        sa.Column("previous_checkpoint_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "commercial_workflow_checkpoints",
        sa.Column("detached_signature", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "commercial_workflow_checkpoints",
        sa.Column("signature_algorithm", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "commercial_workflow_checkpoints",
        sa.Column("immutable_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "commercial_workflow_checkpoints",
        sa.Column("replay_nonce", sa.String(length=64), nullable=True),
    )
    op.create_foreign_key(
        "fk_workflow_checkpoints_stage",
        "commercial_workflow_checkpoints",
        "commercial_workflow_stages",
        ["stage_id"],
        ["id"],
    )
    op.create_index(
        "ix_commercial_workflow_checkpoints_execution_id",
        "commercial_workflow_checkpoints",
        ["execution_id"],
        unique=False,
    )
    op.create_index(
        "ix_commercial_workflow_checkpoints_stage_id",
        "commercial_workflow_checkpoints",
        ["stage_id"],
        unique=False,
    )
    op.create_index(
        "ix_commercial_workflow_checkpoints_stage_key",
        "commercial_workflow_checkpoints",
        ["stage_key"],
        unique=False,
    )

    op.create_table(
        "commercial_workflow_receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("execution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
        sa.Column("receipt_hash", sa.String(length=64), nullable=False),
        sa.Column("previous_receipt_hash", sa.String(length=64), nullable=True),
        sa.Column("root_stage_hash", sa.String(length=64), nullable=True),
        sa.Column("root_checkpoint_hash", sa.String(length=64), nullable=True),
        sa.Column("provenance_hash", sa.String(length=64), nullable=True),
        sa.Column("detached_signature", sa.String(length=255), nullable=True),
        sa.Column("signature_algorithm", sa.String(length=64), nullable=True),
        sa.Column("verification_status", sa.String(length=32), nullable=True),
        sa.Column("immutable_hash", sa.String(length=64), nullable=True),
        sa.Column("receipt_json", sa.JSON(), nullable=True),
        sa.Column("export_classification", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["execution_id"], ["commercial_workflow_executions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_commercial_workflow_receipts_execution_id",
        "commercial_workflow_receipts",
        ["execution_id"],
        unique=False,
    )
    op.create_index(
        "ix_commercial_workflow_receipts_tenant_id",
        "commercial_workflow_receipts",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_commercial_workflow_receipts_receipt_hash",
        "commercial_workflow_receipts",
        ["receipt_hash"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_commercial_workflow_receipts_receipt_hash", table_name="commercial_workflow_receipts"
    )
    op.drop_index(
        "ix_commercial_workflow_receipts_tenant_id", table_name="commercial_workflow_receipts"
    )
    op.drop_index(
        "ix_commercial_workflow_receipts_execution_id", table_name="commercial_workflow_receipts"
    )
    op.drop_table("commercial_workflow_receipts")

    op.drop_index(
        "ix_commercial_workflow_checkpoints_stage_key", table_name="commercial_workflow_checkpoints"
    )
    op.drop_index(
        "ix_commercial_workflow_checkpoints_stage_id", table_name="commercial_workflow_checkpoints"
    )
    op.drop_index(
        "ix_commercial_workflow_checkpoints_execution_id",
        table_name="commercial_workflow_checkpoints",
    )
    op.drop_constraint(
        "fk_workflow_checkpoints_stage", "commercial_workflow_checkpoints", type_="foreignkey"
    )
    op.drop_column("commercial_workflow_checkpoints", "replay_nonce")
    op.drop_column("commercial_workflow_checkpoints", "immutable_hash")
    op.drop_column("commercial_workflow_checkpoints", "signature_algorithm")
    op.drop_column("commercial_workflow_checkpoints", "detached_signature")
    op.drop_column("commercial_workflow_checkpoints", "previous_checkpoint_hash")
    op.drop_column("commercial_workflow_checkpoints", "snapshot_hash")
    op.drop_column("commercial_workflow_checkpoints", "stage_key")
    op.drop_column("commercial_workflow_checkpoints", "stage_id")

    op.drop_index(
        "ix_commercial_workflow_stages_stage_key", table_name="commercial_workflow_stages"
    )
    op.drop_index(
        "ix_commercial_workflow_stages_tenant_id", table_name="commercial_workflow_stages"
    )
    op.drop_index(
        "ix_commercial_workflow_stages_definition_id", table_name="commercial_workflow_stages"
    )
    op.drop_index(
        "ix_commercial_workflow_stages_execution_id", table_name="commercial_workflow_stages"
    )
    op.drop_table("commercial_workflow_stages")

    op.drop_index(
        "ix_commercial_workflow_executions_tenant_id", table_name="commercial_workflow_executions"
    )
    op.drop_index(
        "ix_commercial_workflow_executions_request_id", table_name="commercial_workflow_executions"
    )
    op.drop_constraint(
        "fk_workflow_executions_replay_of_execution",
        "commercial_workflow_executions",
        type_="foreignkey",
    )
    op.drop_column("commercial_workflow_executions", "metadata_json")
    op.drop_column("commercial_workflow_executions", "paused_at")
    op.drop_column("commercial_workflow_executions", "offline_bundle_hash")
    op.drop_column("commercial_workflow_executions", "drift_detected")
    op.drop_column("commercial_workflow_executions", "determinism_status")
    op.drop_column("commercial_workflow_executions", "policy_gate_status")
    op.drop_column("commercial_workflow_executions", "last_checkpoint_hash")
    op.drop_column("commercial_workflow_executions", "resume_token_hash")
    op.drop_column("commercial_workflow_executions", "ledger_hash")
    op.drop_column("commercial_workflow_executions", "provenance_hash")
    op.drop_column("commercial_workflow_executions", "dag_hash")
    op.drop_column("commercial_workflow_executions", "execution_mode")
    op.drop_column("commercial_workflow_executions", "tenant_id")
    op.drop_column("commercial_workflow_executions", "request_id")
    op.drop_column("commercial_workflow_executions", "replay_of_execution_id")

    op.drop_index(
        "ix_commercial_workflow_definitions_definition_hash",
        table_name="commercial_workflow_definitions",
    )
    op.drop_column("commercial_workflow_definitions", "sovereign_ready")
    op.drop_column("commercial_workflow_definitions", "offline_compatible")
    op.drop_column("commercial_workflow_definitions", "policy_bundle_ref")
    op.drop_column("commercial_workflow_definitions", "immutable_hash")
    op.drop_column("commercial_workflow_definitions", "definition_hash")
    op.drop_column("commercial_workflow_definitions", "entry_stage")
    op.drop_column("commercial_workflow_definitions", "dag_json")
    op.drop_column("commercial_workflow_definitions", "workflow_family")
