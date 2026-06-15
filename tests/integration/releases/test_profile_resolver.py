import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "control_plane"))

from app.services.platform.profile_resolver import ProfileResolver


def test_profile_unknown_env_override_fails():
    # Setting an unknown UPPERCASE env variable should block
    resolver = ProfileResolver()
    with patch_env({"AGENT_UNKNOWN_FEATURE_ENABLED": "true"}):
        with pytest.raises(ValueError, match="Unknown environment override"):
            resolver.resolve("appliance")


def test_profile_high_risk_blocked_without_auth():
    resolver = ProfileResolver()
    with patch_env(
        {"AGENT_CODE_SANDBOX_PROVIDER": "firecracker", "ALLOW_HIGH_RISK_PROFILE_OVERRIDE": "false"}
    ):
        with pytest.raises(ValueError, match="High risk override.*is blocked"):
            resolver.resolve("appliance")


def test_profile_high_risk_allowed_with_auth():
    resolver = ProfileResolver()
    with patch_env(
        {"AGENT_CODE_SANDBOX_PROVIDER": "firecracker", "ALLOW_HIGH_RISK_PROFILE_OVERRIDE": "true"}
    ):
        res = resolver.resolve("appliance")
        assert res["flags"]["AGENT_CODE_SANDBOX_PROVIDER"] == "firecracker"


def test_production_profile_validation_requires_worker():
    resolver = ProfileResolver()
    with patch_env({"AGENT_WORKER_ENABLED": "false"}):
        with pytest.raises(ValueError, match="requires 'AGENT_WORKER_ENABLED' to be true"):
            resolver.resolve("agentic-production")


class patch_env:
    def __init__(self, env_dict):
        self.env_dict = env_dict
        self.original_env = {}

    def __enter__(self):
        for k, v in self.env_dict.items():
            self.original_env[k] = os.environ.get(k)
            os.environ[k] = v

    def __exit__(self, type, value, traceback):
        for k in self.env_dict:
            orig = self.original_env[k]
            if orig is None:
                del os.environ[k]
            else:
                os.environ[k] = orig
