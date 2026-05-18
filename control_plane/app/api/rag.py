import os
import uuid
import logging
import json
from typing import List, Optional

import numpy as np
import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from app.core.config import get_settings
from app.db.session import get_db_session, redis_client
from app.models.client import Client
from app.models.rag_document import RAGDocument
from app.models.rag_document_chunk import RAGDocumentChunk
from app.schemas.rag import (
    RAGFileResponse, 
    RAGFileListResponse, 
    RAGQueryRequest, 
    RAGQueryResponse,
    RAGSource,
    RAGUsage
)
from app.services.auth import require_client
from app.services.rag_processor import delete_rag_document
from app.services.embeddings import get_embedding_service
from app.services.model_policy import resolve_requested_model
from app.services.quota import ensure_quota, record_usage, QuotaExceeded
from app.services.billing import resolve_effective_plan
from app.api.deps import get_inference_proxy
from app.utils.token_estimator import estimate_prompt_tokens, estimate_tokens_from_text
from app.api.client import _chat_with_fallback

from app.services.rag_usage import get_rag_usage_and_limits, check_rag_feature_blocked, record_rag_event

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
    session.add(doc)
    
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
    result = await session.execute(
        select(RAGDocument).where(RAGDocument.client_id == client.id).order_by(RAGDocument.created_at.desc())
    )
    return {"data": result.scalars().all()}

@client_rag_router.get("/documents/{doc_id}", response_model=RAGFileResponse)
async def get_client_rag_document(
    doc_id: uuid.UUID,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    doc = (await session.execute(
        select(RAGDocument).where(RAGDocument.id == doc_id, RAGDocument.client_id == client.id)
    )).scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@client_rag_router.delete("/documents/{doc_id}")
async def delete_client_rag_document(
    doc_id: uuid.UUID,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    doc = (await session.execute(
        select(RAGDocument).where(RAGDocument.id == doc_id, RAGDocument.client_id == client.id)
    )).scalar_one_or_none()
    
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
    a = np.array(a)
    b = np.array(b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))

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
    session.add(doc)
    
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
    result = await session.execute(
        select(RAGDocument).where(RAGDocument.client_id == client.id).order_by(RAGDocument.created_at.desc())
    )
    return {"data": result.scalars().all()}

@router.get("/files/{file_id}", response_model=RAGFileResponse)
async def get_rag_file(
    file_id: uuid.UUID,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    doc = (await session.execute(
        select(RAGDocument).where(RAGDocument.id == file_id, RAGDocument.client_id == client.id)
    )).scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")
    return doc

@router.delete("/files/{file_id}")
async def delete_rag_file(
    file_id: uuid.UUID,
    client: Client = Depends(require_client),
    session: AsyncSession = Depends(get_db_session),
):
    doc = (await session.execute(
        select(RAGDocument).where(RAGDocument.id == file_id, RAGDocument.client_id == client.id)
    )).scalar_one_or_none()
    
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
    doc = (await session.execute(
        select(RAGDocument).where(RAGDocument.id == file_id, RAGDocument.client_id == client.id)
    )).scalar_one_or_none()
    
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
    if not settings.rag_enabled:
        raise HTTPException(status_code=403, detail="RAG is disabled")

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
    stmt = select(RAGDocumentChunk).where(RAGDocumentChunk.client_id == client.id)
    if payload.file_ids:
        stmt = stmt.where(RAGDocumentChunk.document_id.in_(payload.file_ids))
    
    chunks = (await session.execute(stmt)).scalars().all()
    
    if not chunks:
        return {
            "answer": "Não encontrei nenhum documento para consultar.",
            "sources": [],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        }

    scored_chunks = []
    for chunk in chunks:
        score = cosine_similarity(query_embedding, chunk.embedding)
        scored_chunks.append((score, chunk))
    
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    top_chunks = scored_chunks[:payload.top_k]
    
    # 3. Build prompt
    context_str = ""
    sources = []
    for score, chunk in top_chunks:
        doc = (await session.execute(select(RAGDocument).where(RAGDocument.id == chunk.document_id))).scalar_one()
        context_str += f"[fonte: {doc.original_filename}, página {chunk.page_number}]\n{chunk.content}\n\n"
        sources.append(RAGSource(
            file_id=chunk.document_id,
            filename=doc.original_filename,
            page=chunk.page_number,
            chunk_index=chunk.chunk_index,
            text=chunk.content,
            score=float(score)
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
    effective_plan = resolve_effective_plan(client)
    
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
