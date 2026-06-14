# Owner: platform-ops
import json
import logging
import os
import uuid
from typing import Optional

from app.api.client import _chat_with_fallback
from app.api.deps import get_inference_proxy
from app.core.config import get_settings
from app.services.runtime_dependencies import get_db_session
from app.models.core.client import Client
from app.models.commercial.commercial_rag_vault import (
    CommercialRAGDocument,
    CommercialRAGLegalHold,
    CommercialRAGPoisoningAlert,
    CommercialRAGRetrievalAudit,
    CommercialRAGVault,
)
from app.models.commercial.commercial_retrieval_proofs import CommercialRetrievalProof
from app.models.rag.rag_collection import RAGCollection
from app.models.rag.rag_document import RAGDocument
from app.models.rag.rag_document_chunk import RAGDocumentChunk
from app.services.auth import AdminRole, require_admin_role, require_client
from app.services.billing.core import resolve_effective_plan_for_session
from app.services.model_policy import resolve_requested_model
from app.services.quota import QuotaExceeded, ensure_quota, record_usage
from app.services.rag.rag_access_control import RetrievalAccessDenied
from app.services.rag.rag_audit import record_retrieval_audit
from app.services.rag.rag_vault import get_or_create_default_vault
from app.services.rag.rag_vault import register_document as register_regulated_document
from app.services.rag.rag_vault import sanitize_metadata as sanitize_rag_metadata
from app.services.rag.rag_vault import sanitize_text as sanitize_rag_text
from app.services.rag.retrieval_proofs import (
    export_retrieval_proof,
    generate_retrieval_proof,
    replay_retrieval_proof,
    verify_lineage_consistency,
    verify_retrieval_proof,
)
from app.services.rag_enterprise.ingestion import delete_enterprise_document, ingest_document
from app.services.rag_enterprise.parsers import (
    get_parser_status,
)
from app.services.rag_enterprise.policies import (
    check_file_type_allowed,
    check_quota_documents,
    check_quota_storage,
    is_cloud_embedding_allowed,
    resolve_enterprise_rag_policy,
)
from app.services.rag_enterprise.retrieval import build_rag_context, execute_enterprise_query
from app.services.rag_enterprise.schemas import (
    AdminOverview,
    CollectionCreate,
    CollectionListResponse,
    CollectionResponse,
    EnterpriseDocumentListResponse,
    EnterpriseDocumentResponse,
    EnterpriseQueryRequest,
    EnterpriseQueryResponse,
)
from app.services.rag_usage import (
    check_rag_feature_blocked,
    get_rag_usage_and_limits,
    record_rag_event,
)
from app.utils.token_estimator import estimate_tokens_from_text
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/v1/rag", tags=["rag_enterprise"])
admin_router = APIRouter(prefix="/admin/rag", tags=["admin_rag"])


class AdminVaultCreatePayload(BaseModel):
    client_id: uuid.UUID | None = None
    vault_name: str
    vault_mode: str = "standard"
    encryption_required: bool = False
    retrieval_mode: str = "hybrid"
    retention_policy_days: int | None = 30
    immutable_audit_enabled: bool = True


class AdminDocumentCreatePayload(BaseModel):
    vault_id: uuid.UUID
    document_title: str
    plaintext: str = ""
    classification: str = "internal"
    source_type: str = "admin"
    provenance_hash: str | None = None
    signed_manifest_hash: str | None = None
    legal_hold: bool = False
    metadata_json: dict | None = None


class AdminLegalHoldCreatePayload(BaseModel):
    vault_id: uuid.UUID
    document_id: uuid.UUID | None = None
    hold_reason: str


class AdminRetrievalReplayPayload(BaseModel):
    replay_sources: list[dict]


# --- Helper ---

def _check_rag_enabled():
    if not settings.rag_enabled:
        raise HTTPException(status_code=403, detail="RAG is disabled")


