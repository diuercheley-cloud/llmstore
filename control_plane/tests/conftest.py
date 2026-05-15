import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import get_settings

@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.fixture
def admin_token_headers():
    settings = get_settings()
    token = settings.admin_super_token or settings.admin_token or "test-admin-token"
    return {"X-Admin-Token": token}
