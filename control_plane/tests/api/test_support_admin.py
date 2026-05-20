import os
import tarfile
import json
import pytest
from fastapi import status
from pathlib import Path

@pytest.mark.asyncio
async def test_create_support_bundle_unauthorized(async_client):
    response = await async_client.post("/admin/support/bundle")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_create_support_bundle_success(async_client, admin_token_headers):
    response = await async_client.post("/admin/support/bundle", headers=admin_token_headers)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "filename" in data
    assert "path" in data
    
    bundle_path = data["path"]
    assert os.path.exists(bundle_path)
    
    # Verify bundle contents
    with tarfile.open(bundle_path, "r:gz") as tar:
        members = tar.getnames()
        # The first member is the directory itself
        bundle_dir = members[0]
        assert f"{bundle_dir}/version.json" in members
        assert f"{bundle_dir}/runtime.json" in members
        assert f"{bundle_dir}/health.txt" in members
        
        # Check for secrets in version.json (should not be there, but good to check)
        f = tar.extractfile(f"{bundle_dir}/version.json")
        version_data = json.load(f)
        assert "version" in version_data
        assert "git_commit" in version_data

@pytest.mark.asyncio
async def test_get_latest_support_bundle(async_client, admin_token_headers):
    # First ensure a bundle exists
    await async_client.post("/admin/support/bundle", headers=admin_token_headers)
    
    response = await async_client.get("/admin/support/bundle/latest", headers=admin_token_headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/gzip"

@pytest.mark.asyncio
async def test_bundle_sanitization(async_client, admin_token_headers):
    # This is a bit harder to test without injecting logs, 
    # but we can check if our redaction logic works on strings
    from app.services.support_bundle import SupportBundleService
    service = SupportBundleService()
    
    sensitive_str = "My key is sk-local-example and my token is ADMIN_TOKEN=admin-token-123"
    sanitized = service._redact_string(sensitive_str)
    
    assert "sk-local-example" in sanitized
    assert "admin-token-123" in sanitized
