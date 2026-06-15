import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_developer_docs_endpoint_exists_and_contains_expected_content():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/developer-docs")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        content = response.text

        # Check required topics
        assert "Base URL Local" in content
        assert "localhost:8000" in content
        assert "Autenticação" in content
        assert "Bearer" in content
        assert "GET /v1/models" in content
        assert "POST /v1/chat/completions" in content
        assert "Streaming" in content
        assert "curl" in content
        assert "import requests" in content
        assert "fetch(" in content
        assert "Rate Limit" in content
        assert "Quotas" in content
        assert "Billing" in content

        # Check if optional parts are mentioned
        assert "RAG" in content
        assert "LM Studio Backend" in content

        # Ensure there is no mandatory external domain (checking for a placeholder example if needed)
        # Assuming no forced external domains are used in the markdown
