import pytest
from unittest.mock import MagicMock, patch
from app.core.config import Settings

# Create a mock settings object that satisfies all Pydantic validation requirements
# We need to ensure that this mock object has all attributes that Settings would have.
class MockSettings(MagicMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.jwt_secret = "a-valid-secret-key-32-chars-long!"
        self.admin_token = "a-valid-admin-token-32-chars-long!"

@pytest.fixture(autouse=True)
def mock_get_settings():
    valid_settings = MockSettings()
    with patch("app.db.session.settings", valid_settings), \
         patch("app.core.config.get_settings", return_value=valid_settings):
        yield

def test_jwt_secret_default_insecure():
    """Ensure that setting JWT_SECRET to default value raises an error."""
    # We bypass the fixture mock by testing the real Settings class directly.
    with pytest.raises(ValueError, match="Default value is insecure"):
        Settings(_env_file=None, JWT_SECRET="change-me-at-all-costs")

def test_jwt_secret_too_short():
    """Ensure that setting JWT_SECRET to a short value raises an error."""
    with pytest.raises(ValueError, match="too short"):
        Settings(_env_file=None, JWT_SECRET="short-secret")

def test_jwt_secret_valid():
    """Ensure that a valid JWT_SECRET passes."""
    secret = "a-long-enough-and-very-secure-secret-key-32-chars-plus"
    settings = Settings(_env_file=None, JWT_SECRET=secret)
    assert settings.jwt_secret == secret
