import json
import logging
import os
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.client import Client
from app.models.rag_document import RAGDocument
from app.models.rag_document_chunk import RAGDocumentChunk
from app.models.rag_collection import RAGCollection
from app.services.auth import require_client, require_admin_role
from app.services.rag_enterprise.schemas import (
    CollectionCreate, CollectionResponse, CollectionListResponse,
    EnterpriseDocumentResponse, EnterpriseDocumentListResponse,
    EnterpriseQueryRequest, EnterpriseQueryResponse,
    EnterpriseSource, AdminOverview,
)
from app.services.rag_enterprise.ingestion import ingest_document, delete_enterprise_document
from app.services.rag_enterprise.retrieval import execute_enterprise_query, build_rag_context
from app.services.rag_enterprise.policies import (
    resolve_enterprise_rag_policy,
    check_quota_documents,
    check_quota_storage,
    check_file_type_allowed,
    is_cloud_embedding_allowed,
    ALLOWED_FILE_TYPES_DEFAULT,
)
from app.services.rag_enterprise.parsers import get_parsers_summary, get_parser_status, SUPPORTED_EXTENSIONS
from app.services.rag_usage import get_rag_usage_and_limits, check_rag_feature_blocked, record_rag_event
from app.services.model_policy import resolve_requested_model
from app.services.quota import ensure_quota, record_usage, QuotaExceeded
from app.services.billing import resolve_effective_plan
from app.api.deps import get_inference_proxy
from app.api.client import _chat_with_fallback
from app.utils.token_estimator import estimate_prompt_tokens, estimate_tokens_from_text

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/v1/rag", tags=["rag_enterprise"])
admin_router = APIRouter(prefix="/admin/rag", tags=["admin_rag"])


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

@router.post("/query", response_model=EnterpriseQueryResponse)
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

    sources, scores = await execute_enterprise_query(
        session=session,
        client_id=client.id,
        question=payload.question,
        top_k=payload.top_k,
        score_threshold=payload.score_threshold,
        document_ids=payload.document_ids,
        collection_ids=payload.collection_ids,
        cloud_allowed=cloud_allowed,
    )

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
    effective_plan = resolve_effective_plan(client)

    prompt_tokens = estimate_prompt_tokens(prompt=prompt)
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

    await record_usage(session, client.id, prompt_tokens, completion_tokens)
    await record_rag_event(session, client.id, "rag_query", quantity=1)
    await record_rag_event(session, client.id, "rag_query_tokens", quantity=prompt_tokens + completion_tokens)

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
    admin=Depends(require_admin_role("READ")),
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
    admin=Depends(require_admin_role("READ")),
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


@admin_router.post("/reindex")
async def admin_reindex(
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(require_admin_role("WRITE")),
):
    docs = (await session.execute(
        select(RAGDocument).where(RAGDocument.status.in_(["failed", "indexed"]))
    )).scalars().all()

    from app.api.rag import RAG_QUEUE_NAME
    from app.db.session import redis_client

    count = 0
    for doc in docs:
        doc.status = "uploaded"
        doc.error_message = None
        await redis_client.rpush(RAG_QUEUE_NAME, str(doc.id))
        count += 1
    await session.commit()

    return {"reindexed": count, "status": "queued"}
