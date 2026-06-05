import csv
import io
import json
from typing import Any, Dict, List, Optional

from app.db.session import get_db_session
from app.schemas.compliance_evidence import (
    ComplianceFramework, EvidenceCollectionRequest, EvidenceExportFormat, EvidenceItem
)
from app.services.compliance.evidence.collector import ComplianceEvidenceService
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/admin/compliance/evidence", tags=["admin-compliance"])

# In-memory store for this prototype session
COLLECTED_EVIDENCE: List[EvidenceItem] = []

@router.get("", response_model=List[EvidenceItem])
async def list_evidence():
    return COLLECTED_EVIDENCE

@router.post("/collect", response_model=List[EvidenceItem])
async def collect_evidence(
    request: EvidenceCollectionRequest,
    db: AsyncSession = Depends(get_db_session)
):
    service = ComplianceEvidenceService(db)
    items = await service.collect_evidence(request.frameworks)
    
    if not request.dry_run:
        COLLECTED_EVIDENCE.extend(items)
        
    return items

@router.get("/export")
async def export_evidence(
    format: EvidenceExportFormat = Query(EvidenceExportFormat.JSON),
    db: AsyncSession = Depends(get_db_session)
):
    if not COLLECTED_EVIDENCE:
        # Collect if empty for demo purposes
        service = ComplianceEvidenceService(db)
        COLLECTED_EVIDENCE.extend(await service.collect_evidence([f for f in ComplianceFramework]))

    if format == EvidenceExportFormat.JSON:
        data = [item.dict() for item in COLLECTED_EVIDENCE]
        # Pydantic dict handles UUID and datetime conversion usually, but ensure JSON serializable
        return Response(content=json.dumps(data, default=str), media_type="application/json")

    elif format == EvidenceExportFormat.CSV:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "framework", "control_id", "evidence_type", "source", 
            "collected_at", "status", "content_hash", "redaction_status"
        ])
        for item in COLLECTED_EVIDENCE:
            writer.writerow([
                item.id, item.framework, item.control_id, item.evidence_type, 
                item.source, item.collected_at, item.status, 
                item.content_hash, item.redaction_status
            ])
        return Response(
            content=output.getvalue(), 
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=compliance_evidence.csv"}
        )

    elif format == EvidenceExportFormat.MARKDOWN:
        service = ComplianceEvidenceService(db)
        report = service.format_as_markdown(COLLECTED_EVIDENCE)
        return Response(
            content=report, 
            media_type="text/markdown",
            headers={"Content-Disposition": "attachment; filename=compliance_report.md"}
        )

    raise HTTPException(status_code=400, detail="Invalid export format")
