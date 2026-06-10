import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services.agents.a2a.a2a_discovery import A2ADiscoveryService


@pytest.mark.asyncio
async def test_a2a_discovery_announce_requires_registration():
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    service = A2ADiscoveryService(db)

    with patch(
        "app.services.agents.a2a.a2a_discovery.A2ASecurityService.verify_a2a_enabled_or_raise"
    ):
        with pytest.raises(HTTPException, match="Agent not registered"):
            await service.announce_presence("tenant", uuid.uuid4(), {"tools": []})
