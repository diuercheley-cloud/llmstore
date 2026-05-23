# Owner: platform-ops
import uuid
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.dependencies import get_current_admin, get_db
from app.models.operations.correlation import (
    OperationalCorrelation,
    CorrelatedOperationalEvent,
    OperationalTrustLink,
    compute_deterministic_hash,
)
from app.services.operations.correlation.deterministic_correlation_engine import DeterministicOperationsCorrelationEngine
from app.services.operations.correlation.trust_graph import OperationalTrustGraphService
from app.services.operations.correlation.correlation_risk_analysis import OperationalCorrelationRiskAnalysisService
from app.services.operations.correlation.receipts import (
    build_correlation_receipt,
    build_trust_link_receipt,
    build_graph_summary_receipt,
)
from app.services.operations.correlation.audit_events import (
    log_correlation_created,
    log_trust_link_created,
    log_graph_generated,
)

router = APIRouter()

CORRELATION_ENGINE = DeterministicOperationsCorrelationEngine()
RISK_SERVICE = OperationalCorrelationRiskAnalysisService()

# --- Schemas ---

class CorrelationRunRequest(BaseModel):
    client_id: uuid.UUID
    events: List[Dict[str, Any]]
    forecasts: Optional[List[Dict[str, Any]]] = None

class RiskAnalysisRequest(BaseModel):
    client_id: uuid.UUID
    correlation_id: uuid.UUID

# --- Endpoints ---

@router.post("/run")
async def run_deterministic_correlation(
    payload: CorrelationRunRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin)
):
    """
    Executes deterministic correlation on provided events.
    Strictly advisory-only and tenant-isolated.
    """
    result = CORRELATION_ENGINE.correlate(payload.events, payload.forecasts)

    corr_hash = compute_deterministic_hash(
        fields={
            "client_id": str(payload.client_id),
            "correlation_type": result["correlation_type"],
            "correlation_key": result["correlation_key"],
            "correlation_score": result["correlation_score"],
            "confidence": result["confidence"],
            "involved_domains": result["involved_domains"],
            "advisory_only": True,
        }
    )

    existing_stmt = select(OperationalCorrelation).where(OperationalCorrelation.immutable_hash == corr_hash)
    correlation = (await db.execute(existing_stmt)).scalar_one_or_none()
    created_now = correlation is None

    if correlation is None:
        correlation = OperationalCorrelation(
            client_id=payload.client_id,
            correlation_type=result["correlation_type"],
            source_domains_json=result["involved_domains"],
            correlation_key=result["correlation_key"],
            correlation_score=result["correlation_score"],
            confidence=result["confidence"],
            advisory_only=True,
            immutable_hash=corr_hash,
        )
        db.add(correlation)
        await db.commit()
        await db.refresh(correlation)

    if created_now:
        await log_correlation_created(db, payload.client_id, correlation.id, correlation.correlation_type)
        await db.commit()

    receipt = build_correlation_receipt(
        {
            "immutable_hash": correlation.immutable_hash,
            "correlation_type": correlation.correlation_type,
            "correlation_key": correlation.correlation_key,
            "involved_domains": correlation.source_domains_json,
        }
    )
    
    return {
        "correlation": {
            "id": correlation.id,
            "type": correlation.correlation_type,
            "score": correlation.correlation_score,
            "confidence": correlation.confidence
        },
        "receipt": receipt
    }

@router.get("/")
async def list_correlations(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin)
):
    """
    Lists correlations for a specific client.
    """
    stmt = select(OperationalCorrelation).where(OperationalCorrelation.client_id == client_id).order_by(OperationalCorrelation.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/trust-graph/build")
async def build_trust_graph(
    client_id: uuid.UUID,
    events: List[Dict[str, Any]],
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin)
):
    """
    Builds the Operational Trust Graph based on events and historical correlations.
    """
    stmt = select(OperationalCorrelation).where(OperationalCorrelation.client_id == client_id)
    correlations_db = (await db.execute(stmt)).scalars().all()
    correlations = [
        {"involved_domains": c.source_domains_json, "correlation_score": c.correlation_score} 
        for c in correlations_db
    ]
    
    service = OperationalTrustGraphService(db, client_id)
    links = await service.build_graph(events, correlations)
    await db.commit()

    for link in links:
        if getattr(link, "_phase70_created_now", False):
            await log_trust_link_created(db, client_id, link.source_node, link.target_node)
    await db.commit()
    
    summary = await service.export_graph_summary()
    await log_graph_generated(db, client_id, summary)
    await db.commit()
    
    receipt = build_graph_summary_receipt(summary)
    
    return {
        "summary": summary,
        "receipt": receipt
    }

@router.get("/trust-graph")
async def get_trust_graph_summary(
    client_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin)
):
    """
    Returns a summary of the current trust graph state.
    """
    service = OperationalTrustGraphService(db, client_id)
    return await service.export_graph_summary()

@router.get("/{correlation_id}")
async def get_correlation_details(
    correlation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin)
):
    """
    Returns detailed information for a specific correlation.
    """
    stmt = select(OperationalCorrelation).where(OperationalCorrelation.id == correlation_id)
    correlation = (await db.execute(stmt)).scalar_one_or_none()
    if not correlation:
        raise HTTPException(status_code=404, detail="Correlation not found")
    return correlation

@router.post("/correlation-risk-analysis")
async def execute_advisory_analysis(
    payload: RiskAnalysisRequest,
    db: AsyncSession = Depends(get_db),
    _admin: Any = Depends(get_current_admin)
):
    """
    Executes advisory risk analysis for a given correlation.
    Always advisory_only=True and dry_run=True.
    """
    stmt = select(OperationalCorrelation).where(OperationalCorrelation.id == payload.correlation_id)
    correlation = (await db.execute(stmt)).scalar_one_or_none()
    if not correlation:
        raise HTTPException(status_code=404, detail="Correlation not found")
    if correlation.client_id != payload.client_id:
        raise HTTPException(status_code=404, detail="Correlation not found for client")
        
    corr_data = {
        "correlation_score": correlation.correlation_score,
        "confidence": correlation.confidence,
        "involved_domains": correlation.source_domains_json,
        "correlation_key": correlation.correlation_key
    }
    
    analysis = RISK_SERVICE.analyze_correlation_risk(corr_data)
    return analysis
