import sys
from pathlib import Path

import pytest
import pytest_asyncio
from app.db.base import Base
from app.models.core.client import Client
from app.models.commercial.commercial_rag_vault_vault import CommercialRAGRetrievalAudit, CommercialRAGVault
from app.services.rag.retrieval_proofs import (
    export_retrieval_proof,
    generate_retrieval_proof,
    replay_retrieval_proof,
    verify_lineage_consistency,
    verify_retrieval_proof,
)
from app.services.rag_enterprise.schemas import EnterpriseSource
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TOOLS_ROOT = Path(__file__).resolve().parents[2] / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))
from public_verifier.verifier_core import Verifier


@pytest_asyncio.fixture
async def session(isolated_db_url):
    engine = create_async_engine(isolated_db_url)
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with Session() as s:
        yield s
    await engine.dispose()


async def _build_proof(session: AsyncSession):
    client = Client(name="tenant")
    session.add(client)
    await session.flush()
    vault = CommercialRAGVault(client_id=client.id, vault_name="regulated", vault_mode="confidential", encryption_required=True, retrieval_mode="hybrid")
    session.add(vault)
    await session.flush()
    audit = CommercialRAGRetrievalAudit(
        vault_id=vault.id,
        client_id=client.id,
        request_hash="req-hash",
        retrieval_hash="retrieval-hash",
        user_identity_hash="user-hash",
        retrieved_chunk_count=2,
        policy_result="allow",
        model_id="local-model",
        immutable_hash="immutable-hash",
    )
    session.add(audit)
    await session.flush()
    sources = [
        EnterpriseSource(document_id=audit.id, filename="a.txt", page=1, chunk_index=0, text="alpha context", score=0.9),
        EnterpriseSource(document_id=vault.id, filename="b.txt", page=2, chunk_index=1, text="beta context", score=0.8),
    ]
    proof = await generate_retrieval_proof(
        session,
        vault=vault,
        audit=audit,
        sources=sources,
        retrieval_metadata={"policy_result": "allow", "violations": [], "governed": True, "max_context_chunks": 5},
        model_id="local-model",
    )
    await session.commit()
    return proof


@pytest.mark.asyncio
async def test_merkle_inclusion_and_lineage_integrity(session: AsyncSession):
    proof = await _build_proof(session)
    result = await verify_retrieval_proof(session, proof)
    assert result["merkle_valid"] is True
    assert result["lineage_valid"] is True
    assert await verify_lineage_consistency(session, proof) is True


@pytest.mark.asyncio
async def test_retrieval_replay_detects_drift(session: AsyncSession):
    proof = await _build_proof(session)
    replay = await replay_retrieval_proof(
        session,
        proof=proof,
        replay_sources=[
            {"document_id": proof.proof_json["chunk_participants"][0]["document_id"], "chunk_index": 0, "text_hash": proof.proof_json["chunk_participants"][0]["text_hash"]},
            {"document_id": "drift-doc", "chunk_index": 99, "text_hash": "deadbeef"},
        ],
    )
    await session.commit()
    assert replay.replay_status == "drift_detected"
    assert replay.drift_score and replay.drift_score > 0


@pytest.mark.asyncio
async def test_proof_export_import_verifier_validation(session: AsyncSession):
    proof = await _build_proof(session)
    exported = await export_retrieval_proof(session, proof)
    verifier = Verifier(exported)
    verifier.run_all_checks()
    assert verifier.get_overall_status() in {"VALID", "PARTIAL"}
    assert not any("Proof hash mismatch" in err for err in verifier.errors)


@pytest.mark.asyncio
async def test_public_gateway_style_verification(session: AsyncSession):
    proof = await _build_proof(session)
    result = await verify_retrieval_proof(session, proof)
    assert result["valid"] is True
