from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from app.core.config import get_settings
from app.models.commercial_rag_vault import CommercialRAGPoisoningAlert
from app.services.rag.rag_vault import sanitize_text
from sqlalchemy.ext.asyncio import AsyncSession

settings = get_settings()

INJECTION_PATTERNS = [
    (r"ignore\s+previous\s+instructions", "prompt_injection", "high"),
    (r"system\s+override", "prompt_injection", "high"),
    (r"you\s+must\s+reveal", "prompt_injection", "medium"),
    (r"authority[: ]+ceo|authority[: ]+admin", "authority_mimicry", "medium"),
    (r"cross[\s-]?tenant|another\s+tenant", "cross_tenant_attempt", "high"),
    (r"root\s+credentials|private\s+key|secret\s+token", "poisoned_chunk", "critical"),
]


@dataclass
class PoisonDetectionResult:
    flagged: bool
    alert_type: str | None = None
    severity: str = "low"
    summary: str = ""


def inspect_text_for_poisoning(text: str) -> PoisonDetectionResult:
    haystack = (text or "").lower()
    for pattern, alert_type, severity in INJECTION_PATTERNS:
        if re.search(pattern, haystack):
            return PoisonDetectionResult(
                flagged=True,
                alert_type=alert_type,
                severity=severity,
                summary=sanitize_text(f"Heuristic match for {alert_type}: {pattern}", max_len=255),
            )

    token_count = len(haystack.split())
    if token_count > 0:
        repeated_ratio = haystack.count("!!!") + haystack.count("###")
        if repeated_ratio >= 3:
            return PoisonDetectionResult(
                flagged=True,
                alert_type="abnormal_retrieval_pattern",
                severity="medium",
                summary="Repeated delimiter pattern suggests poisoning or instruction stuffing",
            )

    return PoisonDetectionResult(flagged=False)


async def create_poison_alert(
    session: AsyncSession,
    *,
    vault_id: uuid.UUID,
    alert_type: str,
    severity: str,
    summary: str,
) -> CommercialRAGPoisoningAlert:
    alert = CommercialRAGPoisoningAlert(
        vault_id=vault_id,
        alert_type=alert_type,
        severity=severity,
        summary=sanitize_text(summary, max_len=255),
        resolved=False,
    )
    session.add(alert)
    await session.flush()
    return alert


async def analyze_and_record_poisoning(
    session: AsyncSession,
    *,
    vault_id: uuid.UUID,
    text: str,
) -> PoisonDetectionResult:
    if not getattr(settings, "commercial_rag_vault_enable_poison_detection", True):
        return PoisonDetectionResult(flagged=False)

    result = inspect_text_for_poisoning(text)
    if result.flagged and result.alert_type:
        await create_poison_alert(
            session,
            vault_id=vault_id,
            alert_type=result.alert_type,
            severity=result.severity,
            summary=result.summary,
        )
    return result
