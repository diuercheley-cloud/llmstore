import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.security.runtime_attestation import create_runtime_attestation, verify_runtime_attestation, compute_trust_score
from app.services.security.runtime_integrity import (
    block_untrusted_runtimes,
    require_attestation_for_sensitive_tenants,
    require_attestation_for_sovereign,
)


@pytest.mark.asyncio
async def test_block_untrusted_enforce_mode(session: AsyncSession):
    await create_runtime_attestation(
        session,
        cluster_id="cluster-block",
        node_id="untrusted-node",
    )
    with pytest.raises(ValueError, match="untrusted runtime"):
        await block_untrusted_runtimes(session, cluster_id="cluster-block", mode="enforce")


@pytest.mark.asyncio
async def test_block_untrusted_report_only(session: AsyncSession):
    await create_runtime_attestation(
        session,
        cluster_id="cluster-report",
        node_id="node-unknown",
    )
    result = await block_untrusted_runtimes(session, cluster_id="cluster-report", mode="report_only")
    assert result["allowed"] is True


@pytest.mark.asyncio
async def test_block_untrusted_disabled(session: AsyncSession):
    result = await block_untrusted_runtimes(session, cluster_id="cluster-disabled", mode="disabled")
    assert result["allowed"] is False


@pytest.mark.asyncio
async def test_sovereign_attestation_requirement(session: AsyncSession):
    with pytest.MonkeyPatch().context() as mp:
        from app.core.config import get_settings
        get_settings.cache_clear()
        mp.setenv("COMMERCIAL_RUNTIME_ATTESTATION_REQUIRE_FOR_SOVEREIGN", "true")
        mp.setenv("COMMERCIAL_RUNTIME_ATTESTATION_ENABLED", "true")

        result = await require_attestation_for_sovereign(
            session,
            cluster_id="cluster-sovereign",
        )


@pytest.mark.asyncio
async def test_sensitive_tenant_attestation_flow(session: AsyncSession):
    with pytest.MonkeyPatch().context() as mp:
        from app.core.config import get_settings
        get_settings.cache_clear()
        mp.setenv("COMMERCIAL_RUNTIME_ATTESTATION_REQUIRE_FOR_SENSITIVE_TENANTS", "true")
        mp.setenv("COMMERCIAL_RUNTIME_ATTESTATION_ENABLED", "true")

        await create_runtime_attestation(
            session,
            cluster_id="cluster-sensitive",
            tenant_id="sensitive-tenant",
        )

        result = await require_attestation_for_sensitive_tenants(
            session,
            tenant_id="sensitive-tenant",
            cluster_id="cluster-sensitive",
        )


@pytest.mark.asyncio
async def test_runtime_attestation_chain_of_trust(session: AsyncSession):
    r1 = await create_runtime_attestation(session, cluster_id="chain-cluster", node_id="node-1")
    await verify_runtime_attestation(session, r1.id)
    await compute_trust_score(session, r1.id)

    r2 = await create_runtime_attestation(
        session,
        cluster_id="chain-cluster",
        node_id="node-1",
        previous_attestation_id=r1.id,
    )
    assert r2.previous_hash == r1.immutable_hash
    assert r2.immutable_hash != r1.immutable_hash


@pytest.mark.asyncio
async def test_untrusted_runtime_detection_via_policy(session: AsyncSession):
    record = await create_runtime_attestation(
        session,
        cluster_id="cluster-enforce",
        enclave_type="software_attested",
    )
    await verify_runtime_attestation(session, record.id)
    await compute_trust_score(session, record.id)

    with pytest.MonkeyPatch().context() as mp:
        from app.core.config import get_settings
        get_settings.cache_clear()
        mp.setenv("COMMERCIAL_RUNTIME_ATTESTATION_MODE", "enforce")
        mp.setenv("COMMERCIAL_RUNTIME_ATTESTATION_ENABLED", "true")

        result = await block_untrusted_runtimes(
            session,
            cluster_id="cluster-enforce",
        )


@pytest.mark.asyncio
async def test_evidence_replay_protection(session: AsyncSession):
    from app.services.security.attestation_challenges import issue_challenge, respond_to_challenge

    challenge = await issue_challenge(
        session,
        cluster_id="cluster-replay",
        node_id="node-replay",
    )
    assert challenge.status == "pending"
    assert challenge.response_received is False

    from app.core.time import utc_now
    from datetime import timedelta
    challenge.expires_at = utc_now() - timedelta(seconds=1)
    await session.flush()
    with pytest.raises(ValueError, match="Challenge has expired"):
        await respond_to_challenge(
            session,
            challenge.id,
            {"nonce": challenge.challenge_data_json["nonce"], "response_hash": "placeholder"},
        )
