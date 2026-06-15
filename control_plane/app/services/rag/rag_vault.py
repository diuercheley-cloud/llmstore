from __future__ import annotations

import hashlib
import json
import re
import uuid
from typing import Any

from app.core.config import get_settings
from app.models.commercial.commercial_rag_vault import (
    CommercialRAGAccessPolicy,
    CommercialRAGChunk,
    CommercialRAGDocument,
    CommercialRAGVault,
)
from app.models.core.client import Client
from app.services.routing.commercial_report_export import sanitize_report_payload
from app.services.security.tenant_encryption import TenantEncryptionService
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

settings = get_settings()

SENSITIVE_CLASSIFICATIONS = {"confidential", "restricted", "sovereign_restricted"}
DEFAULT_ABAC = {"allowed_roles": ["tenant_user", "tenant_admin"], "regions": ["local"]}


def hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json(payload: Any) -> str:
    return json.dumps(
        payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"), default=str
    )


def sanitize_text(value: str, *, max_len: int = 255) -> str:
    cleaned = re.sub(r"[\x00-\x1f\x7f]+", " ", value or "").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:max_len]


def sanitize_metadata(payload: dict[str, Any] | None) -> dict[str, Any]:
    return sanitize_report_payload(payload or {})


def build_signed_manifest_hash(
    *,
    document_hash: str,
    provenance_hash: str | None,
    source_type: str,
    client_id: str | None,
) -> str:
    manifest = {
        "document_hash": document_hash,
        "provenance_hash": provenance_hash,
        "source_type": source_type,
        "client_id": client_id,
    }
    return hash_text(canonical_json(manifest))


async def get_or_create_default_vault(
    session: AsyncSession,
    *,
    client_id: uuid.UUID | None,
) -> CommercialRAGVault:
    stmt = select(CommercialRAGVault).where(
        CommercialRAGVault.client_id == client_id,
        CommercialRAGVault.vault_name == "default-regulated-vault",
    )
    vault = (await session.execute(stmt)).scalar_one_or_none()
    if vault:
        return vault

    vault = CommercialRAGVault(
        client_id=client_id,
        vault_name="default-regulated-vault",
        vault_mode="confidential" if client_id else "standard",
        encryption_required=bool(client_id),
        retrieval_mode="hybrid",
        immutable_audit_enabled=settings.commercial_rag_vault_enable_immutable_audit,
    )
    session.add(vault)
    await session.flush()

    policy = CommercialRAGAccessPolicy(
        vault_id=vault.id,
        policy_name="default-regulated-policy",
        policy_mode=settings.commercial_rag_vault_policy_mode,
        allow_cross_tenant=False,
        require_abac=True,
        require_signed_document=settings.commercial_rag_vault_require_signed_documents,
        require_confidential_runtime=settings.commercial_rag_vault_require_confidential_runtime,
        require_trusted_model=False,
        max_context_chunks=settings.commercial_rag_vault_max_context_chunks,
    )
    session.add(policy)
    await session.flush()
    return vault


async def resolve_vault_policy(
    session: AsyncSession,
    vault_id: uuid.UUID,
) -> CommercialRAGAccessPolicy | None:
    stmt = (
        select(CommercialRAGAccessPolicy)
        .where(CommercialRAGAccessPolicy.vault_id == vault_id)
        .order_by(desc(CommercialRAGAccessPolicy.updated_at))
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def register_document(
    session: AsyncSession,
    *,
    vault: CommercialRAGVault,
    title: str,
    plaintext: str,
    classification: str,
    source_type: str,
    metadata_json: dict[str, Any] | None,
    provenance_hash: str | None = None,
    signed_manifest_hash: str | None = None,
    legal_hold: bool = False,
) -> CommercialRAGDocument:
    safe_title = sanitize_text(title)
    safe_metadata = sanitize_metadata(metadata_json)
    document_hash = hash_text(plaintext)
    document = CommercialRAGDocument(
        vault_id=vault.id,
        document_hash=document_hash,
        document_title=safe_title,
        classification=classification,
        ingestion_status="indexed",
        source_type=sanitize_text(source_type, max_len=64),
        provenance_hash=provenance_hash,
        signed_manifest_hash=signed_manifest_hash
        or build_signed_manifest_hash(
            document_hash=document_hash,
            provenance_hash=provenance_hash,
            source_type=source_type,
            client_id=str(vault.client_id) if vault.client_id else None,
        ),
        legal_hold=legal_hold,
        metadata_json=safe_metadata,
    )
    session.add(document)
    await session.flush()
    return document


async def register_chunk(
    session: AsyncSession,
    *,
    document: CommercialRAGDocument,
    chunk_index: int,
    plaintext: str,
    embedding: list[float] | None,
    acl_json: dict[str, Any] | None,
    encrypt_payload: bool,
    client_id: uuid.UUID | None,
) -> CommercialRAGChunk:
    encrypted_payload = None
    safe_acl = sanitize_metadata(acl_json or DEFAULT_ABAC)
    if encrypt_payload:
        svc = TenantEncryptionService(settings)
        artifact = await svc.encrypt_payload(
            session,
            client_id,
            plaintext,
            artifact_type="rag_chunk",
            resource_type="commercial_rag_vault_chunk",
            resource_id=str(document.id),
            key_purpose="rag_vault",
        )
        encrypted_payload = artifact.encrypted_payload
        safe_acl["encryption_artifact_id"] = str(artifact.id)

    chunk = CommercialRAGChunk(
        document_id=document.id,
        chunk_hash=hash_text(plaintext),
        chunk_index=chunk_index,
        embedding_hash=hash_text(canonical_json(embedding)) if embedding is not None else None,
        acl_json=safe_acl,
        encrypted_payload=encrypted_payload,
        poisoned_flag=False,
    )
    session.add(chunk)
    await session.flush()
    return chunk


def should_encrypt_payload(vault: CommercialRAGVault, classification: str) -> bool:
    return vault.encryption_required or classification in SENSITIVE_CLASSIFICATIONS


def should_store_plaintext(classification: str) -> bool:
    return classification not in SENSITIVE_CLASSIFICATIONS


def sanitize_chunk_preview(plaintext: str) -> str:
    preview = sanitize_text(plaintext, max_len=96)
    return (
        f"[redacted-regulated-chunk:{hash_text(preview)[:16]}]"
        if preview
        else "[redacted-regulated-chunk]"
    )


async def tenant_client_lookup(
    session: AsyncSession,
    client_id: uuid.UUID | None,
) -> Client | None:
    if client_id is None:
        return None
    return await session.get(Client, client_id)
