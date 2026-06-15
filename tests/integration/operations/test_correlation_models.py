import uuid

import pytest
from app.core.time import utc_now
from app.models.operations.correlation import (
    CorrelatedOperationalEvent,
    OperationalCorrelation,
    OperationalTrustLink,
    compute_deterministic_hash,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class TestCorrelationDeterministicHash:
    def test_deterministic_same_input(self):
        fields = {"client_id": str(uuid.uuid4()), "type": "auth_failure_inference_impact"}
        h1 = compute_deterministic_hash(fields=fields)
        h2 = compute_deterministic_hash(fields=fields)
        assert h1 == h2

    def test_deterministic_different_input(self):
        h1 = compute_deterministic_hash(fields={"a": 1})
        h2 = compute_deterministic_hash(fields={"a": 2})
        assert h1 != h2

    def test_output_format(self):
        h = compute_deterministic_hash(fields={"x": 1})
        assert isinstance(h, str)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


@pytest.mark.asyncio
class TestCorrelationModels:
    async def test_create_operational_correlation(self, session: AsyncSession):
        client_id = uuid.uuid4()
        correlation = OperationalCorrelation(
            client_id=client_id,
            correlation_type="latency_vs_billing",
            source_domains_json=["billing", "runtime"],
            correlation_key="client_X_spike",
            correlation_score=0.85,
            confidence=0.9,
            immutable_hash="hash123",
            previous_hash="prev123",
        )
        session.add(correlation)
        await session.commit()

        result = await session.execute(
            select(OperationalCorrelation).where(OperationalCorrelation.client_id == client_id)
        )
        saved = result.scalars().one()
        assert saved.correlation_type == "latency_vs_billing"
        assert saved.source_domains_json == ["billing", "runtime"]
        assert saved.advisory_only is True  # Default
        assert saved.immutable_hash == "hash123"
        assert saved.previous_hash == "prev123"

    async def test_create_correlated_event(self, session: AsyncSession):
        client_id = uuid.uuid4()
        correlation_id = uuid.uuid4()

        # Need a real correlation for foreign key consistency
        correlation = OperationalCorrelation(
            id=correlation_id,
            client_id=client_id,
            correlation_type="test",
            source_domains_json={},
            correlation_key="test_key",
            immutable_hash="hash_corr",
        )
        session.add(correlation)

        event = CorrelatedOperationalEvent(
            client_id=client_id,
            correlation_id=correlation_id,
            event_type="api_error",
            source_domain="gateway",
            source_ref="req_123",
            severity="error",
            event_timestamp=utc_now(),
            immutable_hash="hash_event",
        )
        session.add(event)
        await session.commit()

        result = await session.execute(
            select(CorrelatedOperationalEvent).where(
                CorrelatedOperationalEvent.source_ref == "req_123"
            )
        )
        saved = result.scalars().one()
        assert saved.event_type == "api_error"
        assert saved.correlation_id == correlation_id
        assert saved.severity == "error"

    async def test_create_trust_link(self, session: AsyncSession):
        client_id = uuid.uuid4()
        link = OperationalTrustLink(
            client_id=client_id,
            source_node="auth_service",
            target_node="inference_api",
            trust_relation="depends_on",
            confidence=0.99,
            immutable_hash="hash_link",
        )
        session.add(link)
        await session.commit()

        result = await session.execute(
            select(OperationalTrustLink).where(OperationalTrustLink.client_id == client_id)
        )
        saved = result.scalars().one()
        assert saved.source_node == "auth_service"
        assert saved.target_node == "inference_api"
        assert saved.advisory_only is True
        assert saved.trust_relation == "depends_on"
