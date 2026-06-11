import pytest
from unittest.mock import MagicMock
from app.domains.auth.contracts import AuthRepository, UserData
from app.domains.auth.repositories import SqlAlchemyAuthRepository

@pytest.mark.asyncio
async def test_auth_repository_contract():
    db = MagicMock()
    repo = SqlAlchemyAuthRepository(db)
    assert isinstance(repo, AuthRepository)

def test_user_data_schema():
    user = UserData(
        id="user-1",
        username="testuser",
        email="test@example.com",
        roles=["admin"],
        permissions=["system:read"]
    )
    assert user.username == "testuser"
    assert "admin" in user.roles
    assert user.is_active is True
