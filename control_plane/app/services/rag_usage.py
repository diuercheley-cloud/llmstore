import uuid

from app.models.core.client import Client
from app.models.core.client_feature_block import ClientFeatureBlock
from app.services.billing.core import resolve_effective_plan_for_session
from app.services.quota import month_start
from app.storage import resolve_storage_backend
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_rag_usage_and_limits(session: AsyncSession, client: Client):
    effective_plan = await resolve_effective_plan_for_session(session, client)

    backend = resolve_storage_backend(session)
    summary = await backend.document_store.summarize_rag_documents(client.id)
    doc_count = summary["documents_count"]
    storage_bytes = summary["storage_bytes"]
    storage_mb = storage_bytes / (1024 * 1024)

    from datetime import date

    start_of_month = month_start(date.today())
    usage_summary = await backend.document_store.summarize_rag_usage_events(
        client.id, since=start_of_month
    )
    pages_processed = usage_summary.get("pages_processed", 0)
    queries_count = usage_summary.get("rag_query", 0)
    tokens_used = usage_summary.get("rag_query_tokens", 0)

    # Check if blocked
    block_result = await session.execute(
        select(ClientFeatureBlock).where(
            ClientFeatureBlock.client_id == client.id, ClientFeatureBlock.feature == "rag"
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
            "max_queries_per_month": effective_plan.rag_max_queries_per_month,
        },
        "usage": {
            "client_id": str(client.id),
            "documents_count": doc_count,
            "storage_mb": round(storage_mb, 2),
            "pages_processed_month": pages_processed,
            "queries_month": queries_count,
            "tokens_month": tokens_used,
        },
        "rag_blocked": is_blocked,
        "blocked_reason": blocked_reason,
    }


async def check_rag_feature_blocked(session: AsyncSession, client_id: uuid.UUID):
    block_result = await session.execute(
        select(ClientFeatureBlock).where(
            ClientFeatureBlock.client_id == client_id, ClientFeatureBlock.feature == "rag"
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
    metadata_json: dict | None = None,
):
    backend = resolve_storage_backend(session)
    await backend.document_store.add_rag_usage_event(
        client_id=client_id,
        event_type=event_type,
        quantity=quantity,
        document_id=document_id,
        storage_bytes=storage_bytes,
        tokens=tokens,
        metadata_json=metadata_json,
    )
