"""
Graph RAG + Agentic RAG service.
Combines knowledge graph traversal with vector retrieval for enriched context,
and provides agentic retrieval loops that iteratively refine searches.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List

from app.core.config import get_settings
from app.models.rag.rag_document_chunk import RAGDocumentChunk as RAGChunk
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class GraphRAGContext:
    entities: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    chunks: List[Dict[str, Any]] = field(default_factory=list)
    query: str = ""
    expanded_queries: List[str] = field(default_factory=list)


@dataclass
class AgenticRAGResult:
    answer: str = ""
    sources: List[Dict[str, Any]] = field(default_factory=list)
    iterations: int = 0
    confidence: float = 0.0
    reasoning: List[str] = field(default_factory=list)


class KnowledgeGraphRAGService:
    """
    Graph-enhanced RAG: traverses the knowledge graph to find connected entities,
    then uses those to enrich vector search queries.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def graph_enhanced_retrieval(self, query: str, tenant_id: str,
                                       max_entities: int = 10, max_chunks: int = 20) -> GraphRAGContext:
        """
        Performs graph-enhanced retrieval:
        1. Extract entities from query (via LLM or pattern matching)
        2. Find connected entities in the knowledge graph
        3. Use entity context to build expanded queries
        4. Retrieve chunks using both original and expanded queries
        """
        ctx = GraphRAGContext(query=query)

        entities = await self._extract_entities(query)
        ctx.entities = entities[:max_entities]

        if entities:
            related = await self._find_related_entities([e["name"] for e in entities], tenant_id)
            ctx.relationships = related

            expanded = await self._build_expanded_queries(query, entities, related)
            ctx.expanded_queries = expanded

            all_queries = [query] + expanded
            seen_hashes = set()
            for q in all_queries:
                chunks = await self._vector_search(q, tenant_id, max_chunks // len(all_queries))
                for c in chunks:
                    h = c.get("content_hash", "")
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        ctx.chunks.append(c)

        if not ctx.chunks:
            ctx.chunks = await self._vector_search(query, tenant_id, max_chunks)

        return ctx

    async def _extract_entities(self, query: str) -> List[Dict[str, str]]:
        nouns = [w for w in query.split() if w[0].isupper() and len(w) > 2] if query else []
        entities = [{"name": n, "type": "extracted"} for n in nouns]
        if not entities and query:
            entities.append({"name": query.split()[0] if len(query.split()) > 0 else query, "type": "inferred"})
        return entities

    async def _find_related_entities(self, entity_names: List[str], tenant_id: str) -> List[Dict]:
        if not entity_names:
            return []

        try:
            placeholders = ", ".join([f"'{n}'" for n in entity_names])
            sql = text(f"""
                SELECT DISTINCT e.name, e.type, r.relationship_type
                FROM kg_entities e
                JOIN kg_relationships r ON e.id = r.source_entity_id OR e.id = r.target_entity_id
                WHERE (r.source_entity_name IN ({placeholders})
                   OR r.target_entity_name IN ({placeholders}))
                  AND e.tenant_id = :tenant_id
                LIMIT 50
            """)
            result = await self.db.execute(sql, {"tenant_id": tenant_id})
            rows = result.fetchall()
            return [
                {"name": row[0], "type": row[1], "relationship": row[2]}
                for row in rows
            ]
        except Exception as e:
            logger.warning("Knowledge graph query failed (may not exist): %s", e)
            return []

    async def _build_expanded_queries(self, query: str, entities: List[Dict],
                                       relationships: List[Dict]) -> List[str]:
        expanded = []
        if relationships:
            related_names = list(set(r["name"] for r in relationships))
            if related_names:
                expanded.append(f"{query} related to {', '.join(related_names[:5])}")
        entity_names = [e["name"] for e in entities]
        if entity_names:
            expanded.append(f"{query} about {', '.join(entity_names[:3])}")
        return expanded[:3]

    async def _vector_search(self, query: str, tenant_id: str, limit: int = 10) -> List[Dict]:
        try:
            sql = text("""
                SELECT c.id, c.content, c.document_id, c.metadata,
                       c.content_hash, d.title as doc_title,
                       c.embedding <=> (
                           SELECT embedding FROM rag_chunks
                           WHERE tenant_id = :tenant_id
                           LIMIT 1
                       ) AS distance
                FROM rag_chunks c
                JOIN rag_documents d ON c.document_id = d.id
                WHERE c.tenant_id = :tenant_id
                  AND d.tenant_id = :tenant_id
                  AND c.embedding IS NOT NULL
                ORDER BY c.embedding <=> (
                    SELECT embedding FROM rag_chunks
                    WHERE tenant_id = :tenant_id
                    ORDER BY embedding <=> CAST(:query AS vector)
                    LIMIT 1
                )
                LIMIT :limit
            """)
            result = await self.db.execute(sql, {
                "tenant_id": tenant_id,
                "query": query,
                "limit": limit,
            })
            rows = result.fetchall()
            return [
                {
                    "id": str(row[0]),
                    "content": row[1],
                    "document_id": str(row[2]) if row[2] else "",
                    "metadata": row[3] if row[3] else {},
                    "content_hash": row[4] or "",
                    "doc_title": row[5] or "",
                }
                for row in rows
            ]
        except Exception as e:
            logger.warning("Vector search fallback (no pgvector): %s", e)
            try:
                result = await self.db.execute(
                    select(RAGChunk).where(RAGChunk.client_id == tenant_id)
                    .order_by(RAGChunk.created_at.desc()).limit(limit)
                )
                return [
                    {"id": str(c.id), "content": c.content,
                     "metadata": c.metadata_json or {}, "content_hash": ""}
                    for c in result.scalars().all()
                ]
            except Exception:
                return []


class AgenticRAGService:
    """
    Agentic RAG: the agent iteratively retrieves, evaluates, and refines its search.
    If initial results are insufficient, it generates new queries and retrieves again.
    """

    def __init__(self, db: AsyncSession, llm_complete_fn=None):
        self.db = db
        self.llm = llm_complete_fn
        self.graph_rag = KnowledgeGraphRAGService(db)

    async def retrieve_with_iteration(
        self,
        query: str,
        tenant_id: str,
        max_iterations: int = 3,
        relevance_threshold: float = 0.3,
        use_graph: bool = True,
    ) -> AgenticRAGResult:
        result = AgenticRAGResult()
        all_chunks = []
        reasoning = []

        current_query = query

        for i in range(max_iterations):
            result.iterations = i + 1
            reasoning.append(f"Iteration {i+1}: searching for '{current_query[:80]}'")

            if use_graph:
                ctx = await self.graph_rag.graph_enhanced_retrieval(
                    current_query, tenant_id, max_chunks=10
                )
                new_chunks = ctx.chunks
                if ctx.expanded_queries:
                    reasoning.append(f"Graph expanded queries: {ctx.expanded_queries}")
            else:
                new_chunks = await self._basic_retrieve(current_query, tenant_id, limit=10)

            all_chunks.extend(new_chunks)

            relevance = self._evaluate_relevance(current_query, new_chunks)
            reasoning.append(f"Relevance score: {relevance:.2f} (threshold: {relevance_threshold})")

            if relevance >= relevance_threshold:
                reasoning.append("Sufficient context found, stopping.")
                break

            if i < max_iterations - 1:
                current_query = await self._generate_refined_query(
                    current_query, new_chunks, i + 1
                )
                if current_query == query:
                    reasoning.append("No refinement possible, stopping.")
                    break
                reasoning.append(f"Refined query: '{current_query[:80]}'")

        deduped = self._deduplicate(all_chunks)
        result.sources = deduped
        result.reasoning = reasoning

        context = "\n\n".join(
            f"[Source {j+1}] {c.get('content', '')[:500]}"
            for j, c in enumerate(deduped[:10])
        )

        if self.llm:
            result.answer = await self.llm(
                f"Context:\n{context}\n\n"
                f"Question: {query}\n\n"
                f"Provide a comprehensive answer based on the context above. "
                f"If the context is insufficient, state what's missing."
            )
            result.confidence = min(1.0, len(deduped) / 5) * (result.iterations / max_iterations)
        else:
            result.answer = (
                f"Retrieved {len(deduped)} relevant chunks across "
                f"{result.iterations} iteration(s). Most relevant: "
                f"{deduped[0].get('content', 'N/A')[:200] if deduped else 'No results found.'}"
            )

        return result

    async def _basic_retrieve(self, query: str, tenant_id: str, limit: int = 10) -> List[Dict]:
        try:
            result = await self.db.execute(
                select(RAGChunk).where(RAGChunk.client_id == tenant_id)
                .order_by(RAGChunk.created_at.desc()).limit(limit)
            )
            return [
                {"id": str(c.id), "content": c.content,
                 "metadata": c.metadata_json or {}, "content_hash": ""}
                for c in result.scalars().all()
            ]
        except Exception:
            return []

    def _evaluate_relevance(self, query: str, chunks: List[Dict]) -> float:
        if not chunks:
            return 0.0
        query_words = set(query.lower().split())
        if not query_words:
            return 0.5
        scores = []
        for chunk in chunks:
            content = (chunk.get("content") or "").lower()
            if not content:
                continue
            matches = sum(1 for w in query_words if w in content)
            scores.append(matches / len(query_words))
        return sum(scores) / len(scores) if scores else 0.0

    async def _generate_refined_query(self, original: str, chunks: List[Dict],
                                       iteration: int) -> str:
        if not chunks:
            return original

        content_preview = "\n".join((c.get("content") or "")[:100] for c in chunks[:3])
        terms = set()
        for c in chunks:
            content = c.get("content") or ""
            terms.update(w for w in content.split() if w[0].isupper() and len(w) > 3)

        if terms:
            extra_terms = list(terms)[:5]
            return f"{original} {' '.join(extra_terms)}"

        return original

    def _deduplicate(self, chunks: List[Dict]) -> List[Dict]:
        seen = set()
        deduped = []
        for c in chunks:
            h = c.get("content_hash") or c.get("id") or str(hash(c.get("content", "")))
            if h not in seen:
                seen.add(h)
                deduped.append(c)
        return deduped


class GraphRAGRouter:
    """
    API layer for Graph RAG and Agentic RAG endpoints.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.service = KnowledgeGraphRAGService(db)
        self.agentic = AgenticRAGService(db)

    async def search(self, query: str, tenant_id: str, mode: str = "graph") -> Dict:
        if mode == "agentic":
            result = await self.agentic.retrieve_with_iteration(query, tenant_id)
            return {
                "answer": result.answer,
                "sources": result.sources,
                "iterations": result.iterations,
                "confidence": result.confidence,
                "reasoning": result.reasoning,
            }
        else:
            ctx = await self.service.graph_enhanced_retrieval(query, tenant_id)
            return {
                "entities": ctx.entities,
                "relationships": ctx.relationships,
                "chunks": ctx.chunks,
                "expanded_queries": ctx.expanded_queries,
            }
