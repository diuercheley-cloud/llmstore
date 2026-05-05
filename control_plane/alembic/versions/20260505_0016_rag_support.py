"""rag support

Revision ID: 20260505_0016
Revises: 20260504_0015
Create Date: 2026-05-05 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260505_0016'
down_revision = '20260504_0015'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Try to enable pgvector extension only if available
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'vector') THEN
            CREATE EXTENSION IF NOT EXISTS vector;
        END IF;
    END
    $$;
    """)

    # Table rag_documents
    op.create_table(
        'rag_documents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('storage_path', sa.String(length=512), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='uploaded', nullable=False),
        sa.Column('page_count', sa.Integer(), nullable=True),
        sa.Column('chunk_count', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rag_documents_client_id'), 'rag_documents', ['client_id'], unique=False)
    op.create_index(op.f('ix_rag_documents_status'), 'rag_documents', ['status'], unique=False)

    # Table rag_document_chunks
    op.create_table(
        'rag_document_chunks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['document_id'], ['rag_documents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add embedding column with pgvector if available, otherwise JSONB
    conn = op.get_bind()
    res = conn.execute(sa.text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")).scalar()
    if res:
        # We need to import Vector here or use raw SQL
        op.execute("ALTER TABLE rag_document_chunks ADD COLUMN embedding vector(384)")
    else:
        op.add_column('rag_document_chunks', sa.Column('embedding', postgresql.JSONB(), nullable=True))

    op.create_index(op.f('ix_rag_document_chunks_client_id'), 'rag_document_chunks', ['client_id'], unique=False)
    op.create_index(op.f('ix_rag_document_chunks_document_id'), 'rag_document_chunks', ['document_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_rag_document_chunks_document_id'), table_name='rag_document_chunks')
    op.drop_index(op.f('ix_rag_document_chunks_client_id'), table_name='rag_document_chunks')
    op.drop_table('rag_document_chunks')
    op.drop_index(op.f('ix_rag_documents_status'), table_name='rag_documents')
    op.drop_index(op.f('ix_rag_documents_client_id'), table_name='rag_documents')
    op.drop_table('rag_documents')
