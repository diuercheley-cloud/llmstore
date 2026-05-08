import pytest
import pytest_asyncio
from httpx import AsyncClient
import uuid
import os

@pytest.mark.asyncio
async def test_delete_client_empty_id(admin_client: AsyncClient, admin_token_headers):
    # Testing that passing garbage doesn't crash but returns 404 or 422
    resp = await admin_client.post(
        f"/admin/clients/{uuid.uuid4()}/purge",
        headers=admin_token_headers,
        json={"anonymize_instead": True}
    )
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_delete_client_no_auth(admin_client: AsyncClient):
    resp = await admin_client.post(
        f"/admin/clients/{uuid.uuid4()}/purge",
        json={"anonymize_instead": True}
    )
    assert resp.status_code in [401, 403]

@pytest.mark.asyncio
async def test_models_dir_protection():
    # This is more of a system-level check
    root_dir = os.path.dirname(os.path.dirname(__file__))
    models_dir = os.path.join(root_dir, "models")
    assert os.path.exists(models_dir), "Models directory should exist"
    
    # We can't easily test that a script didn't delete it without running the script
    # But we can verify it's still there after validation script runs (done in validate-delete-client-local.sh)
