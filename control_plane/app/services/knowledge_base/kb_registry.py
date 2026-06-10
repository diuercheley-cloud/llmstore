# Owner: agent-platform
import logging
import uuid
from typing import Dict, List, Optional

from app.models.rag.knowledge_base import KBDocument, KBDocumentVersion, KnowledgeBase
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class KBRegistry:
    """
    Manages the lifecycle of Knowledge Bases and their documents.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_kb(self, tenant_id: str, name: str, description: str = None, provider_config: Dict = None) -> KnowledgeBase:
        kb = KnowledgeBase(
            tenant_id=tenant_id,
            name=name,
            description=description,
            provider_config=provider_config or {}
        )
        self.db.add(kb)
        await self.db.flush()
        return kb

    async def get_kb(self, kb_id: uuid.UUID) -> Optional[KnowledgeBase]:
        stmt = select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_kbs(self, tenant_id: str) -> List[KnowledgeBase]:
        stmt = select(KnowledgeBase).where(KnowledgeBase.tenant_id == tenant_id)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def register_document(self, kb_id: uuid.UUID, name: str, source_type: str, source_url: str = None, metadata: Dict = None) -> KBDocument:
        doc = KBDocument(
            kb_id=kb_id,
            name=name,
            source_type=source_type,
            source_url=source_url,
            metadata_json=metadata or {}
        )
        self.db.add(doc)
        await self.db.flush()
        return doc

    async def create_document_version(self, doc_id: uuid.UUID, version_tag: str, content_hash: str, storage_path: str = None) -> KBDocumentVersion:
        version = KBDocumentVersion(
            document_id=doc_id,
            version_tag=version_tag,
            content_hash=content_hash,
            storage_path=storage_path,
            status="pending"
        )
        self.db.add(version)
        await self.db.flush()
        return version

    async def get_document_versions(self, doc_id: uuid.UUID) -> List[KBDocumentVersion]:
        stmt = select(KBDocumentVersion).where(KBDocumentVersion.document_id == doc_id).order_by(KBDocumentVersion.created_at.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
