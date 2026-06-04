"""Tests for Graph RAG and Agentic RAG — entity extraction, vector search, iterative retrieval."""

from unittest.mock import AsyncMock, patch

import pytest
from app.services.rag.graph_rag import (
    AgenticRAGResult,
    AgenticRAGService,
    GraphRAGContext,
    GraphRAGRouter,
    KnowledgeGraphRAGService,
)


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def kg_service(mock_db):
    return KnowledgeGraphRAGService(mock_db)


@pytest.fixture
def mock_llm():
    async def fake_complete(ctx: str) -> str:
        return "Mocked answer based on context."
    return fake_complete


@pytest.fixture
def agentic_service(mock_db, mock_llm):
    return AgenticRAGService(mock_db, llm_complete_fn=mock_llm)


class TestKnowledgeGraphRAGService:
    @pytest.mark.asyncio
    async def test_extract_entities_capitalized_words(self, kg_service):
        entities = await kg_service._extract_entities("Alice and Bob work at Acme Corp in New York")
        names = [e["name"] for e in entities]
        assert "Alice" in names
        assert "Bob" in names
        assert "Acme" in names
        assert "New" in names

    @pytest.mark.asyncio
    async def test_extract_entities_single_word(self, kg_service):
        entities = await kg_service._extract_entities("Hello")
        names = [e["name"] for e in entities]
        assert "Hello" in names

    @pytest.mark.asyncio
    async def test_extract_entities_empty(self, kg_service):
        entities = await kg_service._extract_entities("")
        assert entities == []

    @pytest.mark.asyncio
    async def test_extract_entities_fallback_lowercase(self, kg_service):
        entities = await kg_service._extract_entities("hello world")
        assert len(entities) == 1
        assert entities[0]["name"] == "hello"

    @pytest.mark.asyncio
    async def test_build_expanded_queries(self, kg_service):
        queries = await kg_service._build_expanded_queries(
            "Tell me about AI",
            [{"name": "Machine"}, {"name": "Deep"}],
            [{"name": "Neural"}, {"name": "Learning"}],
        )
        assert len(queries) >= 1
        assert all("Tell me about AI" in q for q in queries)

    @pytest.mark.asyncio
    async def test_build_expanded_queries_no_entities(self, kg_service):
        queries = await kg_service._build_expanded_queries("Hello", [], [])
        assert queries == []

    @pytest.mark.asyncio
    async def test_build_expanded_queries_no_relationships(self, kg_service):
        queries = await kg_service._build_expanded_queries(
            "Hello", [{"name": "World"}], [],
        )
        assert len(queries) == 1
        assert "World" in queries[0]

    @pytest.mark.asyncio
    async def test_find_related_entities_empty_list(self, kg_service):
        results = await kg_service._find_related_entities([], "tenant-1")
        assert results == []

    @pytest.mark.asyncio
    async def test_find_related_entities_db_error(self, kg_service):
        kg_service.db.execute = AsyncMock(side_effect=Exception("DB error"))
        results = await kg_service._find_related_entities(["Test"], "tenant-1")
        assert results == []

    @pytest.mark.asyncio
    async def test_vector_search_fallback(self, kg_service):
        kg_service.db.execute = AsyncMock(side_effect=Exception("no pgvector"))
        kg_service.db.execute.return_value = AsyncMock()
        kg_service.db.execute.return_value.scalars = lambda: AsyncMock()
        kg_service.db.execute.return_value.scalars().all = lambda: []
        with patch.object(kg_service, '_vector_search', wraps=kg_service._vector_search):
            results = await kg_service._vector_search("test", "tenant-1", limit=5)
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_graph_enhanced_retrieval(self, kg_service):
        kg_service._extract_entities = AsyncMock(return_value=[{"name": "Test", "type": "extracted"}])
        kg_service._find_related_entities = AsyncMock(return_value=[])
        kg_service._build_expanded_queries = AsyncMock(return_value=["test query"])
        kg_service._vector_search = AsyncMock(return_value=[{"id": "1", "content": "test chunk", "content_hash": "abc"}])
        ctx = await kg_service.graph_enhanced_retrieval("test query", "tenant-1")
        assert isinstance(ctx, GraphRAGContext)
        assert ctx.query == "test query"
        assert len(ctx.chunks) > 0

    @pytest.mark.asyncio
    async def test_graph_enhanced_retrieval_no_entities(self, kg_service):
        kg_service._extract_entities = AsyncMock(return_value=[])
        kg_service._vector_search = AsyncMock(return_value=[{"id": "1", "content": "fallback", "content_hash": "abc"}])
        ctx = await kg_service.graph_enhanced_retrieval("fallback query", "tenant-1")
        assert len(ctx.chunks) == 1
        assert ctx.chunks[0]["content"] == "fallback"


