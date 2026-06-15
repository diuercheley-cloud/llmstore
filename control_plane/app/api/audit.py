import logging
from typing import Any

from app.services.runtime_dependencies import get_db_session
from app.services.security.immutable_audit import ImmutableAuditStore
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(tags=["immutable-audit"])


@router.post("/api/audit/verify")
async def verify_audit_log(db: AsyncSession = Depends(get_db_session)) -> dict[str, Any]:
    """
    Cryptographically verifies the integrity of the entire audit trail.
    """
    is_valid, failed_block_id, reason = await ImmutableAuditStore.verify_chain(db)

    return {
        "status": "success" if is_valid else "failed",
        "is_valid": is_valid,
        "failed_block_id": failed_block_id,
        "reason": reason,
    }


@router.get("/api/audit/export")
async def export_audit_log(db: AsyncSession = Depends(get_db_session)) -> list[dict[str, Any]]:
    """
    Exports the complete cryptographically verifiable audit log.
    """
    return await ImmutableAuditStore.export_logs(db)
