import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .base import VectorStoreBase

logger = logging.getLogger(__name__)

class PGVectorStore(VectorStoreBase):
    """
    PostgreSQL pgvector implementation of the VectorStore interface.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(
        self,
        collection_name: str,
        id: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None,
    ) -> None:
        # Map collection_name to table_name
        if collection_name == "agent_memory":
            table_name = "agent_memory_indexes"
            id_col = "memory_item_id"
            vector_col = "embedding_vector"
        else:
            table_name = "rag_document_chunks"
            id_col = "id"
            vector_col = "embedding"
        
        vector_str = json.dumps(vector)
        meta_str = json.dumps(metadata or {})
        
        # We handle both cases with a single logic if possible
        if table_name == "agent_memory_indexes":
            sql = text(f"""
                INSERT INTO {table_name} (id, {id_col}, embedding, {vector_col}, tenant_id, agent_id, index_status, created_at, updated_at)
                VALUES (:uuid, :id, :metadata, CAST(:embedding AS vector), :tenant_id, :agent_id, 'completed', NOW(), NOW())
                ON CONFLICT ({id_col}) DO UPDATE SET
                    {vector_col} = CAST(:embedding AS vector),
                    embedding = :metadata,
                    updated_at = NOW()
            """)
        else:
            sql = text(f"""
                INSERT INTO {table_name} (id, content, embedding, metadata_json, client_id, document_id, chunk_index, page_number, token_count, created_at)
                VALUES (:id, :content, CAST(:embedding AS vector), :metadata, :client_id, :doc_id, 0, 0, 0, NOW())
                ON CONFLICT (id) DO UPDATE SET
                    embedding = CAST(:embedding AS vector),
                    metadata_json = :metadata,
                    content = :content
            """)
        
        client_id = metadata.get("client_id") or metadata.get("tenant_id")
        doc_id = metadata.get("document_id") or uuid.uuid4()
        agent_id = metadata.get("agent_id") or uuid.uuid4()
        content = metadata.get("content", "")

        try:
            await self.session.execute(sql, {
                "id": id,
                "uuid": uuid.uuid4(),
                "content": content,
                "embedding": vector_str,
                "metadata": meta_str,
                "client_id": client_id,
                "tenant_id": client_id,
                "doc_id": doc_id,
                "agent_id": agent_id
            })
            await self.session.flush()
        except Exception as e:
            logger.error(f"PGVector upsert failed on table {table_name}: {e}")
            raise

    async def search(
        self,
        collection_name: str,
        vector: List[float],
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if collection_name == "agent_memory":
            table_name = "agent_memory_indexes"
            id_col = "memory_item_id"
            vector_col = "embedding_vector"
            tenant_col = "tenant_id"
        else:
            table_name = "rag_document_chunks"
            id_col = "id"
            vector_col = "embedding"
            tenant_col = "client_id"

        vector_str = json.dumps(vector)
        filter_sql = ""
        params = {"embedding": vector_str, "limit": limit}
        
        if filters:
            if "client_id" in filters or "tenant_id" in filters:
                val = filters.get("client_id") or filters.get("tenant_id")
                filter_sql += f" AND {tenant_col} = :tenant_id"
                params["tenant_id"] = val
            if "document_id" in filters:
                filter_sql += " AND document_id = :doc_id"
                params["doc_id"] = filters["document_id"]
            if "agent_id" in filters:
                filter_sql += " AND agent_id = :agent_id"
                params["agent_id"] = filters["agent_id"]

        sql = text(f"""
            SELECT {id_col}, 
                   (1 - ({vector_col} <=> CAST(:embedding AS vector))) as score
            FROM {table_name}
            WHERE 1=1 {filter_sql}
            ORDER BY score DESC
            LIMIT :limit
        """)
        
        try:
            result = await self.session.execute(sql, params)
            hits = []
            for row in result:
                hits.append({
                    "id": str(row[0]),
                    "score": float(row[1])
                })
            return hits
        except Exception as e:
            logger.error(f"PGVector search failed on table {table_name}: {e}")
            return []

    async def delete(
        self,
        collection_name: str,
        ids: List[str],
        namespace: Optional[str] = None,
    ) -> None:
        if collection_name == "agent_memory":
            table_name = "agent_memory_indexes"
            id_col = "memory_item_id"
        else:
            table_name = "rag_document_chunks"
            id_col = "id"
            
        sql = text(f"DELETE FROM {table_name} WHERE {id_col} IN :ids")
        await self.session.execute(sql, {"ids": tuple(ids)})
        await self.session.flush()

    async def collection_create(
        self,
        collection_name: str,
        dimension: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        # In Postgres, we could create a new table or just record the collection existence
        # For this implementation, we assume the table is shared.
        pass

    async def collection_delete(
        self,
        collection_name: str,
    ) -> None:
        # In a shared table approach, we would delete all rows for this collection
        pass

    async def healthcheck(self) -> Dict[str, Any]:
        try:
            res = await self.session.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
            has_extension = res.scalar() is not None
            return {
                "status": "healthy" if has_extension else "degraded",
                "provider": "pgvector",
                "extension_installed": has_extension
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e), "provider": "pgvector"}
