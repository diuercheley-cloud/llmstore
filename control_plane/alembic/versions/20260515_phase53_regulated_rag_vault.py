"""phase53_regulated_rag_vault

Revision ID: 3b1a2c4d5e6f
Revises: 65d3a2f8b1c4
Create Date: 2026-05-15 14:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '3b1a2c4d5e6f'
down_revision = '65d3a2f8b1c4'
branch_labels = None
depends_on = None

def upgrade():
    # Drop existing tables from Phase 48 to apply Phase 53 schema
    op.execute("DROP TABLE IF EXISTS commercial_rag_legal_holds CASCADE")
    op.execute("DROP TABLE IF EXISTS commercial_rag_poisoning_alerts CASCADE")
    op.execute("DROP TABLE IF EXISTS commercial_rag_retrieval_audits CASCADE")
    op.execute("DROP TABLE IF EXISTS commercial_rag_access_policies CASCADE")
    op.execute("DROP TABLE IF EXISTS commercial_rag_chunks CASCADE")
    op.execute("DROP TABLE IF EXISTS commercial_rag_documents CASCADE")
    op.execute("DROP TABLE IF EXISTS commercial_rag_vaults CASCADE")

    # 1. CommercialRAGVault
    op.create_table(
        'commercial_rag_vaults',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(length=128), nullable=False),
        sa.Column('vault_name', sa.String(length=128), nullable=False),
        sa.Column('is_encrypted', sa.Boolean(), nullable=True),
        sa.Column('encryption_key_hash', sa.String(length=128), nullable=True),
        sa.Column('retention_policy_days', sa.Integer(), nullable=True),
        sa.Column('strict_policy_enforcement', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_commercial_rag_vaults_tenant_id'), 'commercial_rag_vaults', ['tenant_id'], unique=False)

    # 2. CommercialRAGDocument
    op.create_table(
        'commercial_rag_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('vault_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_hash', sa.String(length=128), nullable=False),
        sa.Column('metadata_encrypted', sa.JSON(), nullable=True),
        sa.Column('classification_level', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['vault_id'], ['commercial_rag_vaults.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_commercial_rag_documents_document_hash'), 'commercial_rag_documents', ['document_hash'], unique=False)

    # 3. CommercialRAGChunk
    op.create_table(
        'commercial_rag_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chunk_hash', sa.String(length=128), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('embedding_metadata_encrypted', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['commercial_rag_documents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_commercial_rag_chunks_chunk_hash'), 'commercial_rag_chunks', ['chunk_hash'], unique=False)

    # 4. CommercialRetrievalReceipt
    op.create_table(
        'commercial_retrieval_receipts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('vault_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.String(length=128), nullable=False),
        sa.Column('query_hash', sa.String(length=128), nullable=False),
        sa.Column('retrieved_chunk_hashes', sa.JSON(), nullable=False),
        sa.Column('receipt_hash', sa.String(length=128), nullable=False),
        sa.Column('signature', sa.String(length=256), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['vault_id'], ['commercial_rag_vaults.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_commercial_retrieval_receipts_receipt_hash'), 'commercial_retrieval_receipts', ['receipt_hash'], unique=False)
    op.create_index(op.f('ix_commercial_retrieval_receipts_session_id'), 'commercial_retrieval_receipts', ['session_id'], unique=False)

    # 5. CommercialRetrievalPolicyViolation
    op.create_table(
        'commercial_retrieval_policy_violations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('vault_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.String(length=128), nullable=False),
        sa.Column('query_hash', sa.String(length=128), nullable=False),
        sa.Column('violation_type', sa.String(length=64), nullable=False),
        sa.Column('action_taken', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['vault_id'], ['commercial_rag_vaults.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('commercial_retrieval_policy_violations')
    op.drop_index(op.f('ix_commercial_retrieval_receipts_session_id'), table_name='commercial_retrieval_receipts')
    op.drop_index(op.f('ix_commercial_retrieval_receipts_receipt_hash'), table_name='commercial_retrieval_receipts')
    op.drop_table('commercial_retrieval_receipts')
    op.drop_index(op.f('ix_commercial_rag_chunks_chunk_hash'), table_name='commercial_rag_chunks')
    op.drop_table('commercial_rag_chunks')
    op.drop_index(op.f('ix_commercial_rag_documents_document_hash'), table_name='commercial_rag_documents')
    op.drop_table('commercial_rag_documents')
    op.drop_index(op.f('ix_commercial_rag_vaults_tenant_id'), table_name='commercial_rag_vaults')
    op.drop_table('commercial_rag_vaults')
