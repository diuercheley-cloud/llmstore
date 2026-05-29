from pathlib import Path

import pytest

from app.services.agents.catalog.capability_catalog import CapabilityCatalogService


@pytest.mark.asyncio
async def test_capability_catalog_install_and_approve(session):
    service = CapabilityCatalogService(session)
    entry = await service.install_entry(
        {
            "name": "e2e-catalog-plugin",
            "category": "plugin",
            "version": "1.0.0",
            "owner": "platform-ops",
            "manifest": {"entrypoint": "main.py"},
            "permissions": ["fs:read"],
            "status": "draft",
        }
    )

    approved = await service.approve_entry(entry.id, entry.id, "release-line approval")

    assert approved.status == "approved"

    artifact = Path("artifacts/e2e/production-agentic/capability-catalog.md")
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(
        "## Capability Catalog E2E\n- Install path: Real DB-backed\n- Approval path: Real state transition\n",
        encoding="utf-8",
    )
