from unittest.mock import MagicMock

import pytest
from app.domains.policy.contracts import PolicyData, PolicyRepository
from app.domains.policy.repositories import SqlAlchemyPolicyRepository


@pytest.mark.asyncio
async def test_policy_repository_contract():
    db = MagicMock()
    repo = SqlAlchemyPolicyRepository(db)
    assert isinstance(repo, PolicyRepository)


def test_policy_data_schema():
    policy = PolicyData(
        id="pol-1",
        client_id="client-1",
        name="Test Policy",
        scope="global",
        version="1.0",
        dsl="{}",
        status="active",
        hash="h1",
        immutable_hash="ih1",
    )
    assert policy.name == "Test Policy"
    assert policy.status == "active"
