import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.rag_usage import check_rag_feature_blocked, record_rag_event


@pytest.mark.asyncio
async def test_rag_usage_block_and_event_recording():
    result = MagicMock()
    result.scalar_one_or_none.return_value = SimpleNamespace(blocked=True, reason="quota")
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    session.flush = AsyncMock()

    assert await check_rag_feature_blocked(session, uuid.uuid4()) == (True, "quota")
    await record_rag_event(session, uuid.uuid4(), "rag_query")

    session.add.assert_called_once()
    session.flush.assert_awaited_once()
