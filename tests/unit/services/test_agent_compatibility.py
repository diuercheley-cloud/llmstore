import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.services.agents.agent_compatibility import AgentCompatibilityService


@pytest.mark.asyncio
async def test_agent_compatibility_uses_semantic_version_ordering():
    result = MagicMock()
    result.scalar_one_or_none.return_value = SimpleNamespace(
        platform_version_min="2.9.0",
        platform_version_max="2.11.0",
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)

    response = await AgentCompatibilityService(db).check_compatibility(uuid.uuid4(), "2.10.0")

    assert response == {"compatible": True}
