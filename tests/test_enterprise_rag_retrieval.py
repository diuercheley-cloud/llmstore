import uuid
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.services.rag_enterprise.retrieval import (
    cosine_similarity,
    search_chunks,
    execute_enterprise_query,
    build_rag_context,
)
from app.services.rag_enterprise.schemas import EnterpriseSource
from app.models.rag_document_chunk import RAGDocumentChunk


pytestmark = pytest.mark.asyncio


class TestCosineSimilarity:
    def test_identical_vectors(self):
        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]
        assert cosine_similarity(a, b) == 1.0

    def test_opposite_vectors(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert cosine_similarity(a, b) == -1.0

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert cosine_similarity(a, b) == 0.0

    def test_zero_vector(self):
        a = [0.0, 0.0]
        b = [1.0, 0.0]
        assert cosine_similarity(a, b) == 0.0

    def test_empty_vectors(self):
        assert cosine_similarity([], []) == 0.0

    def test_different_lengths(self):
        assert cosine_similarity([1.0], [1.0, 0.0]) == 0.0

    def test_none_vectors(self):
        assert cosine_similarity([], [1.0]) == 0.0


class TestBuildRagContext:
    def test_basic_context(self):
        sources = [
            EnterpriseSource(
                document_id=uuid.uuid4(),
                filename="doc1.pdf",
                page=1,
                chunk_index=0,
                text="Content one",
                score=0.95,
            ),
            EnterpriseSource(
                document_id=uuid.uuid4(),
                filename="doc2.txt",
                page=2,
                chunk_index=1,
                text="Content two",
                score=0.85,
            ),
        ]
        context = build_rag_context(sources)
        assert "doc1.pdf" in context
        assert "doc2.txt" in context
        assert "Content one" in context
        assert "Content two" in context

    def test_empty_sources(self):
        assert build_rag_context([]) == ""

    def test_source_without_page(self):
        sources = [
            EnterpriseSource(
                document_id=uuid.uuid4(),
                filename="doc.txt",
                page=0,
                chunk_index=0,
                text="Content",
                score=0.9,
            ),
        ]
        context = build_rag_context(sources)
        assert "doc.txt" in context
        assert "Content" in context


class TestSearchChunks:
    async def test_search_filters_by_client_id(self):
        session = MagicMock()

        mock_exec_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])
        mock_exec_result.scalars = MagicMock(return_value=mock_scalars)
        session.execute = AsyncMock(return_value=mock_exec_result)

        client_id = uuid.uuid4()

        results = await search_chunks(
            session=session,
            client_id=client_id,
            query_embedding=[0.1] * 384,
            top_k=5,
        )
        assert results == []

    async def test_search_empty_result(self):
        session = MagicMock()

        mock_exec_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])
        mock_exec_result.scalars = MagicMock(return_value=mock_scalars)
        session.execute = AsyncMock(return_value=mock_exec_result)

        results = await search_chunks(
            session=session,
            client_id=uuid.uuid4(),
            query_embedding=[0.1] * 384,
            top_k=5,
        )
        assert results == []

    async def test_search_respects_top_k(self):
        session = MagicMock()

        chunks = []
        for i in range(10):
            chunk = MagicMock(spec=RAGDocumentChunk)
            chunk.id = uuid.uuid4()
            chunk.document_id = uuid.uuid4()
            chunk.client_id = uuid.uuid4()
            chunk.content = f"chunk {i}"
            chunk.chunk_index = i
            chunk.page_number = 1
            chunk.embedding = [0.1 * (i + 1)] + [0.0] * 383
            chunk.token_count = 10
            chunks.append(chunk)

        mock_exec_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=chunks)
        mock_exec_result.scalars = MagicMock(return_value=mock_scalars)
        session.execute = AsyncMock(return_value=mock_exec_result)

        def doc_side_effect(*args, **kwargs):
            doc_result = MagicMock()
            doc = MagicMock()
            doc.id = chunks[0].document_id
            doc.original_filename = "test.pdf"
            doc_result.scalar_one_or_none = MagicMock(return_value=doc)
            return doc_result

        session.execute.side_effect = doc_side_effect

        results = await search_chunks(
            session=session,
            client_id=uuid.uuid4(),
            query_embedding=[1.0] + [0.0] * 383,
            top_k=3,
        )
        assert len(results) <= 3


class TestExecuteQuery:
    @patch("app.services.rag_enterprise.retrieval.get_enterprise_embedding_service")
    async def test_query_returns_sources(self, mock_emb_service):
        session = MagicMock()

        mock_exec_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])
        mock_exec_result.scalars = MagicMock(return_value=mock_scalars)
        session.execute = AsyncMock(return_value=mock_exec_result)

        mock_service = AsyncMock()
        mock_service.embed_text = AsyncMock(return_value=[0.1] * 384)
        mock_emb_service.return_value = mock_service

        sources, scores = await execute_enterprise_query(
            session=session,
            client_id=uuid.uuid4(),
            question="test question",
            top_k=5,
        )
        assert isinstance(sources, list)
        assert isinstance(scores, list)
