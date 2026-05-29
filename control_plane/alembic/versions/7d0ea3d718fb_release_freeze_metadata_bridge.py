"""Release freeze metadata bridge for agentic platform hardening.

Revision ID: 7d0ea3d718fb
Revises: f5a5ea240ea1
Create Date: 2026-05-29 09:05:00.000000

This no-op revision documents model rollout coverage for:
- RuntimeCluster
- DistributedAgentJob
- DistributedJobLease
- DistributedFailoverEvent
- ManagedControlPlaneLink
- ManagedPolicySyncEvent
- AgentCapabilityCatalogEntry
- ConnectorCatalogEntry
- MCPCatalogEntry
- PluginCatalogEntry
- PluginSignature
- PluginTrustReportGov
- PluginInstallEvent
- CapabilityApprovalEvent
"""

revision = "7d0ea3d718fb"
down_revision = "f5a5ea240ea1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    return None


def downgrade() -> None:
    return None
