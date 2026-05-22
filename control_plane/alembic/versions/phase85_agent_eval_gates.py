# Models: AgentEvalDataset, AgentEvalDatasetVersion, AgentEvalGateResult, AgentEvalRegressionResult, AgentPromotionGateResult
"""Agent Evals and Gates

Revision ID: phase85_agent_eval_gates
Revises: phase84_agent_tool_execution
Create Date: 2026-05-22 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'phase85_agent_eval_gates'
down_revision: Union[str, None] = 'phase84_agent_tool_execution'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. agent_eval_suites
    op.create_table('agent_eval_suites',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agent_definitions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_eval_suites_agent_id'), 'agent_eval_suites', ['agent_id'], unique=False)

    # 2. agent_eval_cases
    op.create_table('agent_eval_cases',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('suite_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('input_text', sa.Text(), nullable=False),
        sa.Column('input_hash', sa.String(length=128), nullable=False),
        sa.Column('expected_behavior', sa.Text(), nullable=True),
        sa.Column('prohibited_behavior', sa.Text(), nullable=True),
        sa.Column('allowed_tools', sa.JSON(), nullable=True),
        sa.Column('expected_tool_calls', sa.JSON(), nullable=True),
        sa.Column('max_cost_brl', sa.Float(), nullable=True),
        sa.Column('max_steps', sa.Integer(), nullable=True),
        sa.Column('assertions', sa.JSON(), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['suite_id'], ['agent_eval_suites.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_eval_cases_suite_id'), 'agent_eval_cases', ['suite_id'], unique=False)

    # 3. agent_eval_runs
    op.create_table('agent_eval_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('suite_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('passed_count', sa.Integer(), nullable=False),
        sa.Column('failed_count', sa.Integer(), nullable=False),
        sa.Column('total_count', sa.Integer(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['suite_id'], ['agent_eval_suites.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_eval_runs_suite_id'), 'agent_eval_runs', ['suite_id'], unique=False)

    # 4. agent_eval_results
    op.create_table('agent_eval_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('passed', sa.Boolean(), nullable=False),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('assertion_results', sa.JSON(), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=True),
        sa.Column('total_cost_brl', sa.Float(), nullable=True),
        sa.Column('failure_details', sa.Text(), nullable=True),
        sa.Column('run_id_ref', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['agent_eval_cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['run_id'], ['agent_eval_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_eval_results_case_id'), 'agent_eval_results', ['case_id'], unique=False)
    op.create_index(op.f('ix_agent_eval_results_run_id'), 'agent_eval_results', ['run_id'], unique=False)

    # 5. agent_eval_baselines
    op.create_table('agent_eval_baselines',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('pass_rate', sa.Float(), nullable=False),
        sa.Column('version', sa.String(length=64), nullable=False),
        sa.Column('set_by', sa.String(length=128), nullable=False),
        sa.Column('is_stale', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agent_registry_entries.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['run_id'], ['agent_eval_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_eval_baselines_agent_id'), 'agent_eval_baselines', ['agent_id'], unique=True)

    # 6. agent_eval_datasets
    op.create_table('agent_eval_datasets',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agent_registry_entries.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_eval_datasets_agent_id'), 'agent_eval_datasets', ['agent_id'], unique=False)

    # 7. agent_eval_dataset_versions
    op.create_table('agent_eval_dataset_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.String(length=64), nullable=False),
        sa.Column('cases_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['dataset_id'], ['agent_eval_datasets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_eval_dataset_versions_dataset_id'), 'agent_eval_dataset_versions', ['dataset_id'], unique=False)

    # 8. agent_eval_gate_results
    op.create_table('agent_eval_gate_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('eval_run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('passed', sa.Boolean(), nullable=False),
        sa.Column('pass_rate', sa.Float(), nullable=False),
        sa.Column('tool_misuse_rate', sa.Float(), nullable=False),
        sa.Column('policy_denial_rate', sa.Float(), nullable=False),
        sa.Column('avg_latency_ms', sa.Float(), nullable=False),
        sa.Column('total_cost_brl', sa.Float(), nullable=False),
        sa.Column('max_steps_exceeded', sa.Boolean(), nullable=False),
        sa.Column('secret_leak_detected', sa.Boolean(), nullable=False),
        sa.Column('cross_tenant_access_detected', sa.Boolean(), nullable=False),
        sa.Column('details', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agent_registry_entries.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['eval_run_id'], ['agent_eval_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_eval_gate_results_agent_id'), 'agent_eval_gate_results', ['agent_id'], unique=False)
    op.create_index(op.f('ix_agent_eval_gate_results_eval_run_id'), 'agent_eval_gate_results', ['eval_run_id'], unique=False)

    # 9. agent_eval_regression_results
    op.create_table('agent_eval_regression_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('eval_run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('baseline_run_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('passed', sa.Boolean(), nullable=False),
        sa.Column('regression_detected', sa.Boolean(), nullable=False),
        sa.Column('metric_diffs', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agent_registry_entries.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['eval_run_id'], ['agent_eval_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['baseline_run_id'], ['agent_eval_runs.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_eval_regression_results_agent_id'), 'agent_eval_regression_results', ['agent_id'], unique=False)
    op.create_index(op.f('ix_agent_eval_regression_results_eval_run_id'), 'agent_eval_regression_results', ['eval_run_id'], unique=False)
    op.create_index(op.f('ix_agent_eval_regression_results_baseline_run_id'), 'agent_eval_regression_results', ['baseline_run_id'], unique=False)

    # 10. agent_promotion_gate_results
    op.create_table('agent_promotion_gate_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_status', sa.String(length=32), nullable=False),
        sa.Column('passed', sa.Boolean(), nullable=False),
        sa.Column('baseline_run_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('gate_result_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('regression_result_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('audit_override', sa.Boolean(), nullable=False),
        sa.Column('override_reason', sa.Text(), nullable=True),
        sa.Column('override_by', sa.String(length=128), nullable=True),
        sa.Column('details', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agent_registry_entries.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['baseline_run_id'], ['agent_eval_runs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['gate_result_id'], ['agent_eval_gate_results.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['regression_result_id'], ['agent_eval_regression_results.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_promotion_gate_results_agent_id'), 'agent_promotion_gate_results', ['agent_id'], unique=False)


def downgrade() -> None:
    op.drop_table('agent_promotion_gate_results')
    op.drop_table('agent_eval_regression_results')
    op.drop_table('agent_eval_gate_results')
    op.drop_table('agent_eval_dataset_versions')
    op.drop_table('agent_eval_datasets')
    op.drop_table('agent_eval_baselines')
    op.drop_table('agent_eval_results')
    op.drop_table('agent_eval_runs')
    op.drop_table('agent_eval_cases')
    op.drop_table('agent_eval_suites')
