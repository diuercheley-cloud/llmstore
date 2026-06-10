"""Phase 48 Secure Tenant Data Clean-Room + Regulated RAG Vault

Revision ID: 20260515_0061
Revises: 20260515_0060
Create Date: 2026-05-15 08:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260515_0061"
down_revision = "20260515_0060"
branch_labels = None
depends_on = None


def _uuid_type():
    return postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "commercial_rag_vaults",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("client_id", _uuid_type(), nullable=True),
        sa.Column("vault_name", sa.String(length=255), nullable=False),
        sa.Column("vault_mode", sa.String(length=32), nullable=False),
        sa.Column("encryption_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("retrieval_mode", sa.String(length=32), nullable=False),
        sa.Column("retention_policy_seconds", sa.Integer(), nullable=True),
        sa.Column("immutable_audit_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_commercial_rag_vaults_client_id", "commercial_rag_vaults", ["client_id"])
    op.create_index("ix_commercial_rag_vaults_vault_mode", "commercial_rag_vaults", ["vault_mode"])

    op.create_table(
        "commercial_rag_documents",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("vault_id", _uuid_type(), nullable=False),
        sa.Column("document_hash", sa.String(length=128), nullable=False),
        sa.Column("document_title", sa.String(length=255), nullable=False),
        sa.Column("classification", sa.String(length=32), nullable=False),
        sa.Column("ingestion_status", sa.String(length=32), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("provenance_hash", sa.String(length=128), nullable=True),
        sa.Column("signed_manifest_hash", sa.String(length=128), nullable=True),
        sa.Column("legal_hold", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["vault_id"], ["commercial_rag_vaults.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_commercial_rag_documents_vault_id", "commercial_rag_documents", ["vault_id"])
    op.create_index("ix_commercial_rag_documents_document_hash", "commercial_rag_documents", ["document_hash"])
    op.create_index("ix_commercial_rag_documents_classification", "commercial_rag_documents", ["classification"])
    op.create_index("ix_commercial_rag_documents_ingestion_status", "commercial_rag_documents", ["ingestion_status"])

    op.create_table(
        "commercial_rag_chunks",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("document_id", _uuid_type(), nullable=False),
        sa.Column("chunk_hash", sa.String(length=128), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("embedding_hash", sa.String(length=128), nullable=True),
        sa.Column("acl_json", sa.JSON(), nullable=True),
        sa.Column("encrypted_payload", sa.Text(), nullable=True),
        sa.Column("poisoned_flag", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["commercial_rag_documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_commercial_rag_chunks_document_id", "commercial_rag_chunks", ["document_id"])
    op.create_index("ix_commercial_rag_chunks_chunk_hash", "commercial_rag_chunks", ["chunk_hash"])
    op.create_index("ix_commercial_rag_chunks_poisoned_flag", "commercial_rag_chunks", ["poisoned_flag"])

    op.create_table(
        "commercial_rag_access_policies",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("vault_id", _uuid_type(), nullable=False),
        sa.Column("policy_name", sa.String(length=255), nullable=False),
        sa.Column("policy_mode", sa.String(length=32), nullable=False),
        sa.Column("allow_cross_tenant", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("require_abac", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("require_signed_document", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("require_confidential_runtime", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("require_trusted_model", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("max_context_chunks", sa.Integer(), nullable=False, server_default=sa.text("20")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["vault_id"], ["commercial_rag_vaults.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_commercial_rag_access_policies_vault_id", "commercial_rag_access_policies", ["vault_id"])

    op.create_table(
        "commercial_rag_retrieval_audits",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("vault_id", _uuid_type(), nullable=False),
        sa.Column("client_id", _uuid_type(), nullable=True),
        sa.Column("request_hash", sa.String(length=128), nullable=False),
        sa.Column("retrieval_hash", sa.String(length=128), nullable=False),
        sa.Column("user_identity_hash", sa.String(length=128), nullable=True),
        sa.Column("retrieved_chunk_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("policy_result", sa.String(length=64), nullable=False),
        sa.Column("model_id", sa.String(length=255), nullable=True),
        sa.Column("immutable_hash", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["vault_id"], ["commercial_rag_vaults.id"]),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_commercial_rag_retrieval_audits_vault_id", "commercial_rag_retrieval_audits", ["vault_id"])
    op.create_index("ix_commercial_rag_retrieval_audits_client_id", "commercial_rag_retrieval_audits", ["client_id"])
    op.create_index("ix_commercial_rag_retrieval_audits_request_hash", "commercial_rag_retrieval_audits", ["request_hash"])
    op.create_index("ix_commercial_rag_retrieval_audits_immutable_hash", "commercial_rag_retrieval_audits", ["immutable_hash"])

    op.create_table(
        "commercial_rag_poisoning_alerts",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("vault_id", _uuid_type(), nullable=False),
        sa.Column("alert_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["vault_id"], ["commercial_rag_vaults.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_commercial_rag_poisoning_alerts_vault_id", "commercial_rag_poisoning_alerts", ["vault_id"])
    op.create_index("ix_commercial_rag_poisoning_alerts_alert_type", "commercial_rag_poisoning_alerts", ["alert_type"])
    op.create_index("ix_commercial_rag_poisoning_alerts_resolved", "commercial_rag_poisoning_alerts", ["resolved"])

    op.create_table(
        "commercial_rag_legal_holds",
        sa.Column("id", _uuid_type(), nullable=False),
        sa.Column("vault_id", _uuid_type(), nullable=False),
        sa.Column("document_id", _uuid_type(), nullable=True),
        sa.Column("hold_reason", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["vault_id"], ["commercial_rag_vaults.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["commercial_rag_documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_commercial_rag_legal_holds_vault_id", "commercial_rag_legal_holds", ["vault_id"])
    op.create_index("ix_commercial_rag_legal_holds_document_id", "commercial_rag_legal_holds", ["document_id"])
    op.create_index("ix_commercial_rag_legal_holds_active", "commercial_rag_legal_holds", ["active"])


def downgrade() -> None:
    op.drop_table("commercial_rag_legal_holds")
    op.drop_table("commercial_rag_poisoning_alerts")
    op.drop_table("commercial_rag_retrieval_audits")
    op.drop_table("commercial_rag_access_policies")
    op.drop_table("commercial_rag_chunks")
    op.drop_table("commercial_rag_documents")
    op.drop_table("commercial_rag_vaults")
