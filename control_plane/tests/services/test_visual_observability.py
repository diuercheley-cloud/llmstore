import pytest
from app.services.visual_observability import VisualObservabilityService
import json
import os

def test_dashboard_json_validity():
    dashboard_path = "monitoring/dashboards/platform-overview.json"
    with open(dashboard_path, "r") as f:
        data = json.load(f)
    assert data["uid"] == "platform-overview"

@pytest.mark.asyncio
async def test_incident_timeline_sorting():
    service = VisualObservabilityService()
    timeline = await service.get_incident_timeline()
    assert len(timeline) > 0
    # Check if timestamps are descending (newest first)
    timestamps = [t["timestamp"] for t in timeline]
    assert timestamps == sorted(timestamps, reverse=True)

def test_dashboard_links_no_secrets():
    service = VisualObservabilityService()
    links = service.get_dashboard_links()
    for link in links:
        assert "token" not in link["url"].lower()
        assert "key" not in link["url"].lower()
