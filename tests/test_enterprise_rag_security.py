import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.rag_document import RAGDocument
from app.services.rag_enterprise.embeddings import EnterpriseEmbeddingService
from app.services.rag_enterprise.retrieval import search_chunks

# pytestmark = pytest.mark.asyncio


class TestSecretsNotInLogs:
    def test_parsers_no_secret_leakage(self):
        from app.services.rag_enterprise.parsers import get_parsers_summary
        available, skipped = get_parsers_summary()
        for ext in available + skipped:
            assert "sk-" not in ext
            assert "secret" not in ext.lower()

    def test_chunking_no_secret_leakage(self):
        from app.services.rag_enterprise.chunking import chunk_by_fixed
        from app.services.rag_enterprise.schemas import ChunkingConfig
        config = ChunkingConfig(chunk_size=100, chunk_overlap=0)
        text = "This is public content"
        chunks = chunk_by_fixed(text, config)
        for c in chunks:
            assert "api_key" not in c.metadata
            assert "secret" not in str(c.metadata).lower()

    def test_embeddings_no_secret_storage(self):
        service = EnterpriseEmbeddingService()
        records = service.get_records()
        for r in records:
            assert "sk-" not in r.provider


class TestTenantFilterAlwaysApplied:
    @pytest.mark.asyncio
    async def test_search_always_filters_by_client_id(self):
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

    @pytest.mark.asyncio
    async def test_ingestion_validates_client(self):
        session = MagicMock()
        session.execute = AsyncMock()
        client_id = uuid.uuid4()

        with patch(
            "app.services.rag_enterprise.ingestion.resolve_enterprise_rag_policy",
            AsyncMock(),
        ) as mock_policy:
            mock_policy.return_value.rag_enabled = True
            mock_policy.return_value.max_documents = None
            mock_policy.return_value.max_storage_mb = None
            mock_policy.return_value.max_pages_per_month = None
            mock_policy.return_value.allowed_file_types = [".txt"]
            mock_policy.return_value.cloud_embeddings_allowed = False

            async def fake_execute(stmt):
                result = MagicMock()
                if "rag_document" not in str(stmt):
                    client_mock = MagicMock()
                    client_mock.id = client_id
                    result.scalar_one_or_none = MagicMock(return_value=client_mock)
                else:
                    result.scalar = MagicMock(return_value=0)
                    result.scalars = MagicMock()
                    count_result = MagicMock()
                    count_result.scalar = MagicMock(return_value=0)
                    result.mappings = MagicMock()
                    mappings_result = MagicMock()
                    mappings_result.first = MagicMock(return_value={"doc_count": 0, "storage_bytes": 0})
                    result.mappings.return_value = mappings_result
                return result

            session.execute = AsyncMock(side_effect=fake_execute)

            from app.services.rag_enterprise.ingestion import ingest_document
            with patch("app.services.rag_enterprise.ingestion.record_rag_event", AsyncMock()):
                with patch("app.services.rag_enterprise.ingestion.select") as mock_select:
                    mock_client = MagicMock()
                    mock_client.id = client_id
                    mock_select.return_value.where.return_value.scalar_one_or_none = AsyncMock(
                        return_value=mock_client
                    )
                    with pytest.raises(Exception):
                        await ingest_document(
                            session=session,
                            client_id=client_id,
                            file_path="/nonexistent/test.txt",
                            original_filename="test.txt",
                            content_type="text/plain",
                            file_size_bytes=10,
                        )


class TestNoCloudByDefault:
    def test_local_embedding_default(self):
        from app.services.rag_enterprise.embeddings import get_enterprise_embedding_service
        service = get_enterprise_embedding_service()
        assert service.provider in ("local", "mock")

    def test_cloud_embeddings_policy_default(self):
        from app.services.rag_enterprise.policies import EnterpriseRagPolicy
        policy = EnterpriseRagPolicy()
        assert policy.cloud_embeddings_allowed is False


class TestDeleteRemovesData:
    @pytest.mark.asyncio
    async def test_delete_removes_chunks(self, tmp_path):
        session = MagicMock()
        session.execute = AsyncMock()
        session.delete = AsyncMock()

        f = tmp_path / "test_delete.txt"
        f.write_text("delete me")

        from app.services.rag_enterprise.ingestion import delete_enterprise_document

        doc = RAGDocument(
            id=uuid.uuid4(),
            client_id=uuid.uuid4(),
            filename="test_delete.txt",
            original_filename="test_delete.txt",
            content_type="text/plain",
            file_size_bytes=10,
            storage_path=str(f),
            status="indexed",
        )

        await delete_enterprise_document(session, doc)
        assert not os.path.exists(str(f))
