import pytest
import pytest_asyncio
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.core.config import get_settings
from app.core.time import utc_now
from app.models.agents import (
    AgentDefinition,
    AgentRegistryEntry,
    AgentEvalSuite,
    AgentEvalCase,
    AgentEvalRun,
    AgentEvalResult,
    AgentEvalBaseline,
    AgentEvalDataset,
    AgentEvalDatasetVersion,
    AgentEvalFailure,
    AgentRun,
    AgentRunStep,
)
from app.services.agents.eval_gate import EvalGateService
from app.services.agents.eval_dataset_registry import EvalDatasetRegistryService

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        import app.models.agents  # noqa
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

async def _create_test_data(db: AsyncSession):
    agent_def = AgentDefinition(
        id=uuid.uuid4(),
        name="GateTestAgent",
        version="1.0.0",
        instructions="test",
        model_id="mock-model",
        owner="test",
        tenant_id="test-tenant",
        status="active"
    )
    db.add(agent_def)
    
    entry = AgentRegistryEntry(
        id=uuid.uuid4(),
        agent_id=agent_def.id,
        name="GateTestAgent",
        semantic_version="1.0.0",
        owner="test",
        status="draft",
        instructions="test"
    )
    db.add(entry)
    await db.commit()
    return entry, agent_def

async def _create_run(
    db: AsyncSession, 
    agent_id: uuid.UUID, 
    passed: bool = True, 
    is_golden: bool = False, 
    has_secret: bool = False, 
    provider: str = "gateway",
    has_mock_final_answer: bool = False
):
    suite = AgentEvalSuite(id=uuid.uuid4(), agent_id=agent_id, name="Test Suite")
    db.add(suite)
    await db.flush()
    
    case = AgentEvalCase(
        id=uuid.uuid4(), 
        suite_id=suite.id, 
        name="Test Case", 
        input_text="test", 
        input_hash="hash",
        is_golden=is_golden
    )
    db.add(case)
    await db.flush()
    
    run = AgentEvalRun(
        id=uuid.uuid4(), 
        suite_id=suite.id, 
        status="completed", 
        passed_count=1 if passed else 0,
        failed_count=0 if passed else 1,
        total_count=1,
        metadata_json={"provider": provider}
    )
    db.add(run)
    await db.flush()

    agent_run_id = None
    if has_mock_final_answer:
        agent_run = AgentRun(
            id=uuid.uuid4(),
            agent_id=agent_id,
            tenant_id="test-tenant",
            input_text="test",
            status="completed",
        )
        db.add(agent_run)
        await db.flush()
        agent_run_id = agent_run.id

        final_step = AgentRunStep(
            id=uuid.uuid4(),
            run_id=agent_run.id,
            step_number=1,
            step_type="final",
            input_hash="mock-hash",
            output_hash="mock-hash",
            step_metadata={"mock": True}
        )
        db.add(final_step)
        await db.flush()
    
    result = AgentEvalResult(
        id=uuid.uuid4(),
        run_id=run.id,
        case_id=case.id,
        passed=passed,
        assertion_results=[{"type": "output", "passed": True, "message": "SECRET_KEY" if has_secret else "ok"}],
        run_id_ref=agent_run_id
    )
    db.add(result)
    await db.commit()
    return run

@pytest.mark.asyncio
async def test_dataset_version_immutability():
    async with SessionLocal() as db:
        entry, _ = await _create_test_data(db)
        svc = EvalDatasetRegistryService(db)
        ds = await svc.create_dataset(entry.id, "Test DS")
        
        await svc.create_dataset_version(ds.id, "1.0.0", [{"name": "case1"}])
        
        with pytest.raises(ValueError, match="already exists and is immutable"):
            await svc.create_dataset_version(ds.id, "1.0.0", [{"name": "case1"}])

@pytest.mark.asyncio
async def test_promotion_gate_blocks_no_baseline():
    settings = get_settings()
    settings.agent_production_requires_eval_baseline = True
    
    async with SessionLocal() as db:
        entry, _ = await _create_test_data(db)
        run = await _create_run(db, entry.id)
        
        svc = EvalGateService(db)
        with pytest.raises(ValueError, match="baseline first"):
            await svc.evaluate_promotion(entry.id, run.id)

@pytest.mark.asyncio
async def test_promotion_gate_blocks_golden_failure():
    async with SessionLocal() as db:
        entry, _ = await _create_test_data(db)
        # Golden task fails
        run = await _create_run(db, entry.id, passed=False, is_golden=True)
        
        # Set a baseline first to avoid baseline error
        baseline = AgentEvalBaseline(
            agent_id=entry.id, run_id=run.id, score=1.0, pass_rate=1.0, version="1.0.0", set_by="test"
        )
        db.add(baseline)
        await db.commit()
        
        svc = EvalGateService(db)
        res = await svc.evaluate_promotion(entry.id, run.id)
        assert res.passed is False
        assert res.details["gate_details"]["golden_failed"] is True

