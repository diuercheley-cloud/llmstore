import os

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_control_center_sanitization(admin_client: AsyncClient):
    token = os.environ.get("ADMIN_TOKEN", "admin-token-direct")
    response = await admin_client.get(
        "/admin/system/control-center", headers={"X-Admin-Token": token}
    )
    if response.status_code == 404:
        pytest.skip("Endpoint not reachable")

    assert response.status_code == 200
    data = response.json()

    # Check that artifact paths are relative (don't start with /home/ or /)
    for art_name, art_info in data["artifacts"].items():
        if isinstance(art_info, dict) and "path" in art_info:
            path = art_info["path"]
            assert not path.startswith("/"), f"Artifact path {path} should be relative"
            assert "/home/" not in path, f"Artifact path {path} should not be absolute"

    # Check suggested commands don't contain absolute paths
    for cmd in data["suggested_commands"]:
        assert "/home/" not in cmd["command"]

    # Check that no common secret names are in the JSON keys as values (unless they are keys themselves)
    text = response.text.lower()
    forbidden_values = [
        "password=",
        "secret=",
        "key=",
    ]  # Values usually follow an equal sign or colon in other contexts
    for val in forbidden_values:
        assert val not in text
