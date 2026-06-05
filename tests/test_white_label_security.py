import os
import re
import subprocess

import pytest

CONFIG_EXAMPLE = "config/branding.example.json"


def test_config_not_tracked():
    result = subprocess.check_output(["git", "ls-files", "config/branding.local.json"], stderr=subprocess.DEVNULL, text=True)
    assert result.strip() == "", "config/branding.local.json should NOT be tracked by Git"


def test_example_config_no_secrets():
    with open(CONFIG_EXAMPLE, "r") as f:
        content = f.read()
    secrets_patterns = [
        r"sk-[a-zA-Z0-9]{20,}",
        r"ghp_[a-zA-Z0-9]{36}",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        r"ADMIN_TOKEN=",
        r"JWT_SECRET=",
    ]
    for pattern in secrets_patterns:
        matches = re.findall(pattern, content)
        if matches:
            pytest.fail(f"Secret pattern found in config: {matches[0]}")


def test_branding_service_no_env_exposure():
    import sys
    sys.path.insert(0, "control_plane")
    from app.services.branding import get_safe_branding
    b = get_safe_branding()
    for key, value in b.items():
        if isinstance(value, str):
            assert "sk-" not in value, f"Secret exposed in branding field {key}"
            assert "${" not in value, f"Env var pattern in branding field {key}"


def test_branding_endpoint_no_auth_required():
    from app.api.public import router
    for route in router.routes:
        if "branding" in route.path:
            # Public endpoint should not have authentication dependencies
            path = route.path
            assert "/public/" in path, f"Branding endpoint not in public namespace: {path}"
            return


def test_branding_service_fails_gracefully():
    """Branding service should not crash when config file is missing or broken."""
    import os
    import sys
    import tempfile
    sys.path.insert(0, "control_plane")
    import importlib

    from app.services import branding

    # Test with broken JSON
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    temp.write("not valid json")
    temp.close()

    original_path = branding.BRANDING_CONFIG_PATH
    try:
        branding.BRANDING_CONFIG_PATH = type(original_path)(temp.name)
        importlib.reload(branding)
        b = branding.get_safe_branding()
        assert b["product_name"] == "LLM Inference Stack"
    finally:
        os.unlink(temp.name)
        branding.BRANDING_CONFIG_PATH = original_path
        importlib.reload(branding)


def test_branding_service_invalid_types():
    """Branding service should handle wrong types gracefully."""
    import json
    import os
    import sys
    sys.path.insert(0, "control_plane")
    from app.services.branding import BRANDING_CONFIG_PATH, load_branding

    original_exists = BRANDING_CONFIG_PATH.exists()
    original_content = None
    if original_exists:
        with open(str(BRANDING_CONFIG_PATH)) as f:
            original_content = f.read()

    try:
        with open(str(BRANDING_CONFIG_PATH), "w") as f:
            json.dump({
                "product_name": ["not", "a", "string"],
                "show_powered_by": "not_a_bool",
                "primary_color": 12345,
            }, f)
        b = load_branding()
        assert b["product_name"] == "LLM Inference Stack"
        assert b["show_powered_by"] is True
        assert b["primary_color"] == "#c84c2f"
    finally:
        if original_exists and original_content is not None:
            with open(str(BRANDING_CONFIG_PATH), "w") as f:
                f.write(original_content)
        elif BRANDING_CONFIG_PATH.exists():
            os.unlink(str(BRANDING_CONFIG_PATH))
