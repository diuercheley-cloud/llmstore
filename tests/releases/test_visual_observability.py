import pytest
import uuid
import sys
import os
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "control_plane"))

from app.services.visual_observability import VisualObservabilityService, sanitize_dict
from app.models.agents import AgentIncident

def test_sanitize_dict():
    data = {
        "api_key": "secret123",
        "nested": {
            "token": "token123",
            "safe": "hello"
        },
        "safe_field": 42
    }
    sanitized = sanitize_dict(data)
    assert sanitized["api_key"] == "********"
    assert sanitized["nested"]["token"] == "********"
    assert sanitized["nested"]["safe"] == "hello"
    assert sanitized["safe_field"] == 42

@pytest.mark.asyncio
async def test_empty_timeline_returns_no_data():
    db = AsyncMock()
    db.execute.side_effect = [
        MagicMock(scalars=lambda: MagicMock(all=lambda: [])), # incidents
        MagicMock(scalars=lambda: MagicMock(all=lambda: []))  # workflow events
    ]
    
    svc = VisualObservabilityService(db)
    res = await svc.get_incident_timeline()
    assert res == {"status": "no_data", "items": []}

@pytest.mark.asyncio
async def test_empty_error_budget_returns_no_data():
    db = AsyncMock()
    db.execute.side_effect = [
        MagicMock(scalar=lambda: 0), # total runs
        MagicMock(scalar=lambda: 0)  # failed runs
    ]
    
    svc = VisualObservabilityService(db)
    res = await svc.get_error_budget()
    assert res["status"] == "no_data"
