import uuid

import pytest
import pytest_asyncio
from app.db.base import Base
from app.models.client import Client
from app.models.commercial_rag_vault_vault import (
    CommercialRAGAccessPolicy,
    CommercialRAGDocument,
    CommercialRAGLegalHold,
    CommercialRAGVault,
)
from app.services.rag.rag_access_control import (
    RetrievalAccessDenied,
    evaluate_chunk_acl,
    evaluate_retrieval_access,
    validate_document_access,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def session(isolated_db_url):
    engine = create_async_engine(isolated_db_url)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with Session() as s:
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_cross_tenant_blocked(session: AsyncSession):
    owner = Client(name="owner")
    other = Client(name="other")
    session.add_all([owner, other])
    await session.flush()

    vault = CommercialRAGVault(client_id=owner.id, vault_name="tenant-vault", vault_mode="confidential", encryption_required=True, retrieval_mode="hybrid")
    session.add(vault)
    await session.flush()
    session.add(
        CommercialRAGAccessPolicy(
            vault_id=vault.id,
            policy_name="strict",
            policy_mode="enforce",
            allow_cross_tenant=False,
            require_abac=True,
            max_context_chunks=5,
        )
    )
    await session.commit()

    with pytest.raises(RetrievalAccessDenied) as exc:
        await evaluate_retrieval_access(
            session,
            vault=vault,
            request_client_id=other.id,
            requested_model="regulated-model",
            user_identity="user-a",
            abac_attributes={"role": "tenant_user", "purpose": "support"},
        )
    assert "cross_tenant_blocked" in exc.value.reason


@pytest.mark.asyncio
async def test_signed_document_and_legal_hold_enforced(session: AsyncSession):
    client = Client(name="regulated")
    session.add(client)
    await session.flush()
    vault = CommercialRAGVault(client_id=client.id, vault_name="tenant-vault", vault_mode="confidential", encryption_required=True, retrieval_mode="hybrid")
    session.add(vault)
    await session.flush()
    policy = CommercialRAGAccessPolicy(
        vault_id=vault.id,
        policy_name="strict",
        policy_mode="enforce",
        require_signed_document=True,
        max_context_chunks=5,
    )
    session.add(policy)
    await session.flush()
    document = CommercialRAGDocument(
        vault_id=vault.id,
        document_hash="doc-hash",
        document_title="Restricted Doc",
        classification="restricted",
        ingestion_status="indexed",
        source_type="upload",
        signed_manifest_hash=None,
        legal_hold=True,
        metadata_json={},
    )
    session.add(document)
    await session.flush()
    session.add(
        CommercialRAGLegalHold(
            vault_id=vault.id,
            document_id=document.id,
            hold_reason="case preservation",
            active=True,
        )
    )
    await session.commit()

    violations = await validate_document_access(session, document=document, policy=policy)
    assert "unsigned_document" in violations
    assert "document_legal_hold" in violations
    assert "active_legal_hold" in violations


def test_acl_enforcement():
    violations = evaluate_chunk_acl(
        {
            "allowed_client_ids": [str(uuid.uuid4())],
            "allowed_roles": ["tenant_admin"],
            "allowed_user_hashes": ["allowed-user"],
        },
        request_client_id=uuid.uuid4(),
        user_identity="blocked-user",
        abac_attributes={"role": "tenant_user"},
    )
    assert "acl_client_mismatch" in violations
    assert "acl_role_mismatch" in violations
    assert "acl_user_mismatch" in violations
