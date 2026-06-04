import uuid
from typing import Any, Dict, List

from app.core.time import utc_now
from app.models.operations.correlation import OperationalTrustLink, compute_deterministic_hash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class OperationalTrustGraphService:
    """
    Service for managing the Operational Trust Graph.
    Deterministic, offline-first, and advisory-only.
    """

    def __init__(self, session: AsyncSession, client_id: uuid.UUID):
        self.session = session
        self.client_id = client_id

    async def create_trust_link(
        self, 
        source: str, 
        target: str, 
        relation: str, 
        confidence: float = 0.5,
        advisory_only: bool = True
    ) -> OperationalTrustLink:
        """
        Creates and persists a trust link between two nodes.
        """
        # Ensure deterministic hashing for idempotency check or integrity
        hash_fields = {
            "client_id": str(self.client_id),
            "source": source,
            "target": target,
            "relation": relation,
        }
        immutable_hash = compute_deterministic_hash(fields=hash_fields)

        existing_stmt = select(OperationalTrustLink).where(OperationalTrustLink.immutable_hash == immutable_hash)
        existing = (await self.session.execute(existing_stmt)).scalar_one_or_none()
        if existing is not None:
            setattr(existing, "_phase70_created_now", False)
            return existing

        link = OperationalTrustLink(
            client_id=self.client_id,
            source_node=source,
            target_node=target,
            trust_relation=relation,
            confidence=confidence,
            advisory_only=advisory_only,
            immutable_hash=immutable_hash
        )
        setattr(link, "_phase70_created_now", True)
        self.session.add(link)
        return link

    async def build_graph(self, events: List[Dict[str, Any]], correlations: List[Dict[str, Any]]) -> List[OperationalTrustLink]:
        """
        Builds graph links based on events and detected correlations.
        This is a deterministic process.
        """
        links = []
        
        # Rule 1: Correlated domains gain a "correlated_with" relation
        for corr in correlations:
            domains = sorted(corr.get("involved_domains", []))
            if len(domains) > 1:
                # Create links between all pairs (undirected represented as two directed links or sorted pairs)
                for i in range(len(domains)):
                    for j in range(i + 1, len(domains)):
                        # Deterministic relation based on correlation score
                        score = corr.get("correlation_score", 0.0)
                        link = await self.create_trust_link(
                            source=domains[i],
                            target=domains[j],
                            relation="cross_domain_correlation",
                            confidence=score
                        )
                        links.append(link)

        # Rule 2: Frequent events in a domain strengthen its "operational_presence"
        domain_counts = {}
        for e in events:
            d = e.get("source_domain")
            if d:
                domain_counts[d] = domain_counts.get(d, 0) + 1
        
        for domain, count in domain_counts.items():
            # A domain relates to the 'platform_core'
            link = await self.create_trust_link(
                source=domain,
                target="platform_core",
                relation="operational_dependency",
                confidence=min(1.0, count * 0.1)
            )
            links.append(link)

        return links

    def calculate_trust_confidence(self, links: List[OperationalTrustLink]) -> float:
        """
        Calculates an aggregate trust confidence score for a set of links.
        """
        if not links:
            return 0.0
        
        scores = [l.confidence for l in links]
        return sum(scores) / len(scores)

    async def export_graph_summary(self) -> Dict[str, Any]:
        """
        Exports a serializable summary of the current trust graph for the client.
        """
        stmt = select(OperationalTrustLink).where(OperationalTrustLink.client_id == self.client_id)
        result = await self.session.execute(stmt)
        links = result.scalars().all()

        nodes = set()
        edges = []
        
        for l in links:
            nodes.add(l.source_node)
            nodes.add(l.target_node)
            edges.append({
                "from": l.source_node,
                "to": l.target_node,
                "relation": l.trust_relation,
                "confidence": l.confidence,
                "advisory_only": l.advisory_only
            })

        return {
            "client_id": str(self.client_id),
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": sorted(list(nodes)),
            "edges": edges,
            "aggregate_confidence": self.calculate_trust_confidence(links),
            "exported_at": utc_now().isoformat()
        }
