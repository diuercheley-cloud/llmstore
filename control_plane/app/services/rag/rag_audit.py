from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from app.core.config import get_settings
from app.models.commercial_rag_vault import CommercialRAGRetrievalAudit, CommercialRAGVault
from app.services.governance.federated_audit import FederatedAuditService
from app.services.routing.commercial_report_export import sanitize_report_payload
from sqlalchemy.ext.asyncio import AsyncSession

settings = get_settings()


def _canonical(payload: Any) -> str:
    return json.dumps(sanitize_report_payload(payload), sort_keys=True, ensure_ascii=True, separators=(",", ":"), default=str)


def hash_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def immutable_audit_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical({"kind": "rag_retrieval_audit", **payload}).encode("utf-8")).hexdigest()


async def record_retrieval_audit(
    session: AsyncSession,
    *,
    vault: CommercialRAGVault,
    client_id: uuid.UUID | None,
    request_payload: dict[str, Any],
    retrieval_payload: dict[str, Any],
    user_identity: str | None,
    retrieved_chunk_count: int,
    policy_result: str,
    model_id: str | None,
) -> CommercialRAGRetrievalAudit:
    request_hash = hash_payload(request_payload)
    retrieval_hash = hash_payload(retrieval_payload)
    immutable_hash = None
    if settings.commercial_rag_vault_enable_immutable_audit and vault.immutable_audit_enabled:
        immutable_hash = immutable_audit_hash(
            {
                "vault_id": str(vault.id),
                "client_id": str(client_id) if client_id else None,
                "request_hash": request_hash,
                "retrieval_hash": retrieval_hash,
                "policy_result": policy_result,
                "retrieved_chunk_count": retrieved_chunk_count,
                "model_id": model_id,
            }
        )

    audit = CommercialRAGRetrievalAudit(
        vault_id=vault.id,
        client_id=client_id,
        request_hash=request_hash,
        retrieval_hash=retrieval_hash,
        user_identity_hash=hash_payload({"user_identity": user_identity}) if user_identity else None,
        retrieved_chunk_count=retrieved_chunk_count,
        policy_result=policy_result,
        model_id=model_id,
        immutable_hash=immutable_hash,
    )
    session.add(audit)
    await session.flush()

    if settings.commercial_governance_federation_enabled and immutable_hash:
        service = FederatedAuditService()
        await service.ingest_audit_events(
            session,
            events=[
                {
                    "source_event_id": str(audit.id),
                    "event_type": "evidence_package",
                    "event_payload": {
                        "category": "regulated_rag_retrieval",
                        "immutable_hash": immutable_hash,
                        "vault_id": str(vault.id),
                        "request_hash": request_hash,
                    },
                }
            ],
            source_cluster_id=settings.commercial_governance_federation_cluster_id,
            peer_token=settings.commercial_governance_federation_shared_token or None,
        )
    return audit
