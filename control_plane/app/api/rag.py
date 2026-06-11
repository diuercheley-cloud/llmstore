# Owner: platform-ops
import json
import logging
import os
import uuid

import numpy as np
from app.api.client import _chat_with_fallback
from app.api.deps import get_inference_proxy
from app.core.config import get_settings
from app.db.session import get_db_session, redis_client
from app.models.core.client import Client
from app.models.rag.rag_document import RAGDocument
from app.schemas.rag import (
    RAGFileListResponse,
    RAGFileResponse,
    RAGQueryRequest,
    RAGQueryResponse,
    RAGSource,
)
from app.storage import resolve_storage_backend
from app.services.auth import require_client
from app.services.billing.core import resolve_effective_plan_for_session
from app.services.embeddings import get_embedding_service
from app.services.model_policy import resolve_requested_model
from app.services.quota import QuotaExceeded, ensure_quota, record_usage
from app.services.rag_processor import delete_rag_document
from app.services.rag_usage import (
    check_rag_feature_blocked,
    get_rag_usage_and_limits,
    record_rag_event,
)
from app.utils.token_estimator import estimate_tokens_from_text
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/rag", tags=["rag"])
client_rag_router = APIRouter(prefix="/client/rag", tags=["client_rag"])
settings = get_settings()

RAG_QUEUE_NAME = "rag_jobs:queue"

def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))

# --- Client RAG Endpoints ---

