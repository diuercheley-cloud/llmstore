import uuid
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from unittest.mock import AsyncMock, patch
from decimal import Decimal

from app.api.rag import router as rag_router
from app.api.admin_tests import router as admin_router
from app.db.base import Base
from app.db.session import get_db_session, get_redis
from app.models.client import Client
from app.models.api_key import ApiKey
from app.models.billing_plan import BillingPlan
from app.models.rag_document import RAGDocument
from app.models.client_feature_block import ClientFeatureBlock

@pytest_asyncio.fixture
async def client_and_session(isolated_db_url, fake_redis):
    test_app = FastAPI()
    test_app.include_router(rag_router)
    test_app.include_router(admin_router)
    engine = create_async_engine(isolated_db_url)
    testing_session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db_session():
        async with testing_session_local() as session:
            yield session

    test_app.dependency_overrides[get_db_session] = override_get_db_session
    test_app.dependency_overrides[get_redis] = lambda: fake_redis

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://testserver") as ac:
        yield ac, testing_session_local

    test_app.dependency_overrides.clear()
    await engine.dispose()

@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_rag_document_count_limit(mock_verify, client_and_session):
    async_client, sessionmaker = client_and_session
    
    async with sessionmaker() as session:
        # Create plan with 1 doc limit
        plan = BillingPlan(
            code="test-limited",
            name="Limited",
            rate_limit_per_minute=10,
            daily_token_quota=1000,
            monthly_token_quota=10000,
            max_output_tokens=1000,
            rag_max_documents=1
        )
        session.add(plan)
        await session.commit()
        await session.refresh(plan)
        
        client = Client(name="test-client", billing_status="active", billing_plan_id=plan.id)
        session.add(client)
        await session.commit()
        await session.refresh(client)
        
        prefix = "sk-test-1234"
        api_key = ApiKey(client_id=client.id, name="test", key_prefix=prefix, key_hash="h")
        session.add(api_key)
        
        # Add one doc already
        doc = RAGDocument(
            client_id=client.id,
            filename="existing.pdf",
            original_filename="existing.pdf",
            content_type="application/pdf",
            file_size_bytes=100,
            storage_path="/tmp/existing.pdf"
        )
        session.add(doc)
        await session.commit()
        
        headers = {"Authorization": f"Bearer {prefix}.val"}
        
        # Try to upload second doc
        response = await async_client.post(
            "/v1/rag/files",
            headers=headers,
            files={"file": ("second.pdf", b"%PDF-1.4 content")}
        )
        
        assert response.status_code == 429
        data = response.json()
        assert data["error"] == "rag_limit_exceeded"
        assert data["limit"] == "rag_max_documents"

@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_rag_feature_block(mock_verify, client_and_session):
    async_client, sessionmaker = client_and_session
    
    async with sessionmaker() as session:
        client = Client(name="test-client", billing_status="active")
        session.add(client)
        await session.commit()
        
        prefix = "sk-test-5678"
        api_key = ApiKey(client_id=client.id, name="test", key_prefix=prefix, key_hash="h")
        session.add(api_key)
        
        # Block RAG
        block = ClientFeatureBlock(client_id=client.id, feature="rag", blocked=True, reason="abuse")
        session.add(block)
        await session.commit()
        
        headers = {"Authorization": f"Bearer {prefix}.val"}
        
        # Try to upload
        response = await async_client.post(
            "/v1/rag/files",
            headers=headers,
            files={"file": ("test.pdf", b"%PDF-1.4 content")}
        )
        assert response.status_code == 403
        assert "blocked" in response.json()["detail"]

@pytest.mark.asyncio
@patch("app.services.auth.get_admin_role")
async def test_admin_block_unblock(mock_get_role, client_and_session):
    from app.services.auth import AdminRole
    mock_get_role.return_value = AdminRole.SUPER
    
    async_client, sessionmaker = client_and_session
    
    async with sessionmaker() as session:
        client = Client(name="test-client", billing_status="active")
        session.add(client)
        await session.commit()
        
        headers = {"X-Admin-Token": "super-secret"}
        
        # Block
        response = await async_client.post(
            f"/admin/tests/rag/clients/{client.id}/block",
            headers=headers,
            json={"reason": "test blocking"}
        )
        assert response.status_code == 200
        assert response.json()["blocked"] == True
        
        # Unblock
        response = await async_client.post(
            f"/admin/tests/rag/clients/{client.id}/unblock",
            headers=headers
        )
        assert response.status_code == 200
        assert response.json()["blocked"] == False
