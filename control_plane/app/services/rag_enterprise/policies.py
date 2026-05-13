import uuid
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.rag_document import RAGDocument
from app.models.rag_usage_event import RagUsageEvent
from app.models.client_feature_block import ClientFeatureBlock
from app.services.billing import resolve_effective_plan
from app.services.quota import month_start

logger = logging.getLogger(__name__)

ALLOWED_FILE_TYPES_DEFAULT = [".txt", ".md", ".pdf", ".docx", ".xlsx", ".csv"]


@dataclass
class EnterpriseRagPolicy:
    rag_enabled: bool = True
    max_documents: Optional[int] = None
    max_storage_mb: Optional[int] = None
    max_pages_per_month: Optional[int] = None
    allowed_file_types: List[str] = None
    cloud_embeddings_allowed: bool = False
    retention_days: Optional[int] = None

    def __post_init__(self):
        if self.allowed_file_types is None:
            self.allowed_file_types = ALLOWED_FILE_TYPES_DEFAULT.copy()


async def resolve_enterprise_rag_policy(
    session: AsyncSession,
    client: Client,
) -> EnterpriseRagPolicy:
    effective_plan = resolve_effective_plan(client)

    block_result = await session.execute(
        select(ClientFeatureBlock).where(
            ClientFeatureBlock.client_id == client.id,
            ClientFeatureBlock.feature == "rag"
        )
    )
    block = block_result.scalar_one_or_none()
    is_blocked = block.blocked if block else False

    if is_blocked:
        return EnterpriseRagPolicy(rag_enabled=False)

    policy = EnterpriseRagPolicy(
        rag_enabled=effective_plan.rag_enabled,
        max_documents=effective_plan.rag_max_documents,
        max_storage_mb=effective_plan.rag_max_storage_mb,
        max_pages_per_month=effective_plan.rag_max_pages_per_month,
        allowed_file_types=ALLOWED_FILE_TYPES_DEFAULT.copy(),
        cloud_embeddings_allowed=False,
        retention_days=None,
    )

    return policy


async def check_quota_documents(
    session: AsyncSession,
    client_id: uuid.UUID,
    policy: EnterpriseRagPolicy,
) -> tuple[bool, Optional[str]]:
    if policy.max_documents is None:
        return True, None

    result = await session.execute(
        select(func.count(RAGDocument.id)).where(RAGDocument.client_id == client_id)
    )
    current_count = result.scalar() or 0

    if current_count >= policy.max_documents:
        return False, f"Maximum document limit ({policy.max_documents}) reached"

    return True, None


async def check_quota_storage(
    session: AsyncSession,
    client_id: uuid.UUID,
    policy: EnterpriseRagPolicy,
    additional_bytes: int = 0,
) -> tuple[bool, Optional[str]]:
    if policy.max_storage_mb is None:
        return True, None

    result = await session.execute(
        select(func.sum(RAGDocument.file_size_bytes)).where(RAGDocument.client_id == client_id)
    )
    current_bytes = result.scalar() or 0
    current_mb = (current_bytes + additional_bytes) / (1024 * 1024)

    if current_mb > policy.max_storage_mb:
        return False, f"Storage limit ({policy.max_storage_mb}MB) exceeded"

    return True, None


async def check_quota_pages(
    session: AsyncSession,
    client_id: uuid.UUID,
    policy: EnterpriseRagPolicy,
    additional_pages: int = 0,
) -> tuple[bool, Optional[str]]:
    if policy.max_pages_per_month is None:
        return True, None

    start_of_month = month_start(datetime.now().date())

    result = await session.execute(
        select(func.sum(RagUsageEvent.quantity)).where(
            RagUsageEvent.client_id == client_id,
            RagUsageEvent.event_type == "pages_processed",
            RagUsageEvent.created_at >= start_of_month,
        )
    )
    current_pages = result.scalar() or 0

    if (current_pages + additional_pages) > policy.max_pages_per_month:
        return False, f"Monthly page limit ({policy.max_pages_per_month}) exceeded"

    return True, None


async def check_file_type_allowed(
    filename: str,
    policy: EnterpriseRagPolicy,
) -> tuple[bool, Optional[str]]:
    import os
    ext = os.path.splitext(filename)[1].lower()
    if ext not in policy.allowed_file_types:
        return False, f"File type '{ext}' is not allowed. Allowed: {', '.join(policy.allowed_file_types)}"
    return True, None


async def is_cloud_embedding_allowed(
    client: Client,
    policy: EnterpriseRagPolicy,
) -> bool:
    if not policy.cloud_embeddings_allowed:
        return False
    return True
