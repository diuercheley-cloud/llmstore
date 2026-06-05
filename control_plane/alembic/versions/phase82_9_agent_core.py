"""Agent platform core tables

Revision ID: phase82_9_agent_core
Revises: 6c73eca75cd9
Create Date: 2026-05-22 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'phase82_9_agent_core'
down_revision: Union[str, None] = '6c73eca75cd9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Dependencies needed by AgentDefinition ---
    
    # prompt_templates
    op.create_table(
        'prompt_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.String(length=128), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('variable_schema', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('active_version_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_prompt_templates_tenant_id', 'prompt_templates', ['tenant_id'])
    op.create_index('ix_prompt_templates_name', 'prompt_templates', ['name'])

    # prompt_template_versions
    op.create_table(
        'prompt_template_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('prompt_templates.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version', sa.String(length=64), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # agent_sessions
    op.create_table(
        'agent_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.String(length=128), nullable=False),
        sa.Column('user_id', sa.String(length=128), nullable=True),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False), # FK added later
        sa.Column('title', sa.String(length=256), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='active'),
        sa.Column('retention_policy', sa.JSON(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # multimodal_assets
    op.create_table(
        'multimodal_assets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('asset_type', sa.String(length=32), nullable=False),
        sa.Column('storage_path', sa.String(length=256), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(length=64), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=False),
        sa.Column('provenance', sa.String(length=256), nullable=True),
        sa.Column('exif_sanitized', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )

    from app.db.base import Base
    from app.models.agents import (
        AgentAdapterPromotionReview,
        AgentApprovalDecision,
        AgentApprovalPolicy,
        AgentApprovalRequest,
        AgentBundleInstall,
        AgentBundleTrustReport,
        AgentBundleVersion,
        AgentCatalogItem,
        AgentCatalogRollback,
        AgentCatalogVersion,
        AgentCollaborationSession,
        AgentCompensationAction,
        AgentDefinition,
        AgentDelegationPolicy,
        AgentDeprecation,
        AgentHandoffEvent,
        AgentHandoffPolicy,
        AgentLifecycleEvent,
        AgentMarketplaceEntry,
        AgentMemoryAccessEvent,
        AgentMemoryCollection,
        AgentMemoryConsent,
        AgentMemoryDeleteRequest,
        AgentMemoryExportRequest,
        AgentMemoryIndex,
        AgentMemoryItem,
        AgentMemoryPolicy,
        AgentMemoryRedactionEvent,
        AgentMemoryRetentionJob,
        AgentMemoryRetentionPolicy,
        AgentMemorySearchEvent,
        AgentPlan,
        AgentPolicyDecision,
        AgentPromotion,
        AgentPromotionGate,
        AgentRegistryEntry,
        AgentRun,
        AgentRunCheckpoint,
        AgentRunEvent,
        AgentRunReceipt,
        AgentRunStep,
        AgentSharedMemoryPolicy,
        AgentTask,
        AgentTaskAttempt,
        AgentTaskDependency,
        AgentTool,
        AgentToolInvocation,
        AgentToolPermission,
        AgentToolSafetyReview,
        AgentToolVersion,
        AgentVersion,
    )
    bind = op.get_bind()
    tables = [
        AgentRegistryEntry.__table__,
        AgentVersion.__table__,
        AgentDefinition.__table__,
        AgentRun.__table__,
        AgentRunStep.__table__,
        AgentRunEvent.__table__,
        AgentRunCheckpoint.__table__,
        AgentRunReceipt.__table__,
        AgentPromotion.__table__,
        AgentDeprecation.__table__,
        AgentLifecycleEvent.__table__,
        AgentTool.__table__,
        AgentToolVersion.__table__,
        AgentToolPermission.__table__,
        AgentToolInvocation.__table__,
        AgentToolSafetyReview.__table__,
        AgentApprovalRequest.__table__,
        AgentApprovalDecision.__table__,
        AgentApprovalPolicy.__table__,
        AgentMemoryPolicy.__table__,
        AgentMemoryCollection.__table__,
        AgentMemoryItem.__table__,
        AgentMemoryAccessEvent.__table__,
        AgentMemoryRetentionJob.__table__,
        AgentMemoryConsent.__table__,
        AgentMemoryRetentionPolicy.__table__,
        AgentMemoryRedactionEvent.__table__,
        AgentMemoryIndex.__table__,
        AgentMemorySearchEvent.__table__,
        AgentMemoryDeleteRequest.__table__,
        AgentMemoryExportRequest.__table__,
        AgentPlan.__table__,
        AgentTask.__table__,
        AgentTaskDependency.__table__,
        AgentTaskAttempt.__table__,
        AgentCompensationAction.__table__,
        AgentHandoffPolicy.__table__,
        AgentCollaborationSession.__table__,
        AgentHandoffEvent.__table__,
        AgentMarketplaceEntry.__table__,
        AgentBundleVersion.__table__,
        AgentBundleInstall.__table__,
        AgentBundleTrustReport.__table__,
        AgentAdapterPromotionReview.__table__,
        AgentPolicyDecision.__table__,
        AgentCatalogItem.__table__,
        AgentCatalogVersion.__table__,
        AgentCatalogRollback.__table__,
        AgentDelegationPolicy.__table__,
        AgentSharedMemoryPolicy.__table__
    ]
    Base.metadata.create_all(bind, tables=tables)
    
    # Add FK for agent_sessions now that agent_definitions exists
    op.create_foreign_key('fk_agent_sessions_agent_id', 'agent_sessions', 'agent_definitions', ['agent_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    op.drop_table('agent_shared_memory_policies')
    op.drop_table('agent_delegation_policies')
    op.drop_table('agent_catalog_rollbacks')
    op.drop_table('agent_catalog_versions')
    op.drop_table('agent_catalog_items')
    op.drop_table('agent_policy_decisions')
    op.drop_table('agent_adapter_promotion_reviews')
    op.drop_table('agent_bundle_trust_reports')
    op.drop_table('agent_bundle_installs')
    op.drop_table('agent_bundle_versions')
    op.drop_table('agent_marketplace_entries')
    op.drop_table('agent_handoff_events')
    op.drop_table('agent_collaboration_sessions')
    op.drop_table('agent_handoff_policies')
    op.drop_table('agent_compensation_actions')
    op.drop_table('agent_task_attempts')
    op.drop_table('agent_task_dependencies')
    op.drop_table('agent_tasks')
    op.drop_table('agent_plans')
    op.drop_table('agent_memory_export_requests')
    op.drop_table('agent_memory_delete_requests')
    op.drop_table('agent_memory_search_events')
    op.drop_table('agent_memory_indices')
    op.drop_table('agent_memory_redaction_events')
    op.drop_table('agent_memory_retention_policies')
    op.drop_table('agent_memory_consents')
    op.drop_table('agent_memory_retention_jobs')
    op.drop_table('agent_memory_access_events')
    op.drop_table('agent_memory_items')
    op.drop_table('agent_memory_collections')
    op.drop_table('agent_memory_policies')
    op.drop_table('agent_approval_decisions')
    op.drop_table('agent_approval_requests')
    op.drop_table('agent_approval_policies')
    op.drop_table('agent_tool_safety_reviews')
    op.drop_table('agent_tool_invocations')
    op.drop_table('agent_tool_permissions')
    op.drop_table('agent_tool_versions')
    op.drop_table('agent_tools')
    op.drop_table('agent_lifecycle_events')
    op.drop_table('agent_deprecations')
    op.drop_table('agent_promotions')
    op.drop_table('agent_versions')
    op.drop_table('agent_registry_entries')
    op.drop_table('agent_run_receipts')
    op.drop_table('agent_run_checkpoints')
    op.drop_table('agent_run_events')
    op.drop_table('agent_run_steps')
    op.drop_table('agent_runs')
    op.drop_table('agent_definitions')
    op.drop_table('multimodal_assets')
    op.drop_table('agent_sessions')
    op.drop_table('prompt_template_versions')
    op.drop_table('prompt_templates')
