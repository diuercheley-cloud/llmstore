# Owner: platform-ops

from app.api.dependencies import get_db
from app.models.core.client import Client
from app.models.operations.correlation import OperationalCorrelation
from app.services.auth import require_client
from app.services.operations.correlation.trust_graph import OperationalTrustGraphService
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/portal/operations/correlations", tags=["portal-operations-correlation"])

@router.get("/")
async def list_portal_correlations(
    client: Client = Depends(require_client),
    db: AsyncSession = Depends(get_db)
):
    """
    Lists correlations for the current authenticated portal client.
    Strictly advisory-only.
    """
    stmt = select(OperationalCorrelation).where(OperationalCorrelation.client_id == client.id).order_by(OperationalCorrelation.created_at.desc())
    result = await db.execute(stmt)
    correlations = result.scalars().all()
    
    # Per requirement "não expor payload sensível", we return only the necessary fields
    return [
        {
            "id": str(c.id),
            "correlation_type": c.correlation_type,
            "involved_domains": c.source_domains_json,
            "correlation_score": c.correlation_score,
            "confidence": c.confidence,
            "advisory_only": c.advisory_only,
            "immutable_hash": c.immutable_hash,
            "created_at": c.created_at.isoformat()
        }
        for c in correlations
    ]

@router.get("/trust-graph")
async def get_portal_trust_graph_summary(
    client: Client = Depends(require_client),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns a summary of the current trust graph state for the current authenticated portal client.
    """
    service = OperationalTrustGraphService(db, client.id)
    summary = await service.export_graph_summary()
    return summary
