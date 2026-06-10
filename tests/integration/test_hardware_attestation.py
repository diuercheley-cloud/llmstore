import pytest
from app.services.security.hardware_attestation import (
    collect_attestation_placeholder,
    enforce_attestation_policy,
    summarize_attestation_status,
    verify_attestation_record,
)
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_attestation_placeholder_and_summary(session: AsyncSession):
    record = await collect_attestation_placeholder(
        session,
        cluster_id="cluster-a",
        node_id="node-1",
        evidence_json={"boot": "placeholder", "secret": "token=should-redact"},
        status="unknown",
    )
    assert record.evidence_hash
    assert "should-redact" not in str(record.evidence_json)

    verified = await verify_attestation_record(session, record.id)
    assert verified.status == "trusted"

    summary = await summarize_attestation_status(session)
    assert summary["total_records"] >= 1
    assert summary["status_counts"].get("trusted", 0) >= 1


@pytest.mark.asyncio
async def test_untrusted_enforcement_blocks(session: AsyncSession):
    await collect_attestation_placeholder(
        session,
        cluster_id="cluster-b",
        node_id="node-9",
        evidence_json={"boot": "placeholder"},
        status="untrusted",
    )
    with pytest.raises(ValueError, match="untrusted node present"):
        await enforce_attestation_policy(session, cluster_id="cluster-b", mode="enforce")

    result = await enforce_attestation_policy(session, cluster_id="cluster-b", mode="report_only")
    assert result["allowed"] is True
    assert result["status"] == "untrusted"
