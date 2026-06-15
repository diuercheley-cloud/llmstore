import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class BackupAuditEmitter:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_immutable_event(
        self,
        *,
        action: str,
        actor: str,
        backup_id: str,
        key_id: str | None,
        source: str,
        target: str,
        result: str,
        checksum: str | None,
    ) -> None:
        try:
            from app.core.time import utc_now
            from app.services.security.immutable_audit import ImmutableAuditStore

            payload = {
                "actor": actor,
                "timestamp": ImmutableAuditStore.format_timestamp(utc_now()),
                "backup_id": backup_id,
                "key_id": key_id or "unknown",
                "source": source,
                "target": target,
                "result": result,
                "checksum": checksum or "none",
            }
            await ImmutableAuditStore.write_entry(
                db=self.db, action=action, actor=actor, payload=payload, tenant_id="default"
            )
        except Exception as e:
            logger.error(f"Failed to write immutable audit log: {e}")

    async def record_admin_audit(
        self, event_type: str, status: str, actor: str, target_id: str, metadata: dict[str, Any]
    ) -> None:
        try:
            from app.services.admin_rbac import record_admin_audit_event

            await record_admin_audit_event(
                self.db,
                event_type=event_type,
                status=status,
                actor_identifier=actor,
                target_type="backup",
                target_id=target_id,
                metadata=metadata,
            )
        except Exception as e:
            logger.error(f"Failed to record admin audit event: {e}")
