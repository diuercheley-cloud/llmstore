import hashlib
import json
import uuid
from datetime import datetime
from typing import Any

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.commercial.commercial_governance_federation import (
    CommercialFederatedAuditTrail,
    CommercialGovernanceFederationPeer,
)
from app.services.routing.commercial_report_export import sanitize_report_payload
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

FEDERATED_EVENT_TYPES = {
    "policy_published",
    "policy_activated",
    "rollback",
    "drift",
    "approval",
    "evidence_package",
    "exception",
}


class FederatedAuditService:
    def __init__(self):
        self.settings = get_settings()

    async def export_audit_events(
        self,
        db: AsyncSession,
        peer_cluster_id: str,
        since: datetime | None = None,
        event_types: list[str] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        peer = await self._get_peer(db, peer_cluster_id)
        if peer.status == "disabled":
            raise ValueError(f"Peer {peer_cluster_id} is disabled")

        stmt = select(CommercialFederatedAuditTrail).order_by(
            desc(CommercialFederatedAuditTrail.received_at)
        )

        if since:
            stmt = stmt.where(CommercialFederatedAuditTrail.received_at >= since)
        if event_types:
            stmt = stmt.where(CommercialFederatedAuditTrail.event_type.in_(event_types))

        stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        events = result.scalars().all()

        exported = []
        for ev in events:
            exported.append(
                {
                    "source_event_id": ev.source_event_id,
                    "event_type": ev.event_type,
                    "event_hash": ev.event_hash,
                    "event_payload": ev.event_payload_json,
                    "received_at": ev.received_at.isoformat(),
                }
            )
        return exported

    async def ingest_audit_events(
        self,
        db: AsyncSession,
        events: list[dict[str, Any]],
        source_cluster_id: str,
        peer_token: str | None = None,
    ) -> dict[str, Any]:
        if self.settings.commercial_governance_federation_require_token:
            expected_token = self.settings.commercial_governance_federation_shared_token
            if not expected_token:
                raise ValueError("Federation shared token not configured")
            if not peer_token or peer_token != expected_token:
                raise ValueError("Invalid federation token")

        ingested = 0
        duplicates = 0
        errors = []

        for event in events:
            try:
                sanitized = sanitize_report_payload(event)
                event_type = sanitized.get("event_type", "")
                source_event_id = sanitized.get("source_event_id", str(uuid.uuid4()))
                event_payload = sanitized.get("event_payload", {})

                if event_type and event_type not in FEDERATED_EVENT_TYPES:
                    errors.append(f"Unknown event type: {event_type}")
                    continue

                dedupe_key = f"{source_cluster_id}:{event_type}:{source_event_id}"
                event_hash = self._compute_event_hash(event_payload)

                dup = await self.dedupe_audit_event(db, dedupe_key)
                if dup:
                    duplicates += 1
                    continue

                trail = CommercialFederatedAuditTrail(
                    source_cluster_id=source_cluster_id,
                    source_event_id=source_event_id,
                    event_type=event_type or "unknown",
                    event_hash=event_hash,
                    event_payload_json=event_payload,
                    dedupe_key=dedupe_key,
                )
                db.add(trail)
                ingested += 1
            except Exception as exc:
                errors.append(str(exc))

        await db.flush()

        peer = await db.execute(
            select(CommercialGovernanceFederationPeer).where(
                CommercialGovernanceFederationPeer.peer_cluster_id == source_cluster_id
            )
        )
        peer_record = peer.scalar_one_or_none()
        if peer_record:
            peer_record.last_audit_sync_at = utc_now()

        return {
            "ingested": ingested,
            "duplicates": duplicates,
            "errors": errors,
            "total_events": len(events),
        }

    async def dedupe_audit_event(
        self,
        db: AsyncSession,
        dedupe_key: str,
    ) -> CommercialFederatedAuditTrail | None:
        result = await db.execute(
            select(CommercialFederatedAuditTrail).where(
                CommercialFederatedAuditTrail.dedupe_key == dedupe_key
            )
        )
        return result.scalar_one_or_none()

    def validate_audit_event_hash(self, event: dict[str, Any], expected_hash: str) -> bool:
        payload = event.get("event_payload", {})
        computed = self._compute_event_hash(payload)
        return computed == expected_hash

    async def summarize_federated_audit(
        self,
        db: AsyncSession,
        limit: int = 100,
    ) -> dict[str, Any]:
        stmt = (
            select(CommercialFederatedAuditTrail)
            .order_by(desc(CommercialFederatedAuditTrail.received_at))
            .limit(limit)
        )
        result = await db.execute(stmt)
        events = result.scalars().all()

        type_counts: dict[str, int] = {}
        source_counts: dict[str, int] = {}
        recent_events = []

        for ev in events:
            type_counts[ev.event_type] = type_counts.get(ev.event_type, 0) + 1
            source_counts[ev.source_cluster_id] = source_counts.get(ev.source_cluster_id, 0) + 1
            recent_events.append(
                {
                    "id": str(ev.id),
                    "source_cluster_id": ev.source_cluster_id,
                    "event_type": ev.event_type,
                    "received_at": ev.received_at.isoformat(),
                }
            )

        return {
            "total_events": len(events),
            "by_type": type_counts,
            "by_source": source_counts,
            "recent_events": recent_events[:20],
        }

    @staticmethod
    def _compute_event_hash(payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    async def _get_peer(
        self, db: AsyncSession, peer_cluster_id: str
    ) -> CommercialGovernanceFederationPeer:
        result = await db.execute(
            select(CommercialGovernanceFederationPeer).where(
                CommercialGovernanceFederationPeer.peer_cluster_id == peer_cluster_id
            )
        )
        peer = result.scalar_one_or_none()
        if not peer:
            raise ValueError(f"Peer {peer_cluster_id} not found")
        return peer
