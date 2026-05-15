from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commercial_autonomous_guardrails import CommercialExecutionBlastRadius
from app.services.routing.commercial_report_export import sanitize_report_payload


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def sha256_hex(payload: Any) -> str:
    if not isinstance(payload, str):
        payload = canonical_json(payload)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class BlastRadiusAnalysisService:
    BASE_SCORES = {
        "destructive_replay": 1.0,
        "tenant_quarantine": 0.75,
        "federation_sync": 0.65,
        "rollback": 0.70,
        "runtime_restart": 0.40,
        "safe_throttle": 0.20,
        "model_promotion": 0.55,
    }

    def _severity(self, score: float) -> str:
        if score >= 0.85:
            return "critical"
        if score >= 0.65:
            return "high"
        if score >= 0.35:
            return "medium"
        return "low"

    def score_request(self, request: dict[str, Any]) -> dict[str, Any]:
        sanitized = sanitize_report_payload(request)
        action_type = str(sanitized.get("action_type") or "unknown")
        base = self.BASE_SCORES.get(action_type, 0.3)

        affected_tenants = list(sanitized.get("affected_tenants") or [])
        target_clusters = list(sanitized.get("target_clusters") or [])
        runtime_nodes = list(sanitized.get("runtime_nodes") or [])

        factors = {
            "base_score": base,
            "tenant_multiplier": min(len(affected_tenants) * 0.12, 0.36),
            "cluster_multiplier": min(len(target_clusters) * 0.10, 0.30),
            "runtime_multiplier": min(len(runtime_nodes) * 0.05, 0.20),
            "destructive_bonus": 0.2 if sanitized.get("destructive") else 0.0,
            "rollback_bonus": 0.15 if sanitized.get("rollback_requested") else 0.0,
            "confidential_bonus": 0.12 if sanitized.get("confidential_scope") else 0.0,
            "federation_bonus": 0.15 if sanitized.get("federation_scope") else 0.0,
            "sovereign_bonus": 0.2 if sanitized.get("sovereign_scope") else 0.0,
        }
        raw_score = sum(factors.values())
        score = round(min(raw_score, 1.0), 6)
        scope = {
            "affected_tenants": affected_tenants,
            "cluster_count": len(target_clusters),
            "runtime_node_count": len(runtime_nodes),
            "global_scope": bool(sanitized.get("global_scope")),
        }
        reproducibility_hash = sha256_hex(
            {
                "action_type": action_type,
                "factors": factors,
                "scope": scope,
                "target_id": sanitized.get("target_id"),
                "target_type": sanitized.get("target_type"),
                "tenant_id": sanitized.get("tenant_id"),
            }
        )
        return {
            "action_type": action_type,
            "blast_radius_score": score,
            "risk_vector_json": factors,
            "scope_json": scope,
            "severity": self._severity(score),
            "reproducibility_hash": reproducibility_hash,
            "sanitized_request": sanitized,
        }

    async def analyze_and_record(
        self,
        db: AsyncSession,
        *,
        request: dict[str, Any],
        persist: bool = True,
    ) -> CommercialExecutionBlastRadius:
        analysis = self.score_request(request)
        existing = (
            await db.execute(
                select(CommercialExecutionBlastRadius).where(
                    CommercialExecutionBlastRadius.reproducibility_hash == analysis["reproducibility_hash"]
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing
        sanitized_request = analysis["sanitized_request"]
        row = CommercialExecutionBlastRadius(
            action_type=analysis["action_type"],
            target_type=str(sanitized_request.get("target_type") or "unknown"),
            target_id=sanitized_request.get("target_id"),
            tenant_id=sanitized_request.get("tenant_id"),
            cluster_id=sanitized_request.get("cluster_id"),
            scope_json=analysis["scope_json"],
            risk_vector_json=analysis["risk_vector_json"],
            blast_radius_score=analysis["blast_radius_score"],
            severity=analysis["severity"],
            reproducibility_hash=analysis["reproducibility_hash"],
            blocked=False,
        )
        db.add(row)
        if persist:
            await db.commit()
            await db.refresh(row)
        else:
            await db.flush()
        return row
