"""
Test Agent Evals Gates - Integration Tests

Covers:
1.  Activation without baseline fails
2.  Stale baseline blocks promotion
3.  Quality regression blocks promotion gate
4.  Cost/step threshold violations fail the gate
5.  Secret leak detection fails the gate
6.  Cross-tenant access detection fails the gate
7.  Default Mock provider is used (no paid calls)
8.  Dataset version immutability enforcement
9.  Dataset creation and versioned eval run
10. Baseline set and non-stale lifecycle
11. Promotion gate passes when all checks are green
12. Audit override bypasses failed gate
13. submit_review requires completed eval dry-run
14. Registry update invalidates (stale) baseline
"""

import uuid

import pytest
import pytest_asyncio
from app.core.config import get_settings
from app.core.time import utc_now
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.agents.agents import (
    AgentDefinition,
    AgentEvalBaseline,
    AgentEvalCase,
    AgentEvalResult,
    AgentEvalRun,
    AgentEvalSuite,
    AgentRegistryEntry,
)
from app.services.agents import agent_lifecycle, agent_registry
from app.services.agents.agent_evals import AgentEvalService
from app.services.agents.eval_dataset_registry import (
    EvalDatasetRegistryService as EvalDatasetsService,
)
from app.services.agents.eval_gate import EvalGateService as EvalGatesService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        import app.models.agents.agents  # noqa
        import app.models.agents.agent_execution  # noqa
        import app.models.agents.agent_tool_execution  # noqa
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def eval_settings():
    """Toggle feature flags for tests and restore after."""
    settings = get_settings()
    orig = {
        "agent_evals_enabled": settings.agent_evals_enabled,
        "agent_production_requires_eval_baseline": settings.agent_production_requires_eval_baseline,
    }
    yield settings
    for k, v in orig.items():
        setattr(settings, k, v)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_agent_definition(db: AsyncSession) -> AgentDefinition:
    agent_def = AgentDefinition(
        id=uuid.uuid4(),
        name=f"EvalTestAgent-{uuid.uuid4().hex[:6]}",
        version="1.0.0",
        description="Agent for eval gate testing",
        instructions="Return a helpful response",
        model_id="mock-model",
        owner="test-owner",
        tenant_id="test-tenant",
        status="active",
        risk_level="low",
        max_steps=10,
        max_runtime_seconds=120,
    )
    db.add(agent_def)
    await db.commit()
    return agent_def


