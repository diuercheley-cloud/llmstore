from unittest.mock import AsyncMock, patch

import pytest
from starlette.requests import Request

from app.middleware import request_context_middleware


def _request(content_length: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/health",
            "headers": [(b"content-length", content_length.encode())],
            "client": ("127.0.0.1", 1234),
            "scheme": "http",
            "server": ("test", 80),
            "query_string": b"",
        }
    )


@pytest.mark.parametrize("content_length", ["invalid", "-1"])
async def test_invalid_content_length_is_rejected(content_length):
    settings = type("Settings", (), {"max_request_body_size_bytes": 1024})()
    with patch("app.middleware.get_settings", return_value=settings):
        response = await request_context_middleware(_request(content_length), AsyncMock())
    assert response.status_code == 400
