from datetime import datetime
from unittest.mock import MagicMock

import pytest
from app.domains.audit.contracts import AuditEntryData, AuditRepository
from app.domains.audit.repositories import SqlAlchemyAuditRepository


@pytest.mark.asyncio
async def test_audit_repository_contract():
    db = MagicMock()
    repo = SqlAlchemyAuditRepository(db)
    assert isinstance(repo, AuditRepository)


def test_audit_entry_data_schema():
    entry = AuditEntryData(
        id="1",
        timestamp=datetime.now(),
        action="test.action",
        actor="test-actor",
        payload={"key": "value"},
        tenant_id="tenant-1",
    )
    assert entry.action == "test.action"
    assert entry.payload["key"] == "value"