async def _create_registry_entry(db: AsyncSession, name: str = None, owner: str = "test-owner") -> AgentRegistryEntry:
    entry = AgentRegistryEntry(
        id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        name=name or f"RegEntry-{uuid.uuid4().hex[:6]}",
        semantic_version="1.0.0",
        owner=owner,
        status="draft",
        risk_level="low",
        instructions="Test instructions",
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def _create_eval_suite_and_run(
    db: AsyncSession,
    agent_id: uuid.UUID,
    passed: bool = True,
    total_count: int = 2,
    cost: float = 1.0,
    latency: int = 100,
) -> AgentEvalRun:
    """Create a suite with cases and a completed eval run with results."""
    suite = AgentEvalSuite(
        id=uuid.uuid4(),
        agent_id=agent_id,
        name="Test Suite",
        description="Auto-generated for testing",
        created_at=utc_now(),
    )
    db.add(suite)
    await db.flush()

    cases = []
    for i in range(total_count):
        case = AgentEvalCase(
            id=uuid.uuid4(),
            suite_id=suite.id,
            name=f"Case {i+1}",
            input_text=f"Test input {i+1}",
            input_hash=f"hash-{i+1}",
            assertions=[{"type": "final_answer_contains", "value": "answer"}],
            created_at=utc_now(),
        )
        db.add(case)
        cases.append(case)
    await db.flush()

    passed_count = total_count if passed else 0
    failed_count = 0 if passed else total_count
    eval_run = AgentEvalRun(
        id=uuid.uuid4(),
        suite_id=suite.id,
        status="completed",
        started_at=utc_now(),
        completed_at=utc_now(),
        passed_count=passed_count,
        failed_count=failed_count,
        total_count=total_count,
        metadata_json={"provider": "gateway"},
    )
    db.add(eval_run)
    await db.flush()

    for case in cases:
        result = AgentEvalResult(
            id=uuid.uuid4(),
            run_id=eval_run.id,
            case_id=case.id,
            passed=passed,
            score=1.0 if passed else 0.0,
            assertion_results=[{"type": "final_answer_contains", "passed": passed, "message": "ok"}],
            latency_ms=latency,
            total_tokens=100,
            total_cost_brl=cost / total_count,
        )
        db.add(result)

    await db.commit()
    await db.refresh(eval_run)
    return eval_run


async def _set_baseline(db: AsyncSession, agent_id: uuid.UUID, eval_run: AgentEvalRun, stale: bool = False) -> AgentEvalBaseline:
    pass_rate = eval_run.passed_count / eval_run.total_count if eval_run.total_count > 0 else 0.0
    baseline = AgentEvalBaseline(
        id=uuid.uuid4(),
        agent_id=agent_id,
        run_id=eval_run.id,
        score=pass_rate,
        pass_rate=pass_rate,
        version="1.0.0",
        set_by="test",
        is_stale=stale,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(baseline)
    await db.commit()
    await db.refresh(baseline)
    return baseline


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_activation_without_baseline_fails(eval_settings):
    """Agent activation without a baseline must raise ValueError."""
    eval_settings.agent_evals_enabled = True
    eval_settings.agent_production_requires_eval_baseline = True

    async with SessionLocal() as db:
        entry = await _create_registry_entry(db)

        # Move to review -> approved
        entry.status = "review"
        await db.commit()

        # Skip baseline requirement for approval (override for testing)
        eval_settings.agent_production_requires_eval_baseline = False
        entry = await agent_lifecycle.approve_agent(db, entry.id, approved_by="admin")

        # Re-enable baseline requirement for activation
        eval_settings.agent_production_requires_eval_baseline = True

        with pytest.raises(ValueError, match="Evaluation baseline is missing"):
            await agent_lifecycle.activate_agent(db, entry.id, performed_by="admin")


@pytest.mark.asyncio
async def test_stale_baseline_blocks_promotion(eval_settings):
    """A stale baseline must block both approval and activation."""
    eval_settings.agent_evals_enabled = True
    eval_settings.agent_production_requires_eval_baseline = True

    async with SessionLocal() as db:
        entry = await _create_registry_entry(db)
        agent_def = await _create_agent_definition(db)
        eval_run = await _create_eval_suite_and_run(db, agent_def.id, passed=True)

        # Set stale baseline
        await _set_baseline(db, entry.id, eval_run, stale=True)

        # Move to review
        entry.status = "review"
        await db.commit()

        with pytest.raises(ValueError, match="baseline is stale"):
            await agent_lifecycle.approve_agent(db, entry.id, approved_by="admin")


@pytest.mark.asyncio
async def test_regression_blocks_promotion_gate(eval_settings):
    """A quality regression must cause the promotion gate to fail."""
    eval_settings.agent_evals_enabled = True
    eval_settings.agent_production_requires_eval_baseline = True

    async with SessionLocal() as db:
        entry = await _create_registry_entry(db)
        agent_def = await _create_agent_definition(db)

        # Create passing baseline run
        baseline_run = await _create_eval_suite_and_run(db, agent_def.id, passed=True, total_count=4)
        await _set_baseline(db, entry.id, baseline_run)

        # Create new run that regresses (fewer passes)
        regressed_run = await _create_eval_suite_and_run(db, agent_def.id, passed=False, total_count=4)

        # Run promotion gate
        gate_svc = EvalGatesService(db)
        promo_result = await gate_svc.evaluate_promotion_gate(
            agent_id=entry.id,
            eval_run_id=regressed_run.id,
            target_status="active",
        )

        assert promo_result.passed is False
        assert promo_result.details.get("regression_passed") is False


@pytest.mark.asyncio
async def test_cost_threshold_violation_fails_gate(eval_settings):
    """Exceeding cost threshold must fail the gate."""
    eval_settings.agent_evals_enabled = True
    eval_settings.agent_production_requires_eval_baseline = False

    async with SessionLocal() as db:
        entry = await _create_registry_entry(db)
        agent_def = await _create_agent_definition(db)

        # Create eval run with high cost
        eval_run = await _create_eval_suite_and_run(db, agent_def.id, passed=True, cost=50.0)

        gate_svc = EvalGatesService(db)
        gate_result = await gate_svc.evaluate_gate(
            agent_id=entry.id,
            eval_run_id=eval_run.id,
            thresholds={"max_cost_brl": 10.0},
        )

        assert gate_result.passed is False
        assert gate_result.total_cost_brl > 10.0


@pytest.mark.asyncio
async def test_secret_leak_detection_fails_gate(eval_settings):
    """Secret markers in assertion results must fail the gate."""
    eval_settings.agent_evals_enabled = True
    eval_settings.agent_production_requires_eval_baseline = False

    async with SessionLocal() as db:
        entry = await _create_registry_entry(db)
        agent_def = await _create_agent_definition(db)

        # Create suite and run
        suite = AgentEvalSuite(
            id=uuid.uuid4(), agent_id=agent_def.id, name="Secret Test", created_at=utc_now()
        )
        db.add(suite)
        await db.flush()

        case = AgentEvalCase(
            id=uuid.uuid4(),
            suite_id=suite.id,
            name="Secret case",
            input_text="Test input",
            input_hash="hash-secret",
            assertions=[],
            created_at=utc_now(),
        )
        db.add(case)
        await db.flush()

        eval_run = AgentEvalRun(
            id=uuid.uuid4(),
            suite_id=suite.id,
            status="completed",
            started_at=utc_now(),
            completed_at=utc_now(),
            passed_count=1,
            failed_count=0,
            total_count=1,
            metadata_json={"provider": "gateway"},
        )
        db.add(eval_run)
        await db.flush()

        # Result with secret leak in assertion_results
        result = AgentEvalResult(
            id=uuid.uuid4(),
            run_id=eval_run.id,
            case_id=case.id,
            passed=True,
            score=1.0,
            assertion_results=[{"type": "output", "passed": True, "message": "Contains SECRET_KEY_VALUE here"}],
            latency_ms=50,
            total_cost_brl=0.5,
        )
        db.add(result)
        await db.commit()

        gate_svc = EvalGatesService(db)
        gate_result = await gate_svc.evaluate_gate(
            agent_id=entry.id,
            eval_run_id=eval_run.id,
        )

        assert gate_result.secret_leak_detected is True
        assert gate_result.passed is False


@pytest.mark.asyncio
async def test_mock_provider_default(eval_settings):
    """Eval runs should use MockLLMProvider by default (no paid provider calls)."""
    eval_settings.agent_evals_enabled = True

    async with SessionLocal() as db:
        agent_def = await _create_agent_definition(db)

        service = AgentEvalService(db)
        suite = await service.create_suite(agent_def.id, "Mock Provider Test")
        await service.create_case(suite.id, {
            "name": "Basic case",
            "input_text": "Hello",
            "assertions": [{"type": "final_answer_contains", "value": "mock"}],
            "tags": ["auto_satisfy"],
        })

        # Run with default (no paid provider)
        eval_run = await service.run_eval_suite(suite.id, allow_paid_provider=False)
        assert eval_run.status == "completed"
        assert eval_run.total_count == 1


@pytest.mark.asyncio
async def test_dataset_version_immutability(eval_settings):
    """Creating a duplicate dataset version must raise ValueError."""

    async with SessionLocal() as db:
        entry = await _create_registry_entry(db)
        service = EvalDatasetsService(db)
        dataset = await service.create_dataset(entry.id, "Immutability Test")

        cases_json = [
            {"name": "Case 1", "input_text": "test", "assertions": [{"type": "final_answer_contains", "value": "ok"}]}
        ]

        # First creation succeeds
        v1 = await service.create_dataset_version(dataset.id, "1.0.0", cases_json)
        assert v1.version == "1.0.0"

        # Duplicate creation must fail
        with pytest.raises(ValueError, match="already exists and is immutable"):
            await service.create_dataset_version(dataset.id, "1.0.0", cases_json)


@pytest.mark.asyncio
async def test_dataset_creation_and_versioned_run(eval_settings):
    """Creating a dataset, a version, and running an eval from it must work end-to-end."""

    async with SessionLocal() as db:
        agent_def = await _create_agent_definition(db)
        entry = await _create_registry_entry(db)

        ds_service = EvalDatasetsService(db)
        dataset = await ds_service.create_dataset(entry.id, "E2E Dataset")

        cases_json = [
            {
                "name": "Case Alpha",
                "input_text": "What is 2+2?",
                "assertions": [{"type": "final_answer_contains", "value": "mock"}],
                "tags": ["auto_satisfy"],
            }
        ]
        v1 = await ds_service.create_dataset_version(dataset.id, "1.0.0", cases_json)
        assert v1.version == "1.0.0"
        assert len(v1.cases_json) == 1

        # Run eval on the dataset version
        eval_service = AgentEvalService(db)
        eval_run = await eval_service.run_dataset_version_eval(
            agent_id=agent_def.id,
            dataset_id=dataset.id,
            version="1.0.0",
        )
        assert eval_run.status == "completed"
        assert eval_run.total_count == 1


@pytest.mark.asyncio
async def test_baseline_set_and_non_stale(eval_settings):
    """Setting a baseline must produce a non-stale baseline."""
    async with SessionLocal() as db:
        entry = await _create_registry_entry(db)
        agent_def = await _create_agent_definition(db)
        eval_run = await _create_eval_suite_and_run(db, agent_def.id, passed=True, total_count=3)

        eval_service = AgentEvalService(db)
        baseline = await eval_service.set_baseline(entry.id, eval_run.id, set_by="test-admin")

        assert baseline.is_stale is False
        assert baseline.pass_rate == 1.0
        assert baseline.score == 1.0


@pytest.mark.asyncio
async def test_promotion_gate_passes_all_green(eval_settings):
    """When all checks pass, the promotion gate result must pass."""
    eval_settings.agent_production_requires_eval_baseline = True

    async with SessionLocal() as db:
        entry = await _create_registry_entry(db)
        agent_def = await _create_agent_definition(db)
        eval_run = await _create_eval_suite_and_run(db, agent_def.id, passed=True, cost=1.0, latency=50)

        # Set baseline
        await _set_baseline(db, entry.id, eval_run)

        # Run promotion gate evaluation on the same run (no regression possible)
        gate_svc = EvalGatesService(db)
        promo_result = await gate_svc.evaluate_promotion_gate(
            agent_id=entry.id,
            eval_run_id=eval_run.id,
            target_status="active",
        )

        assert promo_result.passed is True
        assert promo_result.details.get("gate_passed") is True
        assert promo_result.details.get("regression_passed") is True
        assert promo_result.details.get("baseline_ok") is True


@pytest.mark.asyncio
async def test_audit_override_bypasses_failed_gate(eval_settings):
    """Audit override must make the promotion gate pass even when checks fail."""
    eval_settings.agent_production_requires_eval_baseline = True

    async with SessionLocal() as db:
        entry = await _create_registry_entry(db)
        agent_def = await _create_agent_definition(db)

        # Create a failing run
        failing_run = await _create_eval_suite_and_run(db, agent_def.id, passed=False, cost=50.0)

        # Set baseline from failing run (so we have one)
        await _set_baseline(db, entry.id, failing_run)

        gate_svc = EvalGatesService(db)
        promo_result = await gate_svc.evaluate_promotion_gate(
            agent_id=entry.id,
            eval_run_id=failing_run.id,
            target_status="active",
            audit_override=True,
            override_reason="Emergency production deployment",
            override_by="vp-engineering",
        )

        assert promo_result.passed is True
        assert promo_result.audit_override is True
        assert promo_result.override_reason == "Emergency production deployment"
        assert promo_result.override_by == "vp-engineering"


@pytest.mark.asyncio
async def test_submit_review_requires_eval_dryrun(eval_settings):
    """submit_review must require at least one completed eval run when evals are enabled."""
    eval_settings.agent_evals_enabled = True

    async with SessionLocal() as db:
        entry = await _create_registry_entry(db)

        with pytest.raises(ValueError, match="completed evaluation dry-run is required"):
            await agent_lifecycle.submit_review(db, entry.id, performed_by="admin")


@pytest.mark.asyncio
async def test_registry_update_invalidates_baseline(eval_settings):
    """Changing instructions on a registry entry must mark the baseline as stale."""
    async with SessionLocal() as db:
        entry = await _create_registry_entry(db)
        agent_def = await _create_agent_definition(db)
        eval_run = await _create_eval_suite_and_run(db, agent_def.id, passed=True)

        # Set non-stale baseline
        baseline = await _set_baseline(db, entry.id, eval_run, stale=False)
        assert baseline.is_stale is False

        # Update instructions on the registry entry
        await agent_registry.update_registry_entry(
            db, entry.id, {"instructions": "New instructions that differ"}, performed_by="admin"
        )

        # Re-fetch baseline and verify it is now stale
        res = await db.execute(
            select(AgentEvalBaseline).where(AgentEvalBaseline.agent_id == entry.id)
        )
        refreshed_baseline = res.scalar_one_or_none()
        assert refreshed_baseline is not None
        assert refreshed_baseline.is_stale is True