@client_rag_router.get("/usage")
async def get_client_rag_usage(
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    if not settings.rag_enabled:
        raise HTTPException(status_code=403, detail="RAG is disabled")
    
    is_blocked, block_reason = await check_rag_feature_blocked(session, client.id)
    if is_blocked:
        raise HTTPException(status_code=403, detail=f"RAG feature blocked: {block_reason}")
    
    usage_info = await get_rag_usage_and_limits(session, client)
    if not usage_info["rag_enabled"]:
        raise HTTPException(status_code=403, detail="RAG feature is not enabled for your plan")
    
    return usage_info

@client_rag_router.post("/documents", response_model=RAGFileResponse)
async def upload_client_rag_document(
    file: UploadFile = File(...),
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    backend = resolve_storage_backend(session)
    if not settings.rag_enabled:
        raise HTTPException(status_code=403, detail="RAG is disabled")

    usage_info = await get_rag_usage_and_limits(session, client)
    if not usage_info["rag_enabled"]:
        raise HTTPException(status_code=403, detail="RAG feature is not enabled for your plan")

    is_blocked, block_reason = await check_rag_feature_blocked(session, client.id)
    if is_blocked:
        raise HTTPException(status_code=403, detail=f"RAG feature blocked: {block_reason}")

    allowed_exts = [".pdf", ".txt", ".md"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Only {', '.join(allowed_exts)} files are allowed")
    
    usage_info = await get_rag_usage_and_limits(session, client)
    limits = usage_info["limits"]
    usage = usage_info["usage"]
    
    if limits["max_documents"] is not None and usage["documents_count"] >= limits["max_documents"]:
        return JSONResponse(status_code=429, content={
            "error": "rag_limit_exceeded",
            "limit": "rag_max_documents",
            "current": usage["documents_count"],
            "max": limits["max_documents"],
            "plan": usage_info["plan"]
        })

    # Check file size and total storage
    content = await file.read()
    file_size = len(content)
    file_size_mb = file_size / (1024 * 1024)
    
    if file_size_mb > settings.rag_max_file_mb:
        raise HTTPException(status_code=413, detail=f"File too large. Max {settings.rag_max_file_mb}MB")
        
    if limits["max_storage_mb"] is not None and (float(usage["storage_mb"]) + file_size_mb) > limits["max_storage_mb"]:
        return JSONResponse(status_code=429, content={
            "error": "rag_limit_exceeded",
            "limit": "rag_max_storage_mb",
            "current": usage["storage_mb"],
            "max": limits["max_storage_mb"],
            "plan": usage_info["plan"]
        })

    # Create storage dir if not exists (organized by client_id)
    client_storage_dir = os.path.join(settings.rag_storage_dir, str(client.id))
    os.makedirs(client_storage_dir, exist_ok=True)
    
    file_id = uuid.uuid4()
    internal_filename = f"{file_id}{file_ext}"
    storage_path = os.path.join(client_storage_dir, internal_filename)
    
    with open(storage_path, "wb") as f:
        f.write(content)
        
    doc = RAGDocument(
        id=file_id,
        client_id=client.id,
        filename=internal_filename,
        original_filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        file_size_bytes=file_size,
        storage_path=storage_path,
        status="uploaded"
    )
    await backend.document_store.add_rag_document(doc)
    
    await record_rag_event(session, client.id, "document_uploaded", document_id=file_id, storage_bytes=file_size)
    
    await session.commit()
    await session.refresh(doc)
    
    # Enqueue processing
    await redis_client.rpush(RAG_QUEUE_NAME, str(doc.id))
    
    return doc

@client_rag_router.get("/documents", response_model=RAGFileListResponse)
async def list_client_rag_documents(
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    backend = resolve_storage_backend(session)
    return {"data": await backend.document_store.list_rag_documents(client.id)}

@client_rag_router.get("/documents/{doc_id}", response_model=RAGFileResponse)
async def get_client_rag_document(
    doc_id: uuid.UUID,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    backend = resolve_storage_backend(session)
    doc = await backend.document_store.get_rag_document(doc_id, client_id=client.id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@client_rag_router.delete("/documents/{doc_id}")
async def delete_client_rag_document(
    doc_id: uuid.UUID,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    backend = resolve_storage_backend(session)
    doc = await backend.document_store.get_rag_document(doc_id, client_id=client.id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    file_size = doc.file_size_bytes
    await delete_rag_document(session, doc)
    await record_rag_event(session, client.id, "document_deleted", document_id=doc_id, storage_bytes=-file_size)
    await session.commit()
    
    return {"status": "deleted"}

@client_rag_router.post("/query", response_model=RAGQueryResponse)
async def query_client_rag(
    payload: RAGQueryRequest,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
    proxy = Depends(get_inference_proxy),
):
    # Reuse existing query_rag logic or redirect
    return await query_rag(payload, client, session, proxy)

@router.get("/usage")
async def get_rag_usage(
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    if not settings.rag_enabled:
        raise HTTPException(status_code=403, detail="RAG is disabled")
    
    is_blocked, block_reason = await check_rag_feature_blocked(session, client.id)
    if is_blocked:
        raise HTTPException(status_code=403, detail=f"RAG feature blocked: {block_reason}")
    
    return await get_rag_usage_and_limits(session, client)

@router.post("/files", response_model=RAGFileResponse)
async def upload_rag_file(
    file: UploadFile = File(...),
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    backend = resolve_storage_backend(session)
    if not settings.rag_enabled:
        raise HTTPException(status_code=403, detail="RAG is disabled")

    is_blocked, block_reason = await check_rag_feature_blocked(session, client.id)
    if is_blocked:
        raise HTTPException(status_code=403, detail=f"RAG feature blocked: {block_reason}")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    usage_info = await get_rag_usage_and_limits(session, client)
    limits = usage_info["limits"]
    usage = usage_info["usage"]
    
    if limits["max_documents"] is not None and usage["documents_count"] >= limits["max_documents"]:
        return JSONResponse(status_code=429, content={
            "error": "rag_limit_exceeded",
            "limit": "rag_max_documents",
            "current": usage["documents_count"],
            "max": limits["max_documents"],
            "plan": usage_info["plan"]
        })

    # Check file size and total storage
    content = await file.read()
    file_size = len(content)
    file_size_mb = file_size / (1024 * 1024)
    
    if file_size_mb > settings.rag_max_file_mb:
        raise HTTPException(status_code=413, detail=f"File too large. Max {settings.rag_max_file_mb}MB")
        
    if limits["max_storage_mb"] is not None and (float(usage["storage_mb"]) + file_size_mb) > limits["max_storage_mb"]:
        return JSONResponse(status_code=429, content={
            "error": "rag_limit_exceeded",
            "limit": "rag_max_storage_mb",
            "current": usage["storage_mb"],
            "max": limits["max_storage_mb"],
            "plan": usage_info["plan"]
        })

    # Create storage dir if not exists
    os.makedirs(settings.rag_storage_dir, exist_ok=True)
    
    file_id = uuid.uuid4()
    internal_filename = f"{client.id}_{file_id}.pdf"
    storage_path = os.path.join(settings.rag_storage_dir, internal_filename)
    
    with open(storage_path, "wb") as f:
        f.write(content)
        
    doc = RAGDocument(
        id=file_id,
        client_id=client.id,
        filename=internal_filename,
        original_filename=file.filename,
        content_type=file.content_type or "application/pdf",
        file_size_bytes=file_size,
        storage_path=storage_path,
        status="uploaded"
    )
    await backend.document_store.add_rag_document(doc)
    
    await record_rag_event(session, client.id, "document_uploaded", document_id=file_id, storage_bytes=file_size)
    
    await session.commit()
    await session.refresh(doc)
    
    # Enqueue processing
    await redis_client.rpush(RAG_QUEUE_NAME, str(doc.id))
    
    return doc

@router.get("/files", response_model=RAGFileListResponse)
async def list_rag_files(
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    backend = resolve_storage_backend(session)
    return {"data": await backend.document_store.list_rag_documents(client.id)}

@router.get("/files/{file_id}", response_model=RAGFileResponse)
async def get_rag_file(
    file_id: uuid.UUID,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    backend = resolve_storage_backend(session)
    doc = await backend.document_store.get_rag_document(file_id, client_id=client.id)
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")
    return doc

@router.delete("/files/{file_id}")
async def delete_rag_file(
    file_id: uuid.UUID,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    backend = resolve_storage_backend(session)
    doc = await backend.document_store.get_rag_document(file_id, client_id=client.id)
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_size = doc.file_size_bytes
    await delete_rag_document(session, doc)
    await record_rag_event(session, client.id, "document_deleted", document_id=file_id, storage_bytes=-file_size)
    await session.commit()
    
    return {"status": "deleted"}

@router.post("/files/{file_id}/reprocess", response_model=RAGFileResponse)
async def reprocess_rag_file(
    file_id: uuid.UUID,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    backend = resolve_storage_backend(session)
    doc = await backend.document_store.get_rag_document(file_id, client_id=client.id)
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")
    
    doc.status = "uploaded"
    doc.error_message = None
    await session.commit()
    await redis_client.rpush(RAG_QUEUE_NAME, str(doc.id))
    return doc

@router.post("/query", response_model=RAGQueryResponse)
async def query_rag(
    payload: RAGQueryRequest,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
    proxy = Depends(get_inference_proxy),
):
    backend = resolve_storage_backend(session)
    if not settings.rag_enabled:
        raise HTTPException(status_code=403, detail="RAG is disabled")

    # Delegate to enterprise RAG if plan indicates enterprise or enterprise fields are present
    effective_plan = await resolve_effective_plan_for_session(session, client)
    has_enterprise_fields = (
        payload.collection_ids is not None or
        payload.document_ids is not None or
        payload.abac_attributes is not None or
        payload.rerank or
        (payload.score_threshold and payload.score_threshold > 0.0)
    )
    if has_enterprise_fields or effective_plan.code in ("enterprise", "scale") or getattr(effective_plan, "rag_max_documents", 0) > 5:
        from app.api.rag_enterprise import query_enterprise_rag
        from app.services.rag_enterprise.schemas import EnterpriseQueryRequest
        from starlette.responses import JSONResponse

        ent_payload = EnterpriseQueryRequest(
            question=payload.question,
            collection_ids=payload.collection_ids,
            document_ids=payload.document_ids or payload.file_ids,
            model=payload.model,
            top_k=payload.top_k,
            score_threshold=payload.score_threshold or 0.0,
            max_tokens=payload.max_tokens,
            temperature=payload.temperature,
            rerank=payload.rerank or False,
            user_identity=payload.user_identity,
            abac_attributes=payload.abac_attributes,
        )
        ent_res = await query_enterprise_rag(ent_payload, client, session, proxy)
        if isinstance(ent_res, JSONResponse):
            return ent_res

        # Map response to RAGQueryResponse schema structure
        if hasattr(ent_res, "dict"):
            res_dict = ent_res.dict()
        elif isinstance(ent_res, dict):
            res_dict = ent_res
        else:
            return ent_res

        mapped_sources = []
        for s in res_dict.get("sources", []):
            mapped_sources.append({
                "file_id": s.get("document_id") or s.get("file_id"),
                "filename": s.get("filename"),
                "page": s.get("page"),
                "chunk_index": s.get("chunk_index"),
                "text": s.get("text"),
                "score": s.get("score"),
            })
        return {
            "answer": res_dict.get("answer"),
            "sources": mapped_sources,
            "usage": res_dict.get("usage"),
        }

    is_blocked, block_reason = await check_rag_feature_blocked(session, client.id)
    if is_blocked:
        raise HTTPException(status_code=403, detail=f"RAG feature blocked: {block_reason}")

    usage_info = await get_rag_usage_and_limits(session, client)
    if not usage_info["rag_enabled"]:
        raise HTTPException(status_code=403, detail="RAG feature is not enabled for your plan")

    limits = usage_info["limits"]
    usage = usage_info["usage"]

    if limits["max_queries_per_month"] is not None and usage["queries_month"] >= limits["max_queries_per_month"]:
        return JSONResponse(status_code=429, content={
            "error": "rag_limit_exceeded",
            "limit": "rag_max_queries_per_month",
            "current": usage["queries_month"],
            "max": limits["max_queries_per_month"],
            "plan": usage_info["plan"]
        })

    # 1. Generate embedding for the question
    embedding_service = get_embedding_service()
    query_embedding = await embedding_service.embed_text(payload.question)
    
    # 2. Search for similar chunks
    store = backend.vector_store
    filters = {"client_id": client.id}
    if payload.file_ids:
        # For simplicity, we assume single file_id or handle it in provider
        filters["document_id"] = payload.file_ids[0] if payload.file_ids else None

    hits = await store.search(
        collection_name="rag_chunks",
        vector=query_embedding,
        limit=payload.top_k,
        filters=filters
    )
    
    if not hits:
        return {
            "answer": "Não encontrei nenhum documento para consultar.",
            "sources": [],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        }

    # 3. Build prompt
    context_str = ""
    sources = []
    for hit in hits:
        chunk_id = uuid.UUID(hit["id"])
    chunk_ids = [uuid.UUID(hit["id"]) for hit in hits]
    chunks = await backend.document_store.get_rag_chunks(chunk_ids)
    chunks_by_id = {chunk.id: chunk for chunk in chunks}
    documents = await backend.document_store.get_rag_documents_by_ids([chunk.document_id for chunk in chunks])

    for hit in hits:
        chunk_id = uuid.UUID(hit["id"])
        chunk = chunks_by_id.get(chunk_id)
        if not chunk:
            continue

        doc = documents.get(chunk.document_id)
        if doc is None:
            continue
        context_str += f"[fonte: {doc.original_filename}, página {chunk.page_number}]\n{chunk.content}\n\n"
        sources.append(RAGSource(
            file_id=chunk.document_id,
            filename=doc.original_filename,
            page=chunk.page_number,
            chunk_index=chunk.chunk_index,
            text=chunk.content,
            score=float(hit["score"])
        ))
    
    prompt = f"""Você é um assistente que responde usando apenas o contexto fornecido abaixo.
Se a resposta não estiver no contexto, diga que não encontrou informação suficiente nos documentos.
Cite as fontes por nome do arquivo e página.

Contexto:
{context_str}

Pergunta:
{payload.question}

Resposta:"""
    
    # 4. Quota check
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
            session, 
            client.id, 
            effective_plan.daily_token_quota, 
            effective_plan.weekly_token_quota, 
            effective_plan.monthly_token_quota, 
            incoming_tokens
        )
    except QuotaExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    
    # 5. Call inference
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
    
    # 6. Record usage
    await record_usage(
        session, 
        client.id, 
        prompt_tokens, 
        completion_tokens,
        token_count_method=token_count_method,
        tokens_estimated=tokens_estimated
    )
    
    # Record RAG specific usage
    await record_rag_event(session, client.id, "rag_query", quantity=1)
    await record_rag_event(session, client.id, "rag_query_tokens", quantity=prompt_tokens + completion_tokens)
    
    await session.commit()
    
    return {
        "answer": answer,
        "sources": sources,
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }
    }
