"""agentic evolutionary intelligence tables

Revision ID: 20260529_0096
Revises: 20260528_0095
Create Date: 2026-05-29 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260529_0096"
down_revision: Union[str, Sequence[str], None] = "20260528_0095"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from app.db.base import Base
    from app.models.agents.agent_canary import (
        AgentCanaryAssignment,
        AgentCanaryComparison,
        AgentCanaryPromotionReview,
        AgentShadowRun,
    )
    from app.models.agents.agent_cognitive_loopback import (
        AgentFeedbackEvent,
        AgentFewShotExample,
        AgentLearningCandidate,
        AgentLearningPromotionReview,
        AgentSuccessPattern,
    )
    from app.models.agents.agent_debugger import (
        AgentDebugReplay,
        AgentDebugStateEdit,
        AgentRunSnapshot,
    )
    from app.models.agents.agent_federated_memory import (
        FederatedGraphFact,
        FederatedMemoryPeer,
        FederatedMemorySummary,
        FederatedSyncEvent,
        RemoteMemoryReference,
    )
    from app.models.agents.agent_meta_reviewer import (
        AgentMetaReview,
        AgentMetaReviewDecision,
        AgentMetaReviewFinding,
    )
    from app.models.agents.agent_uncertainty import (
        AgentConfidenceScore,
        AgentEvidenceGap,
        AgentUncertaintyEvent,
        AgentUncertaintyPolicy,
    )
    from app.models.agents.agent_wallet import (
        AgentSpendAuthorization,
        AgentWallet,
        AgentWalletLedgerEntry,
        AgentWalletLimit,
    )
    from app.models.agents.digital_twin import (
        DigitalTwin,
        DigitalTwinCommand,
        DigitalTwinSafetyEvent,
        DigitalTwinState,
    )

    bind = op.get_bind()
    tables = [
        AgentCanaryAssignment.__table__,
        AgentShadowRun.__table__,
        AgentCanaryComparison.__table__,
        AgentCanaryPromotionReview.__table__,
        AgentFeedbackEvent.__table__,
        AgentSuccessPattern.__table__,
        AgentFewShotExample.__table__,
        AgentLearningCandidate.__table__,
        AgentLearningPromotionReview.__table__,
        AgentRunSnapshot.__table__,
        AgentDebugReplay.__table__,
        AgentDebugStateEdit.__table__,
        FederatedMemoryPeer.__table__,
        FederatedMemorySummary.__table__,
        FederatedGraphFact.__table__,
        RemoteMemoryReference.__table__,
        FederatedSyncEvent.__table__,
        AgentMetaReview.__table__,
        AgentMetaReviewFinding.__table__,
        AgentMetaReviewDecision.__table__,
        AgentUncertaintyEvent.__table__,
        AgentConfidenceScore.__table__,
        AgentEvidenceGap.__table__,
        AgentUncertaintyPolicy.__table__,
        AgentWallet.__table__,
        AgentWalletLedgerEntry.__table__,
        AgentSpendAuthorization.__table__,
        AgentWalletLimit.__table__,
        DigitalTwin.__table__,
        DigitalTwinState.__table__,
        DigitalTwinCommand.__table__,
        DigitalTwinSafetyEvent.__table__,
    ]
    Base.metadata.create_all(bind, tables=tables)


def downgrade() -> None:
    op.drop_table("digital_twin_safety_events")
    op.drop_table("digital_twin_commands")
    op.drop_table("digital_twin_states")
    op.drop_table("digital_twins")
    op.drop_table("agent_wallet_limits")
    op.drop_table("agent_spend_authorizations")
    op.drop_table("agent_wallet_ledger_entries")
    op.drop_table("agent_wallets")
    op.drop_table("agent_uncertainty_policies")
    op.drop_table("agent_evidence_gaps")
    op.drop_table("agent_confidence_scores")
    op.drop_table("agent_uncertainty_events")
    op.drop_table("agent_meta_review_decisions")
    op.drop_table("agent_meta_review_findings")
    op.drop_table("agent_meta_reviews")
    op.drop_table("federated_sync_events")
    op.drop_table("remote_memory_references")
    op.drop_table("federated_graph_facts")
    op.drop_table("federated_memory_summaries")
    op.drop_table("federated_memory_peers")
    op.drop_table("agent_debug_state_edits")
    op.drop_table("agent_debug_replays")
    op.drop_table("agent_run_snapshots")
    op.drop_table("agent_learning_promotion_reviews")
    op.drop_table("agent_learning_candidates")
    op.drop_table("agent_fewshot_examples")
    op.drop_table("agent_success_patterns")
    op.drop_table("agent_feedback_events")
    op.drop_table("agent_canary_promotion_reviews")
    op.drop_table("agent_canary_comparisons")
    op.drop_table("agent_shadow_runs")
    op.drop_table("agent_canary_assignments")