async def _check_client_rag(session, client):
    _check_rag_enabled()
    is_blocked, reason = await check_rag_feature_blocked(session, client.id)
    if is_blocked:
        raise HTTPException(status_code=403, detail=f"RAG feature blocked: {reason}")
    usage_info = await get_rag_usage_and_limits(session, client)
    if not usage_info["rag_enabled"]:
        raise HTTPException(status_code=403, detail="RAG is not enabled for your plan")
    return usage_info


# --- Collections ---

@router.post("/collections", response_model=CollectionResponse)
async def create_collection(
    payload: CollectionCreate,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    await _check_client_rag(session, client)
    col = RAGCollection(
        client_id=client.id,
        name=payload.name,
        description=payload.description,
        tags=payload.tags,
    )
    session.add(col)
    await session.commit()
    await session.refresh(col)
    return CollectionResponse(
        id=col.id, name=col.name, description=col.description,
        document_count=0, tags=col.tags, created_at=col.created_at,
    )


@router.get("/collections", response_model=CollectionListResponse)
async def list_collections(
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    await _check_client_rag(session, client)
    cols = (await session.execute(
        select(RAGCollection).where(RAGCollection.client_id == client.id)
    )).scalars().all()
    data = []
    for col in cols:
        count_result = await session.execute(
            select(func.count(RAGDocument.id)).where(RAGDocument.client_id == client.id)
        )
        doc_count = count_result.scalar() or 0
        data.append(CollectionResponse(
            id=col.id, name=col.name, description=col.description,
            document_count=doc_count, tags=col.tags, created_at=col.created_at,
        ))
    return CollectionListResponse(data=data)


# --- Documents ---

@router.post("/documents", response_model=EnterpriseDocumentResponse)
async def upload_enterprise_document(
    file: UploadFile = File(...),
    collection_id: Optional[uuid.UUID] = Query(None),
    tags: Optional[str] = Query(None),
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    usage_info = await _check_client_rag(session, client)
    policy = await resolve_enterprise_rag_policy(session, client)

    ext = os.path.splitext(file.filename)[1].lower()
    allowed, msg = await check_file_type_allowed(file.filename, policy)
    if not allowed:
        raise HTTPException(status_code=400, detail=msg)

    content = await file.read()
    file_size = len(content)
    file_size_mb = file_size / (1024 * 1024)

    if file_size_mb > settings.rag_max_file_mb:
        raise HTTPException(status_code=413, detail=f"File too large. Max {settings.rag_max_file_mb}MB")

    doc_ok, doc_msg = await check_quota_documents(session, client.id, policy)
    if not doc_ok:
        return JSONResponse(status_code=429, content={
            "error": "rag_limit_exceeded",
            "limit": "rag_max_documents",
            "current": usage_info["usage"]["documents_count"],
            "max": policy.max_documents,
            "plan": usage_info["plan"],
        })

    storage_ok, storage_msg = await check_quota_storage(session, client.id, policy, file_size)
    if not storage_ok:
        return JSONResponse(status_code=429, content={
            "error": "rag_limit_exceeded",
            "limit": "rag_max_storage_mb",
            "current": usage_info["usage"]["storage_mb"],
            "max": policy.max_storage_mb,
            "plan": usage_info["plan"],
        })

    ext = os.path.splitext(file.filename)[1].lower()
    parser_status = get_parser_status(ext)
    if not parser_status.available:
        raise HTTPException(status_code=400, detail={
            "error": "parser_unavailable",
            "extension": ext,
            "dependency": parser_status.dependency,
            "remediation": parser_status.remediation,
            "message": f"Parser for {ext} is not available. Install {parser_status.dependency}.",
        })

    client_storage_dir = os.path.join(settings.rag_storage_dir, str(client.id), "enterprise")
    os.makedirs(client_storage_dir, exist_ok=True)

    file_id = uuid.uuid4()
    internal_filename = f"{file_id}{ext}"
    storage_path = os.path.join(client_storage_dir, internal_filename)

    with open(storage_path, "wb") as f:
        f.write(content)

    parsed_tags = None
    if tags:
        try:
            parsed_tags = json.loads(tags)
        except (json.JSONDecodeError, TypeError):
            parsed_tags = [tags]

    try:
        doc = await ingest_document(
            session=session,
            client_id=client.id,
            file_path=storage_path,
            original_filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
            file_size_bytes=file_size,
            collection_id=collection_id,
            tags=parsed_tags,
        )
    except ImportError as e:
        if os.path.exists(storage_path):
            os.remove(storage_path)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        if os.path.exists(storage_path):
            os.remove(storage_path)
        logger.exception(f"Enterprise RAG ingest failed for {file.filename}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

    return EnterpriseDocumentResponse(
        id=doc.id,
        filename=doc.filename,
        original_filename=doc.original_filename,
        content_type=doc.content_type,
        file_size_bytes=doc.file_size_bytes,
        status=doc.status,
        page_count=doc.page_count,
        chunk_count=doc.chunk_count,
        collection_id=collection_id,
        tags=parsed_tags,
        created_at=doc.created_at,
        processed_at=doc.processed_at,
    )


@router.get("/documents", response_model=EnterpriseDocumentListResponse)
async def list_enterprise_documents(
    collection_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    await _check_client_rag(session, client)

    stmt = select(RAGDocument).where(RAGDocument.client_id == client.id)
    count_stmt = select(func.count(RAGDocument.id)).where(RAGDocument.client_id == client.id)

    if status:
        stmt = stmt.where(RAGDocument.status == status)
        count_stmt = count_stmt.where(RAGDocument.status == status)

    total = (await session.execute(count_stmt)).scalar() or 0
    docs = (await session.execute(
        stmt.order_by(RAGDocument.created_at.desc()).offset(offset).limit(limit)
    )).scalars().all()

    data = [
        EnterpriseDocumentResponse(
            id=d.id, filename=d.filename, original_filename=d.original_filename,
            content_type=d.content_type, file_size_bytes=d.file_size_bytes,
            status=d.status, page_count=d.page_count, chunk_count=d.chunk_count,
            error_message=d.error_message, created_at=d.created_at,
            processed_at=d.processed_at,
        )
        for d in docs
    ]
    return EnterpriseDocumentListResponse(data=data, total=total)


@router.get("/documents/{doc_id}", response_model=EnterpriseDocumentResponse)
async def get_enterprise_document(
    doc_id: uuid.UUID,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    await _check_client_rag(session, client)
    doc = (await session.execute(
        select(RAGDocument).where(RAGDocument.id == doc_id, RAGDocument.client_id == client.id)
    )).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return EnterpriseDocumentResponse(
        id=doc.id, filename=doc.filename, original_filename=doc.original_filename,
        content_type=doc.content_type, file_size_bytes=doc.file_size_bytes,
        status=doc.status, page_count=doc.page_count, chunk_count=doc.chunk_count,
        error_message=doc.error_message, created_at=doc.created_at,
        processed_at=doc.processed_at,
    )


@router.delete("/documents/{doc_id}")
async def delete_enterprise_document_endpoint(
    doc_id: uuid.UUID,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    await _check_client_rag(session, client)
    doc = (await session.execute(
        select(RAGDocument).where(RAGDocument.id == doc_id, RAGDocument.client_id == client.id)
    )).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_size = doc.file_size_bytes
    await delete_enterprise_document(session, doc)
    await record_rag_event(session, client.id, "document_deleted", document_id=doc_id, storage_bytes=-file_size)
    await session.commit()
    return {"status": "deleted"}


# --- Query ---

async def query_enterprise_rag(
    payload: EnterpriseQueryRequest,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
    proxy = Depends(get_inference_proxy),
):
    usage_info = await _check_client_rag(session, client)
    limits = usage_info["limits"]
    usage = usage_info["usage"]

    if limits["max_queries_per_month"] is not None and usage["queries_month"] >= limits["max_queries_per_month"]:
        return JSONResponse(status_code=429, content={
            "error": "rag_limit_exceeded",
            "limit": "rag_max_queries_per_month",
            "current": usage["queries_month"],
            "max": limits["max_queries_per_month"],
            "plan": usage_info["plan"],
        })

    policy = await resolve_enterprise_rag_policy(session, client)
    cloud_allowed = await is_cloud_embedding_allowed(client, policy)

    try:
        sources, scores, retrieval_audit = await execute_enterprise_query(
            session=session,
            client_id=client.id,
            question=payload.question,
            top_k=payload.top_k,
            score_threshold=payload.score_threshold,
            document_ids=payload.document_ids,
            collection_ids=payload.collection_ids,
            cloud_allowed=cloud_allowed,
            user_identity=payload.user_identity,
            requested_model=payload.model,
            abac_attributes=payload.abac_attributes,
            return_audit=True,
        )
    except RetrievalAccessDenied as exc:
        raise HTTPException(status_code=403, detail=f"Regulated RAG policy denied retrieval: {exc.reason}")

    if not sources:
        return EnterpriseQueryResponse(
            answer="Não encontrei nenhum documento para consultar.",
            sources=[],
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        )

    context_str = build_rag_context(sources)

    prompt = f"""Você é um assistente que responde usando apenas o contexto fornecido abaixo.
Se a resposta não estiver no contexto, diga que não encontrou informação suficiente nos documentos.
Cite as fontes por nome do arquivo e página.

Contexto:
{context_str}

Pergunta:
{payload.question}

Resposta:"""

    selected_model, _ = await resolve_requested_model(session, client=client, requested_model=payload.model)
    effective_plan = await resolve_effective_plan_for_session(session, client)

    from app.services.tokenizer_service import get_tokenizer_service
    tokenizer = get_tokenizer_service()
    token_res = await tokenizer.count_text_tokens(prompt, model=selected_model.model_id)
    prompt_tokens = token_res.input_tokens
    token_count_method = token_res.method
    tokens_estimated = token_res.is_estimated
    incoming_tokens = prompt_tokens + payload.max_tokens

    try:
        await ensure_quota(
            session, client.id,
            effective_plan.daily_token_quota,
            effective_plan.weekly_token_quota,
            effective_plan.monthly_token_quota,
            incoming_tokens,
        )
    except QuotaExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc))

    chat_payload = {
        "model": selected_model.model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": payload.max_tokens,
        "temperature": payload.temperature,
    }

    result = await _chat_with_fallback(proxy, selected_model, chat_payload, False, False, client=client)
    response_payload = json.loads(result.response.body.decode("utf-8"))
    answer = (response_payload.get("choices") or [{}])[0].get("message", {}).get("content", "")

    completion_tokens = estimate_tokens_from_text(answer)

    await record_usage(
        session, 
        client.id, 
        prompt_tokens, 
        completion_tokens,
        token_count_method=token_count_method,
        tokens_estimated=tokens_estimated
    )
    await record_rag_event(session, client.id, "rag_query", quantity=1)
    await record_rag_event(session, client.id, "rag_query_tokens", quantity=prompt_tokens + completion_tokens)

    if settings.commercial_rag_vault_enabled:
        vault = await get_or_create_default_vault(session, client_id=client.id)
        audit = await record_retrieval_audit(
            session,
            vault=vault,
            client_id=client.id,
            request_payload={
                "question": payload.question,
                "document_ids": [str(item) for item in (payload.document_ids or [])],
                "collection_ids": [str(item) for item in (payload.collection_ids or [])],
                "user_identity": payload.user_identity,
            },
            retrieval_payload={
                "retrieval_audit": retrieval_audit,
                "source_count": len(sources),
                "scores": scores,
            },
            user_identity=payload.user_identity,
            retrieved_chunk_count=len(sources),
            policy_result=retrieval_audit.get("policy_result", "allow"),
            model_id=selected_model.model_id,
        )
        await generate_retrieval_proof(
            session,
            vault=vault,
            audit=audit,
            sources=sources,
            retrieval_metadata=retrieval_audit,
            model_id=selected_model.model_id,
        )

    await session.commit()

    return EnterpriseQueryResponse(
        answer=answer,
        sources=sources,
        usage={
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    )


# --- Admin Endpoints ---

@admin_router.get("/overview")
async def admin_rag_overview(
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(require_admin_role(AdminRole.READ)),
):
    total_docs = (await session.execute(select(func.count(RAGDocument.id)))).scalar() or 0
    total_chunks = (await session.execute(select(func.count(RAGDocumentChunk.id)))).scalar() or 0
    storage_result = await session.execute(select(func.sum(RAGDocument.file_size_bytes)))
    total_storage = storage_result.scalar() or 0
    total_cols = (await session.execute(select(func.count(RAGCollection.id)))).scalar() or 0

    clients_with_rag = (await session.execute(
        select(func.count(func.distinct(RAGDocument.client_id)))
    )).scalar() or 0

    status_rows = await session.execute(
        select(RAGDocument.status, func.count(RAGDocument.id)).group_by(RAGDocument.status)
    )
    docs_by_status = dict(status_rows.all())

    client_results = await session.execute(
        select(
            RAGDocument.client_id,
            func.count(RAGDocument.id).label("doc_count"),
            func.sum(RAGDocument.file_size_bytes).label("storage"),
        ).group_by(RAGDocument.client_id)
    )
    clients_data = []
    for row in client_results.mappings():
        clients_data.append({
            "client_id": str(row["client_id"]),
            "documents": row["doc_count"],
            "storage_bytes": row["storage"] or 0,
        })

    return AdminOverview(
        total_documents=total_docs,
        total_collections=total_cols,
        total_chunks=total_chunks,
        total_storage_bytes=total_storage,
        total_clients_with_rag=clients_with_rag,
        documents_by_status=docs_by_status,
        clients=clients_data,
    )


@admin_router.get("/clients/{client_id}/documents")
async def admin_list_client_documents(
    client_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(require_admin_role(AdminRole.READ)),
):
    docs = (await session.execute(
        select(RAGDocument).where(RAGDocument.client_id == client_id)
    )).scalars().all()
    return EnterpriseDocumentListResponse(
        data=[
            EnterpriseDocumentResponse(
                id=d.id, filename=d.filename, original_filename=d.original_filename,
                content_type=d.content_type, file_size_bytes=d.file_size_bytes,
                status=d.status, page_count=d.page_count, chunk_count=d.chunk_count,
                error_message=d.error_message, created_at=d.created_at,
                processed_at=d.processed_at,
            )
            for d in docs
        ],
        total=len(docs),
    )


@admin_router.get("/vaults")
async def admin_list_vaults(
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(require_admin_role(AdminRole.READ)),
):
    rows = (await session.execute(select(CommercialRAGVault).order_by(CommercialRAGVault.created_at.desc()))).scalars().all()
    return [
        {
            "id": str(item.id),
            "client_id": str(item.client_id) if item.client_id else None,
            "vault_name": item.vault_name,
            "vault_mode": item.vault_mode,
            "encryption_required": item.encryption_required,
            "retrieval_mode": item.retrieval_mode,
            "retention_policy_seconds": item.retention_policy_seconds,
            "immutable_audit_enabled": item.immutable_audit_enabled,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        }
        for item in rows
    ]


@admin_router.post("/vaults")
async def admin_create_vault(
    payload: AdminVaultCreatePayload,
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(require_admin_role(AdminRole.WRITE)),
):
    vault = CommercialRAGVault(
        client_id=payload.client_id,
        vault_name=sanitize_rag_text(payload.vault_name),
        vault_mode=payload.vault_mode,
        encryption_required=payload.encryption_required,
        retrieval_mode=payload.retrieval_mode,
        retention_policy_days=payload.retention_policy_days,
        immutable_audit_enabled=payload.immutable_audit_enabled,
    )
    session.add(vault)
    await session.commit()
    await session.refresh(vault)
    return {"id": str(vault.id), "vault_name": vault.vault_name}


@admin_router.get("/documents")
async def admin_list_regulated_documents(
    vault_id: uuid.UUID | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(require_admin_role(AdminRole.READ)),
):
    stmt = select(CommercialRAGDocument).order_by(CommercialRAGDocument.created_at.desc())
    if vault_id:
        stmt = stmt.where(CommercialRAGDocument.vault_id == vault_id)
    rows = (await session.execute(stmt)).scalars().all()
    return [
        {
            "id": str(item.id),
            "vault_id": str(item.vault_id),
            "document_hash": item.document_hash[:16],
            "document_title": item.document_title,
            "classification": item.classification,
            "ingestion_status": item.ingestion_status,
            "source_type": item.source_type,
            "signed_manifest_hash": item.signed_manifest_hash[:16] if item.signed_manifest_hash else None,
            "legal_hold": item.legal_hold,
            "metadata_json": sanitize_rag_metadata(item.metadata_json or {}),
            "created_at": item.created_at.isoformat(),
        }
        for item in rows
    ]


@admin_router.post("/documents")
async def admin_create_regulated_document(
    payload: AdminDocumentCreatePayload,
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(require_admin_role(AdminRole.WRITE)),
):
    vault = await session.get(CommercialRAGVault, payload.vault_id)
    if vault is None:
        raise HTTPException(status_code=404, detail="Vault not found")
    document = await register_regulated_document(
        session,
        vault=vault,
        title=payload.document_title,
        plaintext=payload.plaintext or payload.document_title,
        classification=payload.classification,
        source_type=payload.source_type,
        metadata_json=payload.metadata_json,
        provenance_hash=payload.provenance_hash,
        signed_manifest_hash=payload.signed_manifest_hash,
        legal_hold=payload.legal_hold,
    )
    await session.commit()
    return {"id": str(document.id), "document_hash": document.document_hash}


@admin_router.get("/retrieval-audit")
async def admin_list_retrieval_audit(
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(require_admin_role(AdminRole.READ)),
):
    rows = (await session.execute(
        select(CommercialRAGRetrievalAudit).order_by(CommercialRAGRetrievalAudit.created_at.desc()).limit(200)
    )).scalars().all()
    return [
        {
            "id": str(item.id),
            "vault_id": str(item.vault_id),
            "client_id": str(item.client_id) if item.client_id else None,
            "request_hash": item.request_hash[:16],
            "retrieval_hash": item.retrieval_hash[:16],
            "retrieved_chunk_count": item.retrieved_chunk_count,
            "policy_result": item.policy_result,
            "model_id": item.model_id,
            "immutable_hash": item.immutable_hash[:16] if item.immutable_hash else None,
            "created_at": item.created_at.isoformat(),
        }
        for item in rows
    ]


@admin_router.get("/retrieval-proofs")
async def admin_list_retrieval_proofs(
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(require_admin_role(AdminRole.READ)),
):
    rows = (await session.execute(
        select(CommercialRetrievalProof).order_by(CommercialRetrievalProof.created_at.desc()).limit(200)
    )).scalars().all()
    return [
        {
            "id": str(item.id),
            "retrieval_audit_id": str(item.retrieval_audit_id),
            "vault_id": str(item.vault_id),
            "timeline_id": str(item.timeline_id) if item.timeline_id else None,
            "proof_hash": item.proof_hash[:16],
            "verification_status": item.verification_status,
            "lineage_root_hash": item.lineage_root_hash[:16],
            "retrieval_sent_hash": item.retrieval_sent_hash[:16],
            "created_at": item.created_at.isoformat(),
        }
        for item in rows
    ]


@admin_router.get("/retrieval-proofs/{proof_id}/export")
async def admin_export_retrieval_proof(
    proof_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(require_admin_role(AdminRole.READ)),
):
    proof = await session.get(CommercialRetrievalProof, proof_id)
    if proof is None:
        raise HTTPException(status_code=404, detail="Retrieval proof not found")
    return await export_retrieval_proof(session, proof)


@admin_router.post("/retrieval-proofs/{proof_id}/verify")
async def admin_verify_retrieval_proof(
    proof_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(require_admin_role(AdminRole.WRITE)),
):
    proof = await session.get(CommercialRetrievalProof, proof_id)
    if proof is None:
        raise HTTPException(status_code=404, detail="Retrieval proof not found")
    result = await verify_retrieval_proof(session, proof)
    await session.commit()
    return result


@admin_router.post("/retrieval-proofs/{proof_id}/replay")
async def admin_replay_retrieval_proof(
    proof_id: uuid.UUID,
    payload: AdminRetrievalReplayPayload,
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(require_admin_role(AdminRole.WRITE)),
):
    proof = await session.get(CommercialRetrievalProof, proof_id)
    if proof is None:
        raise HTTPException(status_code=404, detail="Retrieval proof not found")
    replay = await replay_retrieval_proof(session, proof=proof, replay_sources=payload.replay_sources)
    await session.commit()
    return {
        "id": str(replay.id),
        "replay_status": replay.replay_status,
        "drift_status": replay.drift_status,
        "drift_score": replay.drift_score,
    }


@admin_router.get("/retrieval-proofs/{proof_id}/lineage")
async def admin_verify_lineage_consistency(
    proof_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(require_admin_role(AdminRole.READ)),
):
    proof = await session.get(CommercialRetrievalProof, proof_id)
    if proof is None:
        raise HTTPException(status_code=404, detail="Retrieval proof not found")
    return {"valid": await verify_lineage_consistency(session, proof), "lineage_root_hash": proof.lineage_root_hash}


@admin_router.get("/poison-alerts")
async def admin_list_poison_alerts(
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(require_admin_role(AdminRole.READ)),
):
    rows = (await session.execute(
        select(CommercialRAGPoisoningAlert).order_by(CommercialRAGPoisoningAlert.created_at.desc()).limit(200)
    )).scalars().all()
    return [
        {
            "id": str(item.id),
            "vault_id": str(item.vault_id),
            "alert_type": item.alert_type,
            "severity": item.severity,
            "summary": item.summary,
            "resolved": item.resolved,
            "created_at": item.created_at.isoformat(),
        }
        for item in rows
    ]


@admin_router.post("/poison-alerts/{alert_id}/resolve")
async def admin_resolve_poison_alert(
    alert_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(require_admin_role(AdminRole.WRITE)),
):
    alert = await session.get(CommercialRAGPoisoningAlert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.resolved = True
    await session.commit()
    return {"status": "resolved", "id": str(alert.id)}


@admin_router.get("/legal-holds")
async def admin_list_legal_holds(
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(require_admin_role(AdminRole.READ)),
):
    rows = (await session.execute(
        select(CommercialRAGLegalHold).order_by(CommercialRAGLegalHold.created_at.desc()).limit(200)
    )).scalars().all()
    return [
        {
            "id": str(item.id),
            "vault_id": str(item.vault_id),
            "document_id": str(item.document_id) if item.document_id else None,
            "hold_reason": item.hold_reason,
            "active": item.active,
            "created_at": item.created_at.isoformat(),
            "released_at": item.released_at.isoformat() if item.released_at else None,
        }
        for item in rows
    ]


@admin_router.post("/legal-holds")
async def admin_create_legal_hold(
    payload: AdminLegalHoldCreatePayload,
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(require_admin_role(AdminRole.WRITE)),
):
    hold = CommercialRAGLegalHold(
        vault_id=payload.vault_id,
        document_id=payload.document_id,
        hold_reason=sanitize_rag_text(payload.hold_reason, max_len=255),
        active=True,
    )
    session.add(hold)
    if payload.document_id:
        document = await session.get(CommercialRAGDocument, payload.document_id)
        if document:
            document.legal_hold = True
    await session.commit()
    return {"id": str(hold.id), "active": hold.active}


@admin_router.post("/reindex")
async def admin_reindex(
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(require_admin_role(AdminRole.WRITE)),
):
    docs = (await session.execute(
        select(RAGDocument).where(RAGDocument.status.in_(["failed", "indexed"]))
    )).scalars().all()

    from app.api.rag import RAG_QUEUE_NAME
    from app.services.runtime_dependencies import redis_client

    count = 0
    for doc in docs:
        doc.status = "uploaded"
        doc.error_message = None
        await redis_client.rpush(RAG_QUEUE_NAME, str(doc.id))
        count += 1
    await session.commit()

    return {"reindexed": count, "status": "queued"}
