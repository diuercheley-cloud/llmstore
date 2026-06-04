import os
import uuid
from unittest.mock import patch

import pytest
import pytest_asyncio
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.agent_optimization import (
    AgentPolicyCandidate,
    AgentPromptCandidate,
    AgentToolSelectionCandidate,
)
from app.models.agents import (
    AgentDefinition,
    AgentEvalFailure,
)
from app.services.agents.optimization.optimization_experiments import OptimizationExperimentService
from app.services.agents.optimization.optimizer import AgentOptimizerCoordinator
from sqlalchemy import select


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session():
    async with SessionLocal() as session:
        yield session

@pytest_asyncio.fixture
async def sample_agent(db_session):
    agent = AgentDefinition(
        id=uuid.uuid4(),
        name="AutoOptimizingAgent",
        version="1.0.0",
        instructions="Analyze data and output summary.",
        model_id="gpt-4",
        owner="ml-team",
        tenant_id="tenant-opt",
        allowed_tools=["github", "slack"]
    )
    db_session.add(agent)
    await db_session.commit()
    return agent

@pytest.mark.asyncio
async def test_optimizer_disabled_blocks(db_session, sample_agent):
    coordinator = AgentOptimizerCoordinator(db_session)

    # Disable optimization flag
    with patch.dict(os.environ, {"AGENT_AUTO_OPTIMIZATION_ENABLED": "false"}):
        get_settings.cache_clear()
        with pytest.raises(PermissionError):
            await coordinator.run_optimization_experiment("tenant-opt", sample_agent.id)
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_candidate_generation_from_failures(db_session, sample_agent):
    coordinator = AgentOptimizerCoordinator(db_session)

    # 1. Create a failed eval entry to feed the optimizer
    failure = AgentEvalFailure(
        agent_id=sample_agent.id,
        run_id=uuid.uuid4(),
        failure_type="secret_leak",
        details={"tool_name": "github", "reason": "Secret API key leaked in output"}
    )
    db_session.add(failure)
    await db_session.commit()

    # 2. Run experiment
    experiment, candidates = await coordinator.run_optimization_experiment("tenant-opt", sample_agent.id)
    await db_session.commit()

    assert experiment.status == "completed"
    assert len(candidates) == 3  # prompt, tool selection, policy candidates

    # Verify prompt candidate is tweaked based on secret leak
    prompt_cand = next(c for c in candidates if c.candidate_type == "prompt")
    stmt = select(AgentPromptCandidate).where(AgentPromptCandidate.candidate_id == prompt_cand.id)
    res = await db_session.execute(stmt)
    prompt_detail = res.scalar_one()
    assert "SAFETY: Redact all API keys, tokens, or credentials" in prompt_detail.prompt_text

    # Verify tool selection candidate is generated
    tool_cand = next(c for c in candidates if c.candidate_type == "tool_selection")
    stmt_t = select(AgentToolSelectionCandidate).where(AgentToolSelectionCandidate.candidate_id == tool_cand.id)
    res_t = await db_session.execute(stmt_t)
    tool_detail = res_t.scalar_one()
    assert "github" in tool_detail.allowed_tools

@pytest.mark.asyncio
async def test_candidate_eval_and_deltas(db_session, sample_agent):
    coordinator = AgentOptimizerCoordinator(db_session)
    service = OptimizationExperimentService(db_session)

    # Create failure
    failure = AgentEvalFailure(
        agent_id=sample_agent.id,
        run_id=uuid.uuid4(),
        failure_type="tool_error",
        details={"tool_name": "github"}
    )
    db_session.add(failure)
    await db_session.commit()

    # Run experiment
    experiment, candidates = await coordinator.run_optimization_experiment("tenant-opt", sample_agent.id)
    await db_session.commit()

    # Evaluate the prompt candidate
    prompt_cand = next(c for c in candidates if c.candidate_type == "prompt")
    result = await service.evaluate_candidate(prompt_cand.id)
    await db_session.commit()

    assert result is not None
    assert "eval_pass_rate_delta" in result.metrics_delta
    assert "safety_failure_delta" in result.metrics_delta
    assert prompt_cand.status == "completed"

@pytest.mark.asyncio
async def test_approval_requirement_and_promotion_gate(db_session, sample_agent):
    coordinator = AgentOptimizerCoordinator(db_session)
    service = OptimizationExperimentService(db_session)

    # Create a failed eval entry to feed the optimizer
    failure = AgentEvalFailure(
        agent_id=sample_agent.id,
        run_id=uuid.uuid4(),
        failure_type="secret_leak",
        details={"tool_name": "github", "reason": "Secret API key leaked in output"}
    )
    db_session.add(failure)
    await db_session.commit()

    # Run experiment
    experiment, candidates = await coordinator.run_optimization_experiment("tenant-opt", sample_agent.id)
    await db_session.commit()

    prompt_cand = next(c for c in candidates if c.candidate_type == "prompt")
    
    # 1. Evaluate candidate
    await service.evaluate_candidate(prompt_cand.id)
    await db_session.commit()

    # 2. Applying without approval fails
    with pytest.raises(PermissionError) as exc:
        await service.apply_optimization(prompt_cand.id)
    assert "Requires explicit approval" in str(exc.value)

    # 3. Approve candidate
    await service.approve_candidate(prompt_cand.id)
    await db_session.commit()

    # 4. Applying succeeds after approval
    applied_cand = await service.apply_optimization(prompt_cand.id)
    await db_session.commit()

    assert applied_cand.status == "applied"

    # Verify agent definition was actually updated
    res_agent = await db_session.execute(select(AgentDefinition).where(AgentDefinition.id == sample_agent.id))
    updated_agent = res_agent.scalar_one()
    assert "Compiled Directives (DSPy-Optimized)" in updated_agent.instructions

@pytest.mark.asyncio
async def test_safety_regression_gate_blocks(db_session, sample_agent):
    coordinator = AgentOptimizerCoordinator(db_session)
    service = OptimizationExperimentService(db_session)

    # Run experiment
    experiment, candidates = await coordinator.run_optimization_experiment("tenant-opt", sample_agent.id)
    await db_session.commit()

    # Set up candidate with simulate_safety_regression flag inside policy rules
    pol_cand = next(c for c in candidates if c.candidate_type == "policy")
    stmt = select(AgentPolicyCandidate).where(AgentPolicyCandidate.candidate_id == pol_cand.id)
    res = await db_session.execute(stmt)
    pol_detail = res.scalar_one()
    pol_detail.policy_rules = {"simulate_safety_regression": True}
    await db_session.commit()

    # 1. Evaluate candidate
    await service.evaluate_candidate(pol_cand.id)
    await db_session.commit()

    assert pol_cand.safety_regression is True

    # 2. Approve candidate
    await service.approve_candidate(pol_cand.id)
    await db_session.commit()

    # 3. Applying candidate fails because safety regression blocks the gate
    with pytest.raises(PermissionError) as exc:
        await service.apply_optimization(pol_cand.id)
    assert "fails optimization gate checks" in str(exc.value)
