from datetime import datetime
import uuid
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.rag_document import RAGDocument
from app.models.rag_usage_event import RagUsageEvent
from app.models.client_feature_block import ClientFeatureBlock
from app.services.billing import resolve_effective_plan
from app.services.quota import month_start

async def get_rag_usage_and_limits(session: AsyncSession, client: Client):
    effective_plan = resolve_effective_plan(client)
    
    # Get current doc count and storage
    docs_result = await session.execute(
        select(
            func.count(RAGDocument.id).label("doc_count"),
            func.sum(RAGDocument.file_size_bytes).label("storage_bytes")
        ).where(RAGDocument.client_id == client.id)
    )
    docs_row = docs_result.mappings().first()
    doc_count = docs_row["doc_count"] or 0
    storage_bytes = docs_row["storage_bytes"] or 0
    storage_mb = storage_bytes / (1024 * 1024)

    # Get monthly usage (queries and pages)
    from datetime import date
    start_of_month = month_start(date.today())
    
    usage_result = await session.execute(
        select(
            RagUsageEvent.event_type,
            func.sum(RagUsageEvent.quantity).label("total_quantity")
        ).where(
            RagUsageEvent.client_id == client.id,
            RagUsageEvent.created_at >= start_of_month
        ).group_by(RagUsageEvent.event_type)
    )
    
    pages_processed = 0
    queries_count = 0
    tokens_used = 0
    
    for row in usage_result.mappings():
        if row["event_type"] == "pages_processed":
            pages_processed = row["total_quantity"]
        elif row["event_type"] == "rag_query":
            queries_count = row["total_quantity"]
        elif row["event_type"] == "rag_query_tokens":
            tokens_used = row["total_quantity"]

    # Check if blocked
    block_result = await session.execute(
        select(ClientFeatureBlock).where(
            ClientFeatureBlock.client_id == client.id,
            ClientFeatureBlock.feature == "rag"
        )
    )
    block = block_result.scalar_one_or_none()
    is_blocked = block.blocked if block else False
    blocked_reason = block.reason if block else None

    return {
        "plan": effective_plan.code,
        "rag_enabled": effective_plan.rag_enabled,
        "limits": {
            "max_documents": effective_plan.rag_max_documents,
            "max_storage_mb": effective_plan.rag_max_storage_mb,
            "max_pages_per_month": effective_plan.rag_max_pages_per_month,
            "max_queries_per_month": effective_plan.rag_max_queries_per_month
        },
        "usage": {
            "client_id": str(client.id),
            "documents_count": doc_count,
            "storage_mb": round(storage_mb, 2),
            "pages_processed_month": pages_processed,
            "queries_month": queries_count,
            "tokens_month": tokens_used
        },
        "rag_blocked": is_blocked,
        "blocked_reason": blocked_reason
    }

async def check_rag_feature_blocked(session: AsyncSession, client_id: uuid.UUID):
    block_result = await session.execute(
        select(ClientFeatureBlock).where(
            ClientFeatureBlock.client_id == client_id,
            ClientFeatureBlock.feature == "rag"
        )
    )
    block = block_result.scalar_one_or_none()
    if block and block.blocked:
        return True, block.reason
    return False, None

async def record_rag_event(
    session: AsyncSession,
    client_id: uuid.UUID,
    event_type: str,
    quantity: int = 1,
    document_id: uuid.UUID | None = None,
    storage_bytes: int | None = None,
    tokens: int | None = None,
    metadata_json: dict | None = None
):
    event = RagUsageEvent(
        client_id=client_id,
        event_type=event_type,
        quantity=quantity,
        document_id=document_id,
        storage_bytes=storage_bytes,
        tokens=tokens,
        metadata_json=metadata_json
    )
    session.add(event)
    await session.flush()
