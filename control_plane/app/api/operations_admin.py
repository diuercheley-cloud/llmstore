# Owner: platform-ops
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_admin
from app.core.time import utc_now
from app.db.session import get_db_session
from app.models.operations.failure_signals import (
    FailureSignal,
    FailureForecast,
    FailureRiskAssessment,
)
from app.services.operations.forecasting.deterministic_engine import (
    DeterministicFailureForecastingEngine,
)
from app.services.operations.forecasting.risk_scoring import (
    FailureRiskScoringService,
)
from app.services.operations.forecasting.receipts import (
    build_failure_signal_receipt,
    build_failure_forecast_receipt,
    build_failure_risk_assessment_receipt,
)

router = APIRouter(prefix="/admin/operations", tags=["operations"])

ENGINE = DeterministicFailureForecastingEngine()
SCORING = FailureRiskScoringService()


# ── Pydantic schemas ─────────────────────────────────────────────────────────


class FailureSignalCreate(BaseModel):
    client_id: str = Field(..., min_length=1, max_length=64)
    signal_type: str = Field(..., min_length=1, max_length=64)
    source_domain: str = Field(..., min_length=1, max_length=64)
    source_ref: str | None = None
    severity: str = Field(default="info")
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    observed_at: str | None = None
    payload_json: dict[str, Any] | None = None


class FailureSignalRead(BaseModel):
    id: str
    client_id: str
    signal_type: str
    source_domain: str
    source_ref: str | None
    severity: str
    confidence: float | None
    observed_at: str
    immutable_hash: str | None
    previous_hash: str | None
    created_at: str


class FailureSignalCreateResponse(BaseModel):
    signal: FailureSignalRead
    receipt: dict[str, Any]


class _ForecastItem(BaseModel):
    forecast_type: str
    risk_score: float
    confidence: float
    deterministic_version: str
    input_hash: str
    advisory_only: bool
    explanation: dict[str, Any]


class ForecastRunResponse(BaseModel):
    forecast: _ForecastItem
    receipt: dict[str, Any]


class ForecastListResponse(BaseModel):
    forecasts: list[dict[str, Any]]


class FailureRiskAssessmentCreate(BaseModel):
    client_id: str = Field(..., min_length=1, max_length=64)
    forecast_id: str = Field(..., min_length=1, max_length=128)
    dry_run: bool = True


class FailureRiskAssessmentRead(BaseModel):
    id: str
    client_id: str
    forecast_id: str | None
    risk_level: str
    recommendation: str | None
    requires_approval: bool
    dry_run: bool
    advisory_only: bool
    immutable_hash: str | None
    created_at: str


class FailureRiskAssessmentCreateResponse(BaseModel):
    assessment: FailureRiskAssessmentRead
    receipt: dict[str, Any]


# ── Helpers ──────────────────────────────────────────────────────────────────


def _sanitize_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if payload is None:
        return None
    sensitive_keys = {"secret", "token", "password", "credential", "key", "auth"}
    sanitized: dict[str, Any] = {}
    for k, v in payload.items():
        if any(t in k.lower() for t in sensitive_keys):
            sanitized[k] = "<redacted>"
        else:
            sanitized[k] = v if not isinstance(v, str) else v[:500]
    return sanitized


def _model_to_dict(model: Any) -> dict[str, Any]:
    return {
        "id": str(model.id),
        "client_id": str(model.client_id),
        "created_at": str(model.created_at),
    }


def _read_signal(s: FailureSignal) -> FailureSignalRead:
    return FailureSignalRead(
        id=str(s.id),
        client_id=s.client_id,
        signal_type=s.signal_type,
        source_domain=s.source_domain,
        source_ref=s.source_ref,
        severity=s.severity,
        confidence=s.confidence,
        observed_at=str(s.observed_at),
        immutable_hash=s.immutable_hash,
        previous_hash=s.previous_hash,
        created_at=str(s.created_at),
    )


