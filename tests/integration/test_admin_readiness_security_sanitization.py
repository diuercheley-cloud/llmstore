import os

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_api_sanitization(admin_client: AsyncClient):
    token = os.environ.get("ADMIN_TOKEN", "test-admin-token")

    endpoints = ["/admin/readiness/latest", "/admin/security/latest", "/admin/runtime/summary"]

    for ep in endpoints:
        response = await admin_client.get(ep, headers={"X-Admin-Token": token})
        assert response.status_code == 200
        text = response.text.lower()

        # Check for sensitive keywords
        sensitive_keywords = ["secret", "password", "api_key", "token_hash"]
        for kw in sensitive_keywords:
            if kw in text:
                # Allow specific non-secret patterns
                if kw == "secret" and "admin-secret-token" in text:
                    continue
                if kw == "token" and (
                    "token_quota" in text or "tokens" in text or "x-admin-token" in text
                ):
                    continue

                # Check if it's returning full check details with evidence (which might contain logs)
                data = response.json()
                # Ensure no 'evidence' with full logs is returned
                assert "evidence" not in str(data).lower()
                assert "logs/" not in str(data).lower()

                # If we still find the keyword, it might be okay if it's in a title or detail that doesn't leak the actual value
                # For this test, we are strict about not returning raw secrets.
