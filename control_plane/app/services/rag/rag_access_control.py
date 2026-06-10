from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from app.core.config import get_settings
from app.models.commercial.commercial_confidential_runtime import CommercialConfidentialRuntimeProfile
from app.models.commercial.commercial_model_supply_chain import CommercialSignedModelRegistryEntry
from app.models.commercial.commercial_rag_vault import (
    CommercialRAGAccessPolicy,
    CommercialRAGDocument,
    CommercialRAGLegalHold,
    CommercialRAGVault,
)
from app.services.rag.rag_vault import resolve_vault_policy
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

settings = get_settings()


class RetrievalAccessDenied(PermissionError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass
class RetrievalAccessContext:
    vault: CommercialRAGVault
    policy: CommercialRAGAccessPolicy | None
    policy_mode: str
    allowed: bool
    reasons: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    max_context_chunks: int = 0


async def evaluate_retrieval_access(
    session: AsyncSession,
    *,
    vault: CommercialRAGVault,
    request_client_id: uuid.UUID | None,
    requested_model: str | None,
    user_identity: str | None,
    abac_attributes: dict[str, Any] | None,
) -> RetrievalAccessContext:
    policy = await resolve_vault_policy(session, vault.id)
    policy_mode = policy.policy_mode if policy else settings.commercial_rag_vault_policy_mode
    ctx = RetrievalAccessContext(
        vault=vault,
        policy=policy,
        policy_mode=policy_mode,
        allowed=True,
        max_context_chunks=(policy.max_context_chunks if policy else settings.commercial_rag_vault_max_context_chunks),
    )

    def add_violation(reason: str) -> None:
        ctx.violations.append(reason)
        if policy_mode == "enforce":
            ctx.allowed = False
            ctx.reasons.append(reason)

    if vault.client_id and request_client_id and vault.client_id != request_client_id:
        if not policy or not policy.allow_cross_tenant:
            add_violation("cross_tenant_blocked")

    if policy and policy.require_abac:
        attrs = abac_attributes or {}
        if not attrs.get("role"):
            add_violation("abac_missing_role")
        if not attrs.get("purpose"):
            add_violation("abac_missing_purpose")

    if getattr(settings, "commercial_rag_vault_require_confidential_runtime", False) or (policy and policy.require_confidential_runtime):
        stmt = select(CommercialConfidentialRuntimeProfile).where(
            CommercialConfidentialRuntimeProfile.client_id == str(request_client_id),
            CommercialConfidentialRuntimeProfile.enabled == True,
        )
        profile = (await session.execute(stmt)).scalar_one_or_none()
        if profile is None:
            add_violation("confidential_runtime_required")

    if requested_model and policy and policy.require_trusted_model:
        stmt = select(CommercialSignedModelRegistryEntry).where(
            CommercialSignedModelRegistryEntry.model_name == requested_model
        )
        entry = (await session.execute(stmt)).scalar_one_or_none()
        if entry is None or entry.trust_state != "trusted":
            add_violation("trusted_model_required")

    if user_identity is None and policy_mode == "enforce":
        add_violation("user_identity_missing")

    if not ctx.allowed:
        raise RetrievalAccessDenied(",".join(ctx.reasons))

    return ctx


async def validate_document_access(
    session: AsyncSession,
    *,
    document: CommercialRAGDocument,
    policy: CommercialRAGAccessPolicy | None,
) -> list[str]:
    violations: list[str] = []
    if (getattr(settings, "commercial_rag_vault_require_signed_documents", False) or (policy and policy.require_signed_document)) and not document.signed_manifest_hash:
        violations.append("unsigned_document")

    if document.legal_hold:
        violations.append("document_legal_hold")

    stmt = select(CommercialRAGLegalHold).where(
        CommercialRAGLegalHold.vault_id == document.vault_id,
        CommercialRAGLegalHold.active == True,
        (
            (CommercialRAGLegalHold.document_id == None)
            | (CommercialRAGLegalHold.document_id == document.id)
        ),
    )
    holds = (await session.execute(stmt)).scalars().all()
    if holds:
        violations.append("active_legal_hold")

    return violations


def evaluate_chunk_acl(
    acl_json: dict[str, Any] | None,
    *,
    request_client_id: uuid.UUID | None,
    user_identity: str | None,
    abac_attributes: dict[str, Any] | None,
) -> list[str]:
    acl = acl_json or {}
    violations: list[str] = []

    allowed_clients = acl.get("allowed_client_ids") or []
    if allowed_clients and request_client_id and str(request_client_id) not in {str(v) for v in allowed_clients}:
        violations.append("acl_client_mismatch")

    allowed_users = acl.get("allowed_user_hashes") or []
    if allowed_users and user_identity and user_identity not in allowed_users:
        violations.append("acl_user_mismatch")

    allowed_roles = set(acl.get("allowed_roles") or [])
    role = (abac_attributes or {}).get("role")
    if allowed_roles and role not in allowed_roles:
        violations.append("acl_role_mismatch")

    return violations
