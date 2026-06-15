import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.services import rag_usage


@pytest.mark.asyncio
async def test_rag_usage_block_and_event_recording():
    result = MagicMock()
    result.scalar_one_or_none.return_value = SimpleNamespace(blocked=True, reason="quota")
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    backend = MagicMock()
    backend.document_store.add_rag_usage_event = AsyncMock()

    assert await rag_usage.check_rag_feature_blocked(session, uuid.uuid4()) == (True, "quota")

    original_resolver = rag_usage.resolve_storage_backend
    rag_usage.resolve_storage_backend = lambda current_session: backend
    try:
        await rag_usage.record_rag_event(session, uuid.uuid4(), "rag_query")
    finally:
        rag_usage.resolve_storage_backend = original_resolver

    backend.document_store.add_rag_usage_event.assert_awaited_once()
