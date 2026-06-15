import json
import logging
import uuid
from typing import Any

from app.models.agents.agents import AgentMemoryIndex
from app.models.rag.rag_document_chunk import RAGDocumentChunk
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .base import VectorStoreBase

logger = logging.getLogger(__name__)


class PGVectorStore(VectorStoreBase):
    """
    PostgreSQL pgvector implementation of the VectorStore interface.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    def _supports_pgvector(self) -> bool:
        bind = self.session.bind
        if bind is None:
            return False
        return bind.dialect.name == "postgresql"

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def _decode_embedding(raw: Any) -> list[float]:
        if raw is None:
            return []
        if isinstance(raw, list):
            return [float(v) for v in raw]
        if isinstance(raw, str):
            try:
                decoded = json.loads(raw)
                if isinstance(decoded, list):
                    return [float(v) for v in decoded]
            except json.JSONDecodeError:
                return []
        return []

    @staticmethod
    def _as_uuid(value: Any) -> uuid.UUID:
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))

    async def upsert(
        self,
        collection_name: str,
        id: str,
        vector: list[float],
        metadata: dict[str, Any] | None = None,
        namespace: str | None = None,
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

        metadata = metadata or {}
        vector_str = json.dumps(vector)
        meta_str = json.dumps(metadata)
        client_id = metadata.get("client_id") or metadata.get("tenant_id")
        doc_id = metadata.get("document_id") or uuid.uuid4()
        agent_id = metadata.get("agent_id") or uuid.uuid4()
        content = metadata.get("content", "")

        if not self._supports_pgvector():
            if table_name == "agent_memory_indexes":
                stmt = select(AgentMemoryIndex).where(
                    AgentMemoryIndex.memory_item_id == uuid.UUID(id)
                )
                result = await self.session.execute(stmt)
                row = result.scalar_one_or_none()
                if row is None:
                    row = AgentMemoryIndex(
                        tenant_id=str(client_id),
                        agent_id=self._as_uuid(agent_id),
                        memory_item_id=uuid.UUID(id),
                        vector_id=f"vec_{id}",
                    )
                    self.session.add(row)
                row.embedding = vector_str
                row.index_status = "completed"
                await self.session.flush()
                return

            chunk = await self.session.get(RAGDocumentChunk, uuid.UUID(id))
            if chunk is None:
                chunk = RAGDocumentChunk(
                    id=uuid.UUID(id),
                    document_id=self._as_uuid(doc_id),
                    client_id=self._as_uuid(client_id),
                    chunk_index=0,
                    page_number=0,
                    content=content,
                    token_count=0,
                    embedding=vector,
                    metadata_json=metadata or {},
                )
                self.session.add(chunk)
            else:
                chunk.embedding = vector
                chunk.metadata_json = metadata or {}
                chunk.content = content
            await self.session.flush()
            return

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

        try:
            await self.session.execute(
                sql,
                {
                    "id": id,
                    "uuid": uuid.uuid4(),
                    "content": content,
                    "embedding": vector_str,
                    "metadata": meta_str,
                    "client_id": client_id,
                    "tenant_id": client_id,
                    "doc_id": doc_id,
                    "agent_id": agent_id,
                },
            )
            await self.session.flush()
        except Exception as e:
            logger.error(f"PGVector upsert failed on table {table_name}: {e}")
            raise

    async def search(
        self,
        collection_name: str,
        vector: list[float],
        limit: int = 5,
        filters: dict[str, Any] | None = None,
        namespace: str | None = None,
    ) -> list[dict[str, Any]]:
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

        if not self._supports_pgvector():
            try:
                if table_name == "agent_memory_indexes":
                    stmt = select(AgentMemoryIndex)
                    result = await self.session.execute(stmt)
                    rows = result.scalars().all()
                    hits = []
                    for row in rows:
                        if "tenant_id" in params and row.tenant_id != str(params["tenant_id"]):
                            continue
                        if "agent_id" in params and str(row.agent_id) != str(params["agent_id"]):
                            continue
                        embedding = self._decode_embedding(row.embedding)
                        score = self._cosine_similarity(vector, embedding)
                        hits.append({"id": str(row.memory_item_id), "score": score})
                else:
                    stmt = select(RAGDocumentChunk)
                    result = await self.session.execute(stmt)
                    rows = result.scalars().all()
                    hits = []
                    for row in rows:
                        if "tenant_id" in params and str(row.client_id) != str(params["tenant_id"]):
                            continue
                        if "doc_id" in params and str(row.document_id) != str(params["doc_id"]):
                            continue
                        embedding = self._decode_embedding(row.embedding)
                        score = self._cosine_similarity(vector, embedding)
                        hits.append({"id": str(row.id), "score": score})
                hits.sort(key=lambda item: item["score"], reverse=True)
                return hits[:limit]
            except Exception as e:
                logger.error(f"Portable vector search failed on table {table_name}: {e}")
                return []

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
                hits.append({"id": str(row[0]), "score": float(row[1])})
            return hits
        except Exception as e:
            logger.error(f"PGVector search failed on table {table_name}: {e}")
            return []

    async def delete(
        self,
        collection_name: str,
        ids: list[str],
        namespace: str | None = None,
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
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not self._supports_pgvector():
            logger.info(
                "Skipping pgvector collection_create for '%s' because the active dialect is %s",
                collection_name,
                self.session.bind.dialect.name if self.session.bind is not None else "unknown",
            )
            return
        safe_name = collection_name.replace(" ", "_").replace("-", "_").lower()
        table_name = f"vec_{safe_name}"

        sql = text(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                embedding vector({dimension}),
                content TEXT,
                metadata JSONB DEFAULT '{{}}',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await self.session.execute(sql)

        collection_sql = text("""
            INSERT INTO rag_collections (name, table_name, dimension, metadata, created_at)
            VALUES (:name, :table_name, :dimension, :metadata, NOW())
            ON CONFLICT (name) DO UPDATE SET
                table_name = EXCLUDED.table_name,
                dimension = EXCLUDED.dimension,
                metadata = EXCLUDED.metadata
        """)
        await self.session.execute(
            collection_sql,
            {
                "name": collection_name,
                "table_name": table_name,
                "dimension": dimension,
                "metadata": json.dumps(metadata or {}),
            },
        )
        await self.session.flush()
        logger.info(
            f"Created collection '{collection_name}' (table: {table_name}, dimension: {dimension})"
        )

    async def collection_delete(
        self,
        collection_name: str,
    ) -> None:
        if not self._supports_pgvector():
            logger.info(
                "Skipping pgvector collection_delete for '%s' on non-PostgreSQL backend",
                collection_name,
            )
            return
        safe_name = collection_name.replace(" ", "_").replace("-", "_").lower()
        table_name = f"vec_{safe_name}"

        sql = text(f"DROP TABLE IF EXISTS {table_name} CASCADE")
        await self.session.execute(sql)

        collection_sql = text("DELETE FROM rag_collections WHERE name = :name")
        await self.session.execute(collection_sql, {"name": collection_name})
        await self.session.flush()
        logger.info(f"Deleted collection '{collection_name}'")

    async def healthcheck(self) -> dict[str, Any]:
        if not self._supports_pgvector():
            return {
                "status": "degraded",
                "provider": "pgvector",
                "portable_fallback": True,
                "reason": "non_postgresql_backend",
            }
        try:
            res = await self.session.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            )
            has_extension = res.scalar() is not None
            return {
                "status": "healthy" if has_extension else "degraded",
                "provider": "pgvector",
                "extension_installed": has_extension,
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e), "provider": "pgvector"}
