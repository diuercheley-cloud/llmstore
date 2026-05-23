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
    from app.db.base import Base
    from app.models.agents import (
        AgentDefinition, AgentRun, AgentRunStep, AgentRunEvent, AgentRunCheckpoint, AgentRunReceipt,
        AgentRegistryEntry, AgentVersion, AgentPromotion, AgentDeprecation, AgentLifecycleEvent,
        AgentTool, AgentToolVersion, AgentToolPermission, AgentToolInvocation, AgentToolSafetyReview,
        AgentApprovalRequest, AgentApprovalDecision, AgentApprovalPolicy, AgentMemoryPolicy,
        AgentMemoryCollection, AgentMemoryItem, AgentMemoryAccessEvent, AgentMemoryRetentionJob,
        AgentMemoryConsent, AgentMemoryRetentionPolicy, AgentMemoryRedactionEvent, AgentMemoryIndex,
        AgentMemorySearchEvent, AgentMemoryDeleteRequest, AgentMemoryExportRequest, AgentPlan,
        AgentTask, AgentTaskDependency, AgentTaskAttempt, AgentCompensationAction, AgentHandoffPolicy,
        AgentCollaborationSession, AgentHandoffEvent, AgentMarketplaceEntry, AgentBundleVersion,
        AgentBundleInstall, AgentBundleTrustReport, AgentAdapterPromotionReview,
        AgentPromotionGate, AgentPublisherProfile, AgentPublicationReview, AgentCatalogItem,
        AgentCatalogVersion, AgentCatalogRollback, AgentDelegationPolicy, AgentSharedMemoryPolicy,
        AgentPolicyDecision
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
        AgentPromotionGate.__table__,
        AgentPolicyDecision.__table__,
        AgentCatalogItem.__table__,
        AgentCatalogVersion.__table__,
        AgentCatalogRollback.__table__,
        AgentDelegationPolicy.__table__,
        AgentSharedMemoryPolicy.__table__
    ]
    Base.metadata.create_all(bind, tables=tables)


def downgrade() -> None:
    op.drop_table('agent_shared_memory_policies')
    op.drop_table('agent_delegation_policies')
    op.drop_table('agent_catalog_rollbacks')
    op.drop_table('agent_catalog_versions')
    op.drop_table('agent_catalog_items')
    op.drop_table('agent_policy_decisions')
    op.drop_table('agent_promotion_gates')
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
    op.drop_table('agent_memory_indexes')
    op.drop_table('agent_memory_redaction_events')
    op.drop_table('agent_memory_retention_policies')
    op.drop_table('agent_memory_consents')
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