class TestAgenticRAGService:
    def test_evaluate_relevance_high(self, agentic_service):
        score = agentic_service._evaluate_relevance(
            "What is machine learning",
            [{"content": "Machine learning is a subset of artificial intelligence."}],
        )
        assert 0.0 <= score <= 1.0

    def test_evaluate_relevance_low(self, agentic_service):
        score = agentic_service._evaluate_relevance(
            "Quantum physics",
            [{"content": "The weather today is sunny and warm."}],
        )
        assert score < 0.5

    def test_evaluate_relevance_empty_chunks(self, agentic_service):
        score = agentic_service._evaluate_relevance("test", [])
        assert score == 0.0

    def test_evaluate_relevance_no_query_words(self, agentic_service):
        score = agentic_service._evaluate_relevance("", [{"content": "hello"}])
        assert score == 0.5

    def test_deduplicate(self, agentic_service):
        chunks = [
            {"content": "hello", "content_hash": "a"},
            {"content": "hello", "content_hash": "a"},
            {"content": "world", "content_hash": "b"},
        ]
        deduped = agentic_service._deduplicate(chunks)
        assert len(deduped) == 2

    def test_deduplicate_empty(self, agentic_service):
        assert agentic_service._deduplicate([]) == []

    def test_deduplicate_no_hash(self, agentic_service):
        chunks = [
            {"id": "1", "content": "hello"},
            {"id": "2", "content": "world"},
        ]
        deduped = agentic_service._deduplicate(chunks)
        assert len(deduped) == 2

    @pytest.mark.asyncio
    async def test_generate_refined_query(self, agentic_service):
        refined = await agentic_service._generate_refined_query(
            "Tell me about AI",
            [{"content": "Artificial Intelligence is transforming industries."}],
            1,
        )
        assert "AI" in refined

    @pytest.mark.asyncio
    async def test_generate_refined_query_no_capitalized_terms(self, agentic_service):
        refined = await agentic_service._generate_refined_query(
            "hello world",
            [{"content": "just some lowercase text here"}],
            1,
        )
        assert refined == "hello world"

    @pytest.mark.asyncio
    async def test_generate_refined_query_empty_chunks(self, agentic_service):
        refined = await agentic_service._generate_refined_query("test", [], 1)
        assert refined == "test"

    @pytest.mark.asyncio
    async def test_retrieve_with_iteration_basic(self, mock_db, mock_llm):
        agentic = AgenticRAGService(mock_db, llm_complete_fn=mock_llm)
        agentic._basic_retrieve = AsyncMock(return_value=[{"content": "AI is transforming industries.", "content_hash": "a"}])
        result = await agentic.retrieve_with_iteration(
            "Tell me about AI", "tenant-1", max_iterations=3, use_graph=False,
        )
        assert isinstance(result, AgenticRAGResult)
        assert result.answer is not None
        assert result.iterations >= 1

    @pytest.mark.asyncio
    async def test_retrieve_with_iteration_zero_max(self, mock_db):
        agentic = AgenticRAGService(mock_db)
        result = await agentic.retrieve_with_iteration(
            "test", "tenant-1", max_iterations=0,
        )
        assert result.iterations == 0
        assert result.answer != ""

    @pytest.mark.asyncio
    async def test_basic_retrieve(self, mock_db):
        mock_db.execute = AsyncMock()
        mock_db.execute.return_value.scalars.return_value.all.return_value = []
        agentic = AgenticRAGService(mock_db)
        results = await agentic._basic_retrieve("test", "tenant-1", limit=5)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_retrieve_with_iteration_graph_mode(self, mock_db):
        agentic = AgenticRAGService(mock_db)
        with patch.object(agentic.graph_rag, 'graph_enhanced_retrieval', AsyncMock(return_value=GraphRAGContext(chunks=[], query="test"))):
            result = await agentic.retrieve_with_iteration("test", "tenant-1", max_iterations=1, use_graph=True)
            assert result.iterations == 1


class TestGraphRAGRouter:
    @pytest.mark.asyncio
    async def test_search_graph_mode(self, mock_db):
        router = GraphRAGRouter(mock_db)
        with patch.object(router.service, 'graph_enhanced_retrieval', AsyncMock(return_value=GraphRAGContext(
            entities=[], relationships=[], chunks=[], query="test", expanded_queries=["test"],
        ))):
            result = await router.search("test query", "tenant-1", mode="graph")
            assert "entities" in result
            assert "relationships" in result
            assert "chunks" in result

    @pytest.mark.asyncio
    async def test_search_agentic_mode(self, mock_db):
        router = GraphRAGRouter(mock_db)
        with patch.object(router.agentic, 'retrieve_with_iteration', AsyncMock(return_value=AgenticRAGResult(
            answer="test answer", sources=[], iterations=2, confidence=0.8, reasoning=[],
        ))):
            result = await router.search("test query", "tenant-1", mode="agentic")
            assert result["answer"] == "test answer"
            assert result["iterations"] == 2
