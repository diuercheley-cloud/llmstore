import uuid
import pytest
import pytest_asyncio
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.db.session
from app.db.base import Base
from app.models.agents.agents import AgentDefinition, AgentRun
from app.models.agents.dlp import AgentDLPViolation
from app.services.agents.agent_executor import AgentExecutor, MockLLMProvider
from app.services.security.dlp import dlp_service, DLPBlockException
from app.core.config import get_settings

TEST_DB_FILE = Path("/tmp/test-agent-dlp.db")

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
        try:
            TEST_DB_FILE.unlink()
        except Exception:
            pass

@pytest_asyncio.fixture(autouse=True)
async def setup_settings():
    settings = get_settings()
    orig_obs = settings.agent_observability_enabled
    orig_sandbox = settings.agent_tool_sandbox_enabled
    orig_exec = settings.agent_execution_enabled
    orig_tool_exec = settings.agent_tool_execution_enabled
    orig_executor_mock = settings.agent_executor_mock_mode
    
    settings.agent_observability_enabled = True
    settings.agent_tool_sandbox_enabled = False
    settings.agent_execution_enabled = True
    settings.agent_tool_execution_enabled = True
    settings.agent_executor_mock_mode = False
    
    yield
    
    settings.agent_observability_enabled = orig_obs
    settings.agent_tool_sandbox_enabled = orig_sandbox
    settings.agent_execution_enabled = orig_exec
    settings.agent_tool_execution_enabled = orig_tool_exec
    settings.agent_executor_mock_mode = orig_executor_mock

def test_dlp_cpf_validation():
    # Valid CPF
    assert dlp_service.validate_cpf("123.456.789-09") is True
    # Invalid CPF (wrong checksum)
    assert dlp_service.validate_cpf("123.456.789-10") is False
    # Invalid CPF (same digits)
    assert dlp_service.validate_cpf("111.111.111-11") is False

def test_dlp_card_validation():
    # Valid card number (Visa standard test card passing Luhn)
    assert dlp_service.validate_luhn("4111 1111 1111 1111") is True
    # Invalid card number (fails Luhn)
    assert dlp_service.validate_luhn("4111 1111 1111 1112") is False

def test_dlp_regex_matches():
    # Test email
    findings_email = dlp_service.scan_text_sync("Send email to contact@company.com")
    assert len(findings_email) == 1
    assert findings_email[0]["type"] == "email"

    # Test phone
    findings_phone = dlp_service.scan_text_sync("Call (11) 98765-4321 now")
    assert len(findings_phone) == 1
    assert findings_phone[0]["type"] == "phone"

    # Test JWT
    jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    findings_jwt = dlp_service.scan_text_sync(f"My token is {jwt_token}")
    assert len(findings_jwt) == 1
    assert findings_jwt[0]["type"] == "jwt"

    # Test AWS Access Key ID
    findings_aws = dlp_service.scan_text_sync("My key is AKIAIOSFODNN7EXAMPLE")
    assert len(findings_aws) == 1
    assert findings_aws[0]["type"] == "aws_access_key"

    # Test AWS Secret Key with context word
    findings_aws_sec = dlp_service.scan_text_sync("aws secret key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXUSEKEY40")
    assert len(findings_aws_sec) == 1
    assert findings_aws_sec[0]["type"] == "aws_secret_key"

    # Test AWS Secret Key without context (should be ignored by smart rules to avoid false positives)
    findings_aws_sec_no_context = dlp_service.scan_text_sync("Here is a random 40 char string wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXUSEKEY40")
    assert len(findings_aws_sec_no_context) == 0

@pytest.mark.asyncio
async def test_dlp_ingress_redaction(test_db):
    session_factory = test_db
    async with session_factory() as db:
        # Scan and redact
        text = "Confidential: contact@company.com has CPF 123.456.789-09"
        processed, findings = await dlp_service.scan_text(
            db=db,
            text=text,
            run_id=uuid.uuid4(),
            tenant_id="t1",
            direction="ingress",
            content_type="prompt",
            action="redact"
        )
        
        # Verify text is redacted
        assert "[EMAIL_REDACTED]" in processed
        assert "[CPF_REDACTED]" in processed
        assert "contact@company.com" not in processed
        assert "123.456.789-09" not in processed

        # Check DB log
        stmt = select(AgentDLPViolation)
        res = await db.execute(stmt)
        violations = res.scalars().all()
        
        assert len(violations) == 1
        assert violations[0].direction == "ingress"
        assert violations[0].action_taken == "redact"
        assert len(violations[0].findings) == 2

@pytest.mark.asyncio
async def test_dlp_egress_blocking(test_db):
    session_factory = test_db
    async with session_factory() as db:
        text = "This response contains secret sk-1234567890abcdef1234"
        
        with pytest.raises(DLPBlockException):
            await dlp_service.scan_text(
                db=db,
                text=text,
                run_id=uuid.uuid4(),
                tenant_id="t1",
                direction="egress",
                content_type="response",
                action="block"
            )

        # Check DB log still saved the block event
        stmt = select(AgentDLPViolation)
        res = await db.execute(stmt)
        violations = res.scalars().all()
        
        assert len(violations) == 1
        assert violations[0].direction == "egress"
        assert violations[0].action_taken == "block"

@pytest.mark.asyncio
async def test_dlp_ingress_and_egress_executor_integration(test_db):
    session_factory = test_db
    async with session_factory() as db:
        agent = AgentDefinition(
            id=uuid.uuid4(), name="DLP Agent", tenant_id="t1", status="active",
            instructions="Handle requests", model_id="gpt-3.5", owner="admin", version="1.0.0"
        )
        # Ingress prompt has email and CPF
        run = AgentRun(
            id=uuid.uuid4(), agent_id=agent.id, tenant_id="t1", status="running",
            input_text="My contact is contact@company.com and CPF is 123.456.789-09",
            total_steps=0, total_tokens=0, estimated_cost_brl=0.0
        )
        db.add(agent)
        db.add(run)
        
        # Add a dummy tool to database
        from app.models.agents.agents import AgentTool
        tool = AgentTool(
            id=uuid.uuid4(), name="bad_tool", description="D", 
            category="test", input_schema_json={}, output_schema_json={},
            enabled=True
        )
        db.add(tool)
        await db.commit()

        # Mock LLM to return final response containing sensitive credit card (egress leak)
        mock_llm = MockLLMProvider([
            {"type": "final", "output": "Approved card: 4532 7153 9012 3456"}
        ])
        
        executor = AgentExecutor(db, run.id, llm_provider=mock_llm)
        
        # Run step - triggers ingress redaction and LLM decision egress redaction
        await executor.execute_step()
        await db.commit()

        # Reload run and check redacted input
        await db.refresh(run)
        assert "[EMAIL_REDACTED]" in run.input_text
        assert "[CPF_REDACTED]" in run.input_text
        assert "contact@company.com" not in run.input_text

        # Verify logged steps
        stmt_violations = select(AgentDLPViolation).order_by(AgentDLPViolation.created_at.asc())
        res_v = await db.execute(stmt_violations)
        violations = res_v.scalars().all()
        
        # Violations logged: 1 for ingress prompt, 1 for egress response
        assert len(violations) == 2
        assert violations[0].direction == "ingress"
        assert violations[1].direction == "egress"
