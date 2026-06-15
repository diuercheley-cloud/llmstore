import os
from unittest.mock import patch

from app.services.config_service import get_config_service


def test_config_service_feature_flag_override():
    with patch("app.services.config_service._service", None):
        svc = get_config_service()
        # Mock feature flags with a key that is definitely not in env
        with patch.object(svc, "_feature_flags", {"MY_SPECIAL_FLAG_XYZ": True}):
            detailed = svc.get_detailed("MY_SPECIAL_FLAG_XYZ")
            assert detailed.value is True
            assert detailed.source == "file:feature-flags.yaml"


def test_config_service_singleton():
    svc1 = get_config_service()
    svc2 = get_config_service()
    assert svc1 is svc2


def test_config_service_precedence():
    # Reset singleton for test
    with patch("app.services.config_service._service", None):
        svc = get_config_service()
        svc.clear_runtime_overrides()

        # 1. Code Default
        # Use a key that is unlikely to be in env/dotenv
        detailed = svc.get_detailed("SOME_RANDOM_KEY_THAT_DOES_NOT_EXIST")
        assert detailed.source == "default"
        assert detailed.value is None

        # 2. File Override (Mocking feature-flags)
        with patch.object(svc, "_feature_flags", {"TEST_FLAG": "file_val"}):
            detailed = svc.get_detailed("TEST_FLAG")
            assert detailed.value == "file_val"
            assert detailed.source == "file:feature-flags.yaml"

            # 3. Env Override
            with patch.dict(os.environ, {"TEST_FLAG": "env_val"}):
                detailed = svc.get_detailed("TEST_FLAG")
                assert detailed.value == "env_val"
                assert detailed.source == "env"

                # 4. Runtime Override
                svc.set_runtime_override("TEST_FLAG", "runtime_val")
                detailed = svc.get_detailed("TEST_FLAG")
                assert detailed.value == "runtime_val"
                assert detailed.source == "runtime"


def test_config_service_redaction():
    with patch("app.services.config_service._service", None):
        svc = get_config_service()
        svc.set_runtime_override("DATABASE_PASSWORD", "secret123")

        effective = svc.get_effective_config(redact=True)
        pwd_entry = next((item for item in effective if item["key"] == "DATABASE_PASSWORD"), None)
        assert pwd_entry is not None
        assert pwd_entry["value"] == "********"

        effective_no_redact = svc.get_effective_config(redact=False)
        pwd_entry_raw = next(
            (item for item in effective_no_redact if item["key"] == "DATABASE_PASSWORD"), None
        )
        assert pwd_entry_raw["value"] == "secret123"


def test_config_service_nested_file_resolution():
    with patch("app.services.config_service._service", None):
        svc = get_config_service()
        svc._file_configs = {
            "appliance.defaults.yaml": {
                "appliance": {"mode_enabled": True, "DEPLOYMENT_ID": "test-id"}
            }
        }

        # Test case-insensitive nested resolution
        detailed1 = svc.get_detailed("APPLIANCE_MODE_ENABLED")
        assert detailed1.value is True
        assert detailed1.source == "file:appliance.defaults.yaml"

        detailed2 = svc.get_detailed("APPLIANCE_DEPLOYMENT_ID")
        assert detailed2.value == "test-id"


def test_config_service_env_type_conversion():
    with patch("app.services.config_service._service", None):
        svc = get_config_service()

        # Mock settings to have a boolean field
        with patch.dict(os.environ, {"DEBUG": "true"}):
            detailed = svc.get_detailed("DEBUG")
            assert detailed.value is True
            assert isinstance(detailed.value, bool)

        with patch.dict(os.environ, {"DEBUG": "0"}):
            detailed = svc.get_detailed("DEBUG")
            assert detailed.value is False


def test_config_service_get_effective_config_completeness():
    with patch("app.services.config_service._service", None):
        svc = get_config_service()
        svc.set_runtime_override("NEW_RUNTIME_KEY", "val")

        effective = svc.get_effective_config()
        keys = [item["key"] for item in effective]
        assert "NEW_RUNTIME_KEY" in keys
        assert "PROJECT_NAME" in keys