@pytest.mark.asyncio
async def test_promotion_gate_blocks_secret_leak():
    async with SessionLocal() as db:
        entry, _ = await _create_test_data(db)
        run = await _create_run(db, entry.id, passed=True, has_secret=True)
        
        baseline = AgentEvalBaseline(
            agent_id=entry.id, run_id=run.id, score=1.0, pass_rate=1.0, version="1.0.0", set_by="test"
        )
        db.add(baseline)
        await db.commit()
        
        svc = EvalGateService(db)
        res = await svc.evaluate_promotion(entry.id, run.id)
        assert res.passed is False
        assert res.details["gate_details"]["secret_leak_detected"] is True


@pytest.mark.asyncio
async def test_mock_provider_allowed_in_ci():
    settings = get_settings()
    orig = settings.agent_eval_allow_mock_for_promotion
    try:
        async with SessionLocal() as db:
            entry, _ = await _create_test_data(db)
            run = await _create_run(db, entry.id, passed=True, provider="mock")
            
            baseline = AgentEvalBaseline(
                agent_id=entry.id, run_id=run.id, score=1.0, pass_rate=1.0, version="1.0.0", set_by="test"
            )
            db.add(baseline)
            await db.commit()
            
            svc = EvalGateService(db)
            
            res = await svc.evaluate_promotion(entry.id, run.id, target_status="review")
            assert res.passed is True
            
            settings.agent_eval_allow_mock_for_promotion = True
            res = await svc.evaluate_promotion(entry.id, run.id, target_status="active")
            assert res.passed is True
    finally:
        settings.agent_eval_allow_mock_for_promotion = orig


@pytest.mark.asyncio
async def test_promotion_with_mock_blocks():
    settings = get_settings()
    orig = settings.agent_eval_allow_mock_for_promotion
    settings.agent_eval_allow_mock_for_promotion = False
    try:
        async with SessionLocal() as db:
            entry, _ = await _create_test_data(db)
            run = await _create_run(db, entry.id, passed=True, provider="mock")
            
            baseline = AgentEvalBaseline(
                agent_id=entry.id, run_id=run.id, score=1.0, pass_rate=1.0, version="1.0.0", set_by="test"
            )
            db.add(baseline)
            await db.commit()
            
            svc = EvalGateService(db)
            res = await svc.evaluate_promotion(entry.id, run.id, target_status="active")
            assert res.passed is False
            assert res.details["promotion_allowed"] is False
            assert res.details["production_ready"] is False
    finally:
        settings.agent_eval_allow_mock_for_promotion = orig


@pytest.mark.asyncio
async def test_gateway_eval_uses_agent_runtime():
    from app.services.agents.agent_evals import get_eval_provider, GatewayEvalProvider
    provider = get_eval_provider("gateway")
    assert isinstance(provider, GatewayEvalProvider)


@pytest.mark.asyncio
async def test_eval_report_includes_provider():
    async with SessionLocal() as db:
        entry, _ = await _create_test_data(db)
        run = await _create_run(db, entry.id, passed=True, provider="gateway")
        
        baseline = AgentEvalBaseline(
            agent_id=entry.id, run_id=run.id, score=1.0, pass_rate=1.0, version="1.0.0", set_by="test"
        )
        db.add(baseline)
        await db.commit()
        
        svc = EvalGateService(db)
        res = await svc.evaluate_promotion(entry.id, run.id, target_status="active")
        assert res.passed is True
        
        from pathlib import Path
        report_path = Path("artifacts/agent-evals/latest/promotion-gate-report.md")
        assert report_path.exists()
        report_content = report_path.read_text(encoding="utf-8")
        assert "**Provider:** gateway" in report_content


@pytest.mark.asyncio
async def test_mock_final_answer_fails_as_real():
    async with SessionLocal() as db:
        entry, _ = await _create_test_data(db)
        run = await _create_run(db, entry.id, passed=True, provider="gateway", has_mock_final_answer=True)
        
        baseline = AgentEvalBaseline(
            agent_id=entry.id, run_id=run.id, score=1.0, pass_rate=1.0, version="1.0.0", set_by="test"
        )
        db.add(baseline)
        await db.commit()
        
        svc = EvalGateService(db)
        res = await svc.evaluate_promotion(entry.id, run.id, target_status="active")
        assert res.passed is False
        assert res.details["gate_details"]["mock_answer_violation"] is True


@pytest.mark.asyncio
async def test_safety_failure_blocks_promotion_under_strict_gate():
    settings = get_settings()
    orig_strict = settings.agent_eval_gate_strict
    settings.agent_eval_gate_strict = True
    try:
        async with SessionLocal() as db:
            entry, _ = await _create_test_data(db)
            run = await _create_run(db, entry.id, passed=True, has_secret=True)
            
            baseline = AgentEvalBaseline(
                agent_id=entry.id, run_id=run.id, score=1.0, pass_rate=1.0, version="1.0.0", set_by="test"
            )
            db.add(baseline)
            await db.commit()
            
            svc = EvalGateService(db)
            res = await svc.evaluate_promotion(
                entry.id, 
                run.id, 
                target_status="active", 
                audit_override=True, 
                override_reason="emergency", 
                override_by="admin"
            )
            assert res.passed is False
            assert res.details["gate_details"]["secret_leak_detected"] is True
    finally:
        settings.agent_eval_gate_strict = orig_strict
