import uuid

import pytest
from app.models.operations.correlation import OperationalTrustLink
from app.services.operations.correlation.trust_graph import OperationalTrustGraphService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
class TestOperationalTrustGraph:
    async def test_create_trust_link(self, session: AsyncSession):
        client_id = uuid.uuid4()
        service = OperationalTrustGraphService(session, client_id)

        link = await service.create_trust_link("domain_a", "domain_b", "depends_on", confidence=0.8)
        assert link.source_node == "domain_a"
        assert link.target_node == "domain_b"
        assert link.confidence == 0.8
        assert link.advisory_only is True
        assert link.immutable_hash is not None

    async def test_build_graph_from_correlations(self, session: AsyncSession):
        client_id = uuid.uuid4()
        service = OperationalTrustGraphService(session, client_id)

        events = [{"source_domain": "runtime"}]
        correlations = [
            {
                "involved_domains": ["runtime", "billing"],
                "correlation_score": 0.9,
                "correlation_type": "cross_domain_impact",
            }
        ]

        links = await service.build_graph(events, correlations)

        # Should have:
        # 1. runtime -> billing (cross_domain_correlation)
        # 2. runtime -> platform_core (operational_dependency)
        assert len(links) == 2

        source_nodes = [l.source_node for l in links]
        assert "runtime" in source_nodes

        relations = [l.trust_relation for l in links]
        assert "cross_domain_correlation" in relations
        assert "operational_dependency" in relations

    async def test_calculate_trust_confidence(self, session: AsyncSession):
        client_id = uuid.uuid4()
        service = OperationalTrustGraphService(session, client_id)

        links = [OperationalTrustLink(confidence=0.8), OperationalTrustLink(confidence=0.4)]

        avg = service.calculate_trust_confidence(links)
        assert avg == pytest.approx(0.6)

    async def test_export_graph_summary(self, session: AsyncSession):
        client_id = uuid.uuid4()
        service = OperationalTrustGraphService(session, client_id)

        await service.create_trust_link("a", "b", "rel1", confidence=0.7)
        await service.create_trust_link("b", "c", "rel2", confidence=0.5)
        await session.commit()

        summary = await service.export_graph_summary()

        assert summary["client_id"] == str(client_id)
        assert summary["node_count"] == 3
        assert summary["edge_count"] == 2
        assert "a" in summary["nodes"]
        assert "c" in summary["nodes"]
        assert summary["aggregate_confidence"] == 0.6