def _read_assessment(a: FailureRiskAssessment) -> FailureRiskAssessmentRead:
    return FailureRiskAssessmentRead(
        id=str(a.id),
        client_id=a.client_id,
        forecast_id=a.forecast_id,
        risk_level=a.risk_level,
        recommendation=a.recommendation,
        requires_approval=a.requires_approval,
        dry_run=a.dry_run,
        advisory_only=a.advisory_only,
        immutable_hash=a.immutable_hash,
        created_at=str(a.created_at),
    )


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/failure-signals", response_model=FailureSignalCreateResponse)
async def create_failure_signal(
    body: FailureSignalCreate,
    session: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin),
) -> Any:
    observed_at = utc_now()
    if body.observed_at:
        try:
            observed_at = datetime.fromisoformat(body.observed_at)
        except (ValueError, TypeError):
            pass

    payload = _sanitize_payload(body.payload_json)

    signal = FailureSignal(
        client_id=body.client_id,
        signal_type=body.signal_type,
        source_domain=body.source_domain,
        source_ref=body.source_ref,
        severity=body.severity,
        confidence=body.confidence,
        observed_at=observed_at,
        payload_json=payload,
    )
    session.add(signal)
    await session.commit()
    await session.refresh(signal)

    signal_dict = {
        "id": str(signal.id),
        "client_id": signal.client_id,
        "signal_type": signal.signal_type,
        "source_domain": signal.source_domain,
        "source_ref": signal.source_ref,
        "severity": signal.severity,
        "confidence": signal.confidence,
        "observed_at": signal.observed_at,
        "payload_json": signal.payload_json,
        "immutable_hash": signal.immutable_hash,
        "previous_hash": signal.previous_hash,
    }
    receipt = build_failure_signal_receipt(signal_dict)

    return FailureSignalCreateResponse(
        signal=_read_signal(signal),
        receipt=receipt,
    )


