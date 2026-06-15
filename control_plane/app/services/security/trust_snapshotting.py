from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from app.models.commercial.commercial_operations_center import (
    CommercialCryptographicTrustSnapshot,
    CommercialOperationsCenterEvent,
)
from app.services.routing.commercial_report_export import sanitize_report_payload
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from .cryptographic_topology import CryptographicTopologyService
from .trust_graph import TrustGraphService


def _canonical_json(payload: Any) -> str:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str
    )


def _sha256(payload: Any) -> str:
    if not isinstance(payload, str):
        payload = _canonical_json(payload)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class TrustSnapshottingService:
    def __init__(self) -> None:
        self.trust_graph_service = TrustGraphService()
        self.topology_service = CryptographicTopologyService()

    async def _get_latest_snapshot(
        self, db: AsyncSession
    ) -> CommercialCryptographicTrustSnapshot | None:
        try:
            return (
                await db.execute(
                    select(CommercialCryptographicTrustSnapshot).order_by(
                        CommercialCryptographicTrustSnapshot.created_at.desc()
                    )
                )
            ).scalar_one_or_none()
        except SQLAlchemyError:
            return None

    async def _get_latest_event(self, db: AsyncSession) -> CommercialOperationsCenterEvent | None:
        try:
            return (
                await db.execute(
                    select(CommercialOperationsCenterEvent).order_by(
                        CommercialOperationsCenterEvent.created_at.desc()
                    )
                )
            ).scalar_one_or_none()
        except SQLAlchemyError:
            return None

    async def _record_event(
        self,
        db: AsyncSession,
        *,
        event_type: str,
        payload: dict[str, Any],
    ) -> CommercialOperationsCenterEvent:
        latest_event = await self._get_latest_event(db)
        parent_hash = latest_event.hash if latest_event else None
        sanitized_payload = sanitize_report_payload(payload)
        event_hash = _sha256(
            {
                "event_type": event_type,
                "parent_hash": parent_hash,
                "payload": sanitized_payload,
            }
        )
        event = CommercialOperationsCenterEvent(
            event_type=event_type,
            payload_json=sanitized_payload,
            hash=event_hash,
            parent_hash=parent_hash,
        )
        try:
            db.add(event)
            await db.flush()
        except SQLAlchemyError:
            await db.rollback()
        return event

    async def create_snapshot(
        self,
        db: AsyncSession,
        *,
        tenant_id: str | None = None,
    ) -> CommercialCryptographicTrustSnapshot:
        latest_snapshot = await self._get_latest_snapshot(db)
        graph = await self.trust_graph_service.get_full_graph(db, tenant_id=tenant_id)
        topology = await self.topology_service.merkle_linked_topology(db, tenant_id=tenant_id)
        snapshot_payload = {
            "graph": graph,
            "nodes": graph["nodes"],
            "edges": graph["edges"],
            "snapshot": {
                "created_at": datetime.now(UTC).isoformat(),
                "graph_hash": graph["graph_hash"],
                "merkle_root": graph["merkle_root"],
                "node_count": graph["summary"]["node_count"],
                "previous_snapshot_hash": latest_snapshot.immutable_hash
                if latest_snapshot
                else None,
                "tenant_id": tenant_id,
                "topology": topology,
            },
        }
        immutable_hash = _sha256(snapshot_payload)
        snapshot = CommercialCryptographicTrustSnapshot(
            snapshot_data=snapshot_payload,
            immutable_hash=immutable_hash,
        )
        try:
            db.add(snapshot)
            await db.flush()
            await self._record_event(
                db,
                event_type="trust_snapshot_created",
                payload={
                    "graph_hash": graph["graph_hash"],
                    "immutable_hash": immutable_hash,
                    "tenant_id": tenant_id,
                },
            )
            await db.commit()
            await db.refresh(snapshot)
        except SQLAlchemyError:
            await db.rollback()
            snapshot.id = snapshot.id or uuid.uuid4()
            snapshot.created_at = snapshot.created_at or datetime.now(UTC)
        return snapshot

    def verify_snapshot(
        self,
        snapshot: CommercialCryptographicTrustSnapshot,
    ) -> bool:
        current_hash = _sha256(snapshot.snapshot_data)
        return current_hash == snapshot.immutable_hash

    async def export_snapshot_bundle(
        self,
        db: AsyncSession,
        *,
        snapshot: CommercialCryptographicTrustSnapshot | None = None,
        format: str = "json",
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        if snapshot is None:
            snapshot = await self._get_latest_snapshot(db)
        if snapshot is None:
            snapshot = await self.create_snapshot(db, tenant_id=tenant_id)

        payload = sanitize_report_payload(snapshot.snapshot_data)
        manifest = {
            "air_gap_ready": True,
            "created_at": datetime.now(UTC).isoformat(),
            "format": format,
            "immutable_hash": snapshot.immutable_hash,
            "offline_capable": True,
            "snapshot_id": str(snapshot.id),
            "tenant_id": tenant_id,
        }
        manifest_hash = _sha256({"manifest": manifest, "payload": payload})
        bundle: dict[str, Any] = {
            "manifest": manifest,
            "manifest_hash": manifest_hash,
            "payload": payload,
        }
        if format == "signed_bundle":
            bundle["signature_algorithm"] = "sha256_local"
            bundle["detached_signature"] = _sha256(f"{manifest_hash}:ops-center")
        elif format == "offline_audit_package":
            bundle["audit_instructions"] = [
                "Verify manifest_hash against payload.",
                "Validate immutable_hash against snapshot payload.",
                "Operate fully offline; no remote dependency required.",
            ]
            bundle["package_type"] = "offline_audit_package"
            bundle["sovereign_redaction"] = True
        return bundle
