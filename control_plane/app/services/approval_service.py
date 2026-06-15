import logging
import os
import uuid
from datetime import UTC, datetime, timedelta

import httpx
from app.core.time import utc_now
from app.models.governance.human_governance import CriticalApproval
from app.services.admin_rbac import record_admin_audit_event
from fastapi import WebSocket
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def _as_utc_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


logger = logging.getLogger("approval_service")


class ApprovalsWebSocketManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to approvals websocket: {e}")
                self.disconnect(connection)


approvals_ws_manager = ApprovalsWebSocketManager()


class ApprovalService:
    @staticmethod
    async def create_request(
        db: AsyncSession,
        action_type: str,
        description: str,
        requested_by: str,
        payload: dict | None = None,
        metadata: dict | None = None,
        expires_in_seconds: int = 3600,
    ) -> CriticalApproval:
        expires_at = utc_now() + timedelta(seconds=expires_in_seconds)
        req = CriticalApproval(
            action_type=action_type,
            description=description,
            status="pending",
            requested_by=requested_by,
            requested_at=utc_now(),
            expires_at=expires_at,
            payload=payload,
            metadata_json=metadata,
        )
        db.add(req)
        await db.commit()
        await db.refresh(req)

        # Audit
        await record_admin_audit_event(
            db,
            event_type="critical_approval.created",
            status="success",
            actor_identifier=requested_by,
            target_type="critical_approval",
            target_id=str(req.id),
            metadata={"action_type": action_type, "description": description},
        )

        # Dispatch notifications
        await ApprovalService._dispatch_notifications(db, req, "created")

        return req

    @staticmethod
    async def approve_request(
        db: AsyncSession, request_id: uuid.UUID, decided_by: str, reason: str | None = None
    ) -> CriticalApproval:
        stmt = select(CriticalApproval).where(CriticalApproval.id == request_id)
        res = await db.execute(stmt)
        req = res.scalar_one_or_none()
        if not req:
            raise ValueError("Approval request not found")

        await ApprovalService._check_expiration_on_read(db, req)

        if req.status != "pending":
            raise ValueError(f"Cannot approve request in status: {req.status}")

        req.status = "approved"
        req.decided_by = decided_by
        req.decided_at = utc_now()
        req.decision_reason = reason
        await db.commit()
        await db.refresh(req)

        # Audit
        await record_admin_audit_event(
            db,
            event_type="critical_approval.approved",
            status="success",
            actor_identifier=decided_by,
            target_type="critical_approval",
            target_id=str(req.id),
            metadata={"reason": reason},
        )

        # Dispatch notifications
        await ApprovalService._dispatch_notifications(db, req, "approved")

        return req

    @staticmethod
    async def reject_request(
        db: AsyncSession, request_id: uuid.UUID, decided_by: str, reason: str | None = None
    ) -> CriticalApproval:
        stmt = select(CriticalApproval).where(CriticalApproval.id == request_id)
        res = await db.execute(stmt)
        req = res.scalar_one_or_none()
        if not req:
            raise ValueError("Approval request not found")

        await ApprovalService._check_expiration_on_read(db, req)

        if req.status != "pending":
            raise ValueError(f"Cannot reject request in status: {req.status}")

        req.status = "rejected"
        req.decided_by = decided_by
        req.decided_at = utc_now()
        req.decision_reason = reason
        await db.commit()
        await db.refresh(req)

        # Audit
        await record_admin_audit_event(
            db,
            event_type="critical_approval.rejected",
            status="success",
            actor_identifier=decided_by,
            target_type="critical_approval",
            target_id=str(req.id),
            metadata={"reason": reason},
        )

        # Dispatch notifications
        await ApprovalService._dispatch_notifications(db, req, "rejected")

        return req

    @staticmethod
    async def get_request(db: AsyncSession, request_id: uuid.UUID) -> CriticalApproval:
        stmt = select(CriticalApproval).where(CriticalApproval.id == request_id)
        res = await db.execute(stmt)
        req = res.scalar_one_or_none()
        if not req:
            raise ValueError("Approval request not found")

        await ApprovalService._check_expiration_on_read(db, req)
        return req

    @staticmethod
    async def list_requests(
        db: AsyncSession, status: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[CriticalApproval]:
        await ApprovalService.check_all_expirations(db)

        stmt = select(CriticalApproval)
        if status:
            stmt = stmt.where(CriticalApproval.status == status)
        stmt = stmt.order_by(CriticalApproval.requested_at.desc()).limit(limit).offset(offset)
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def check_all_expirations(db: AsyncSession) -> None:
        now = utc_now()
        stmt = select(CriticalApproval).where(CriticalApproval.status == "pending")
        res = await db.execute(stmt)
        pending_reqs = res.scalars().all()
        expired_reqs = [r for r in pending_reqs if _as_utc_aware(r.expires_at) < now]
        for req in expired_reqs:
            req.status = "expired"
            await record_admin_audit_event(
                db,
                event_type="critical_approval.expired",
                status="success",
                actor_identifier="system",
                target_type="critical_approval",
                target_id=str(req.id),
                metadata={"reason": "Expiration timeout reached"},
            )
            await ApprovalService._dispatch_notifications(db, req, "expired")
        if expired_reqs:
            await db.commit()

    @staticmethod
    async def _check_expiration_on_read(db: AsyncSession, req: CriticalApproval) -> None:
        if req.status == "pending" and _as_utc_aware(req.expires_at) < utc_now():
            req.status = "expired"
            await db.commit()
            await record_admin_audit_event(
                db,
                event_type="critical_approval.expired",
                status="success",
                actor_identifier="system",
                target_type="critical_approval",
                target_id=str(req.id),
                metadata={"reason": "Expiration timeout reached"},
            )
            await ApprovalService._dispatch_notifications(db, req, "expired")

    @staticmethod
    async def _dispatch_notifications(
        db: AsyncSession, req: CriticalApproval, event_type: str
    ) -> None:
        """
        Dispatches notifications to all configured channels:
        - dashboard: saved to db (implicit)
        - websocket: broadcast to active ws connections
        - ntfy: push notification to ntfy server if configured
        - gotify: push notification to gotify server if configured
        """
        payload = {
            "event": f"critical_approval.{event_type}",
            "id": str(req.id),
            "action_type": req.action_type,
            "description": req.description,
            "requested_by": req.requested_by,
            "status": req.status,
            "expires_at": req.expires_at.isoformat() if req.expires_at else None,
        }

        # 1. Websocket
        await approvals_ws_manager.broadcast(payload)

        # 2. ntfy
        ntfy_topic = os.getenv("NTFY_TOPIC", "critical-approvals")
        ntfy_url = os.getenv("NTFY_URL", "https://ntfy.sh").rstrip("/")
        if ntfy_topic:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"{ntfy_url}/{ntfy_topic}",
                        headers={
                            "Title": f"Critical Approval: {req.action_type.upper()} ({event_type})",
                            "Priority": "high" if req.status == "pending" else "default",
                        },
                        content=f"Request {req.id}: {req.description} is now {req.status}.",
                    )
            except Exception as e:
                logger.warning(f"Failed to send ntfy notification: {e}")

        # 3. gotify
        gotify_url = os.getenv("GOTIFY_URL")
        gotify_token = os.getenv("GOTIFY_TOKEN")
        if gotify_url and gotify_token:
            try:
                gotify_url = gotify_url.rstrip("/")
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"{gotify_url}/message?token={gotify_token}",
                        json={
                            "title": f"Critical Approval: {req.action_type.upper()} ({event_type})",
                            "message": f"Request {req.id}: {req.description} is now {req.status}.",
                            "priority": 7 if req.status == "pending" else 4,
                        },
                    )
            except Exception as e:
                logger.warning(f"Failed to send gotify notification: {e}")