@router.get("/failure-signals", response_model=list[FailureSignalRead])
async def list_failure_signals(
    client_id: str = Query(..., min_length=1),
    limit: int = Query(default=50, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin),
) -> Any:
    stmt = (
        select(FailureSignal)
        .where(FailureSignal.client_id == client_id)
        .order_by(FailureSignal.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    signals = result.scalars().all()
    return [_read_signal(s) for s in signals]


@router.post("/failure-forecasts/run", response_model=ForecastRunResponse)
async def run_failure_forecast(
    client_id: str = Query(..., min_length=1),
    window_minutes: int = Query(default=60, ge=1, le=1440),
    session: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin),
) -> Any:
    stmt = (
        select(FailureSignal)
        .where(FailureSignal.client_id == client_id)
        .order_by(FailureSignal.created_at.asc())
    )
    result = await session.execute(stmt)
    signals = result.scalars().all()

    signal_dicts = [
        {
            "signal_type": s.signal_type,
            "source_domain": s.source_domain,
            "severity": s.severity,
            "confidence": s.confidence or 0.0,
            "observed_at": s.observed_at,
            "payload_json": s.payload_json,
        }
        for s in signals
    ]

    forecast_result = ENGINE.forecast(
        signal_dicts,
        window_minutes=window_minutes,
        forecast_type="aggregate_failure_risk",
    )
    forecast_result["client_id"] = client_id

    forecast_model = FailureForecast(
        client_id=client_id,
        forecast_type=forecast_result["forecast_type"],
        forecast_window_minutes=window_minutes,
        risk_score=forecast_result["risk_score"],
        confidence=forecast_result["confidence"],
        advisory_only=True,
        deterministic_version=forecast_result["deterministic_version"],
        input_hash=forecast_result["input_hash"],
    )
    session.add(forecast_model)
    await session.commit()
    await session.refresh(forecast_model)

    forecast_result["id"] = str(forecast_model.id)
    forecast_result["immutable_hash"] = forecast_model.immutable_hash

    receipt = build_failure_forecast_receipt(forecast_result)

    return ForecastRunResponse(
        forecast=_ForecastItem(
            forecast_type=forecast_result["forecast_type"],
            risk_score=forecast_result["risk_score"],
            confidence=forecast_result["confidence"],
            deterministic_version=forecast_result["deterministic_version"],
            input_hash=forecast_result["input_hash"],
            advisory_only=forecast_result["advisory_only"],
            explanation=forecast_result["explanation"],
        ),
        receipt=receipt,
    )


@router.get("/failure-forecasts")
async def list_failure_forecasts(
    client_id: str = Query(..., min_length=1),
    limit: int = Query(default=50, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin),
) -> Any:
    stmt = (
        select(FailureForecast)
        .where(FailureForecast.client_id == client_id)
        .order_by(FailureForecast.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    forecasts = result.scalars().all()
    return [
        {
            "id": str(f.id),
            "client_id": f.client_id,
            "forecast_type": f.forecast_type,
            "forecast_window_minutes": f.forecast_window_minutes,
            "risk_score": f.risk_score,
            "confidence": f.confidence,
            "advisory_only": f.advisory_only,
            "deterministic_version": f.deterministic_version,
            "input_hash": f.input_hash,
            "immutable_hash": f.immutable_hash,
            "created_at": str(f.created_at),
        }
        for f in forecasts
    ]


@router.post(
    "/failure-risk-assessments",
    response_model=FailureRiskAssessmentCreateResponse,
)
async def create_failure_risk_assessment(
    body: FailureRiskAssessmentCreate,
    session: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin),
) -> Any:
    stmt = select(FailureForecast).where(FailureForecast.id == body.forecast_id)
    result = await session.execute(stmt)
    forecast_model = result.scalar_one_or_none()
    if not forecast_model:
        raise HTTPException(status_code=404, detail="forecast not found")
    if forecast_model.client_id != body.client_id:
        raise HTTPException(status_code=404, detail="forecast not found")

    forecast_dict = {
        "forecast_type": forecast_model.forecast_type,
        "risk_score": forecast_model.risk_score or 0.0,
        "confidence": forecast_model.confidence or 0.0,
        "deterministic_version": forecast_model.deterministic_version or "v1",
        "input_hash": forecast_model.input_hash or "",
        "advisory_only": forecast_model.advisory_only,
        "client_id": body.client_id,
    }

    assessment_dict = SCORING.build_assessment(forecast_dict, dry_run=body.dry_run)

    assessment = FailureRiskAssessment(
        client_id=body.client_id,
        forecast_id=body.forecast_id,
        risk_level=assessment_dict["risk_level"],
        recommendation=assessment_dict["recommendation"],
        requires_approval=assessment_dict["requires_approval"],
        dry_run=assessment_dict["dry_run"],
        advisory_only=assessment_dict["advisory_only"],
        immutable_hash=assessment_dict["immutable_hash"],
    )
    session.add(assessment)
    await session.commit()
    await session.refresh(assessment)

    assessment_result = {
        "id": str(assessment.id),
        "client_id": assessment.client_id,
        "forecast_id": assessment.forecast_id,
        "risk_level": assessment.risk_level,
        "recommendation": assessment.recommendation,
        "requires_approval": assessment.requires_approval,
        "dry_run": assessment.dry_run,
        "advisory_only": assessment.advisory_only,
        "immutable_hash": assessment.immutable_hash,
        "created_at": str(assessment.created_at),
    }
    receipt = build_failure_risk_assessment_receipt(assessment_result)

    return FailureRiskAssessmentCreateResponse(
        assessment=_read_assessment(assessment),
        receipt=receipt,
    )


@router.get("/failure-risk-assessments", response_model=list[FailureRiskAssessmentRead])
async def list_failure_risk_assessments(
    client_id: str = Query(..., min_length=1),
    limit: int = Query(default=50, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
    admin: Any = Depends(get_current_admin),
) -> Any:
    stmt = (
        select(FailureRiskAssessment)
        .where(FailureRiskAssessment.client_id == client_id)
        .order_by(FailureRiskAssessment.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    assessments = result.scalars().all()
    return [_read_assessment(a) for a in assessments]
