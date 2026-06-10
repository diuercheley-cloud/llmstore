import uuid
from pathlib import Path

import app.db.session
import pytest
import pytest_asyncio
from app.db.base import Base
from app.models.agents.agents import (
    AgentDefinition,
    AgentEvalBaseline,
    AgentIncident,
)
from app.services.agents.promotion_gate import AgentPromotionService
from app.services.agents.prompt_baseline_registry import PromptBaselineRegistry
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Force SQLite for tests
TEST_DB_FILE = Path("/tmp/test-promotion-gates.db")

@pytest_asyncio.fixture(autouse=True)
async def test_db():
    db_url = f"sqlite+aiosqlite:///{TEST_DB_FILE}"
    engine = create_async_engine(db_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    app.db.session.engine = engine
    app.db.session.SessionLocal = session_factory
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield session_factory
    
    await engine.dispose()
    if TEST_DB_FILE.exists():
        try: TEST_DB_FILE.unlink()
        except: pass

@pytest.mark.asyncio
async def test_promotion_fails_without_eval(test_db):
    async with test_db() as db:
        agent = AgentDefinition(
            id=uuid.uuid4(), name="Agent", tenant_id="t1", status="draft",
            instructions="I", model_id="m", owner="admin", version="1.0.0"
        )
        db.add(agent)
        await db.commit()
        
        service = AgentPromotionService(db)
        result = await service.run_promotion_check(agent.id, "active")
        
        assert result["passed"] is False
        assert result["checks"]["eval_baseline"] is False

@pytest.mark.asyncio
async def test_promotion_fails_with_critical_incident(test_db):
    async with test_db() as db:
        agent = AgentDefinition(id=uuid.uuid4(), name="A", tenant_id="t1", status="draft", instructions="I", model_id="m", owner="o", version="1.0.0")
        db.add(agent)
        
        # Passed eval
        eb = AgentEvalBaseline(
            agent_id=agent.id, 
            run_id=uuid.uuid4(),
            score=0.9,
            pass_rate=0.9,
            version="1.0.0",
            set_by="admin"
        )
        db.add(eb)
        
        # Critical incident
        incident = AgentIncident(
            agent_id=agent.id, 
            tenant_id="t1",
            severity="critical", 
            status="open", 
            incident_type="test",
            title="Leak"
        )
        db.add(incident)
        
        # Valid baseline
        registry = PromptBaselineRegistry(db)
        await registry.create_baseline(agent.id, agent.instructions)
        
        await db.commit()
        
        service = AgentPromotionService(db)
        result = await service.run_promotion_check(agent.id, "active")
        
        assert result["passed"] is False
        assert result["checks"]["no_critical_incidents"] is False

@pytest.mark.asyncio
async def test_promotion_fails_when_prompt_changed(test_db):
    async with test_db() as db:
        agent = AgentDefinition(id=uuid.uuid4(), name="A", tenant_id="t1", status="draft", instructions="Old", model_id="m", owner="o", version="1.0.0")
        db.add(agent)
        
        eb = AgentEvalBaseline(
            agent_id=agent.id, 
            run_id=uuid.uuid4(),
            score=0.9,
            pass_rate=0.9,
            version="1.0.0",
            set_by="admin"
        )
        db.add(eb)
        
        # Create baseline for "Old" instructions
        registry = PromptBaselineRegistry(db)
        await registry.create_baseline(agent.id, "Old")
        
        # Change prompt
        agent.instructions = "New and improved"
        await db.commit()
        
        service = AgentPromotionService(db)
        result = await service.run_promotion_check(agent.id, "active")
        
        assert result["passed"] is False
        assert result["checks"]["prompt_freshness"] is False
