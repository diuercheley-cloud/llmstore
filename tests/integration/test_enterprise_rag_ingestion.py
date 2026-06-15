import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.rag.rag_document import RAGDocument
from app.services.rag_enterprise.ingestion import delete_enterprise_document, ingest_document
from app.services.rag_enterprise.parsers import get_parser_status, get_parsers_summary, parse_file
from app.services.rag_enterprise.schemas import SUPPORTED_EXTENSIONS

pytestmark = pytest.mark.asyncio


class TestIngestionParsers:
    async def test_parse_txt(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Hello world")
        result = await parse_file(str(f), ".txt")
        assert "Hello world" in result.text
        assert result.pages == [1]

    async def test_parse_md(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# Title\nContent")
        result = await parse_file(str(f), ".md")
        assert "# Title" in result.text
        assert result.pages == [1]

    async def test_parse_csv(self, tmp_path):
        f = tmp_path / "test.csv"
        f.write_text("a,b,c\n1,2,3")
        result = await parse_file(str(f), ".csv")
        assert "a, b, c" in result.text
        assert len(result.pages) > 0

    async def test_parse_pdf_unavailable(self, tmp_path):
        status = get_parser_status(".pdf")
        if not status.available:
            f = tmp_path / "test.pdf"
            f.write_bytes(b"%PDF-1.4 fake")
            with pytest.raises(ImportError) as exc:
                await parse_file(str(f), ".pdf")
            assert "pymupdf" in str(exc.value)

    async def test_parse_docx_unavailable(self, tmp_path):
        status = get_parser_status(".docx")
        if not status.available:
            f = tmp_path / "test.docx"
            f.write_bytes(b"fake docx")
            with pytest.raises(ImportError) as exc:
                await parse_file(str(f), ".docx")
            assert "python-docx" in str(exc.value)

    async def test_parse_xlsx_unavailable(self, tmp_path):
        status = get_parser_status(".xlsx")
        if not status.available:
            f = tmp_path / "test.xlsx"
            f.write_bytes(b"fake xlsx")
            with pytest.raises(ImportError) as exc:
                await parse_file(str(f), ".xlsx")
            assert "openpyxl" in str(exc.value)

    async def test_unsupported_extension(self, tmp_path):
        f = tmp_path / "test.xyz"
        f.write_text("content")
        with pytest.raises(ValueError, match="Unsupported file extension"):
            await parse_file(str(f), ".xyz")

    async def test_supported_extensions(self):
        assert ".txt" in SUPPORTED_EXTENSIONS
        assert ".md" in SUPPORTED_EXTENSIONS
        assert ".pdf" in SUPPORTED_EXTENSIONS
        assert ".docx" in SUPPORTED_EXTENSIONS
        assert ".xlsx" in SUPPORTED_EXTENSIONS
        assert ".csv" in SUPPORTED_EXTENSIONS

    async def test_parsers_summary(self):
        available, skipped = get_parsers_summary()
        assert ".txt" in available
        assert ".md" in available
        assert ".csv" in available


class TestIngestionPipeline:
    @patch("app.services.rag_enterprise.ingestion.resolve_enterprise_rag_policy")
    @patch(
        "app.services.rag_enterprise.ingestion.record_rag_event",
        new_callable=AsyncMock,
    )
    async def test_ingest_txt_success(self, mock_record, mock_policy, tmp_path):
        mock_policy.return_value = MagicMock()
        mock_policy.return_value.rag_enabled = True
        mock_policy.return_value.max_documents = None
        mock_policy.return_value.max_storage_mb = None
        mock_policy.return_value.max_pages_per_month = None
        mock_policy.return_value.allowed_file_types = [".txt", ".md", ".csv"]
        mock_policy.return_value.cloud_embeddings_allowed = False

        f = tmp_path / "test.txt"
        f.write_text("Hello world. " * 100)

        session = MagicMock()
        session.execute = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        client_id = uuid.uuid4()
        mock_client = MagicMock()
        mock_client.id = client_id

        exec_result = MagicMock()
        exec_result.scalar_one_or_none = AsyncMock(return_value=mock_client)
        session.execute.return_value = exec_result

        with patch("app.services.rag_enterprise.ingestion.select") as mock_select:
            mock_select.return_value.where.return_value = MagicMock()
            mock_select.return_value.where.return_value.scalar_one_or_none = AsyncMock(
                return_value=mock_client
            )
            doc = await ingest_document(
                session=session,
                client_id=client_id,
                file_path=str(f),
                original_filename="test.txt",
                content_type="text/plain",
                file_size_bytes=os.path.getsize(str(f)),
            )
            assert doc is not None
            assert doc.status == "indexed"

    async def test_ingest_fails_when_rag_disabled(self):
        session = MagicMock()
        session.execute = AsyncMock()

        with patch(
            "app.services.rag_enterprise.ingestion.resolve_enterprise_rag_policy",
            AsyncMock(),
        ) as mock_policy:
            mock_policy.return_value.rag_enabled = False
            with pytest.raises(PermissionError):
                await ingest_document(
                    session=session,
                    client_id=uuid.uuid4(),
                    file_path="/tmp/fake.txt",
                    original_filename="test.txt",
                    content_type="text/plain",
                    file_size_bytes=100,
                )

    async def test_delete_document(self, tmp_path):
        session = MagicMock()
        session.execute = AsyncMock()
        session.delete = AsyncMock()

        f = tmp_path / "test_delete.txt"
        f.write_text("delete me")

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


@pytest.fixture
def mock_session():
    return MagicMock()
