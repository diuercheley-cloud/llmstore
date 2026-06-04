import json
import os

CONFIG_EXAMPLE = "config/branding.example.json"
REQUIRED_FIELDS = [
    "product_name", "company_name", "tagline", "support_email",
    "primary_color", "secondary_color", "footer_text",
    "show_powered_by", "capabilities_title",
]


def test_config_example_exists():
    assert os.path.isfile(CONFIG_EXAMPLE), f"Missing: {CONFIG_EXAMPLE}"


def test_config_example_valid_json():
    with open(CONFIG_EXAMPLE, "r") as f:
        data = json.load(f)
    assert isinstance(data, dict)


def test_config_example_has_all_fields():
    with open(CONFIG_EXAMPLE, "r") as f:
        data = json.load(f)
    for field in REQUIRED_FIELDS:
        assert field in data, f"Missing field: {field}"


def test_config_example_no_secrets():
    with open(CONFIG_EXAMPLE, "r") as f:
        content = f.read()
    forbidden = ["sk-", "ghp_", "-----BEGIN", "ADMIN_TOKEN=", "JWT_SECRET="]
    for pattern in forbidden:
        assert pattern not in content, f"Secret pattern found: {pattern}"


def test_config_example_hex_colors():
    with open(CONFIG_EXAMPLE, "r") as f:
        data = json.load(f)
    import re
    hex_pattern = re.compile(r"^#[0-9a-fA-F]{6}$")
    assert hex_pattern.match(data["primary_color"]), f"Invalid primary_color: {data['primary_color']}"
    assert hex_pattern.match(data["secondary_color"]), f"Invalid secondary_color: {data['secondary_color']}"


def test_config_example_show_powered_by_is_bool():
    with open(CONFIG_EXAMPLE, "r") as f:
        data = json.load(f)
    assert isinstance(data["show_powered_by"], bool)


def test_branding_service_defaults():
    import sys
    sys.path.insert(0, "control_plane")
    from app.services.branding import get_safe_branding
    b = get_safe_branding()
    assert b["product_name"] == "LLM Inference Stack"
    assert b["primary_color"] == "#c84c2f"
    assert b["show_powered_by"] is True


def test_color_validation():
    import sys
    sys.path.insert(0, "control_plane")
    from app.services.branding import _validate_hex_color
    assert _validate_hex_color("#ff0000") == "#ff0000"
    assert _validate_hex_color("#FF0000") == "#ff0000"
    assert _validate_hex_color("#aabbcc") == "#aabbcc"
    assert _validate_hex_color("red") is None
    assert _validate_hex_color("#fff") is None
    assert _validate_hex_color("") is None
    assert _validate_hex_color("123456") is None


def test_sanitize_string():
    import sys
    sys.path.insert(0, "control_plane")
    from app.services.branding import _sanitize_string
    assert _sanitize_string("  Hello  ") == "Hello"
    assert _sanitize_string("<script>alert(1)</script>Test") == "alert(1)Test"
    assert len(_sanitize_string("A" * 500)) <= 200


def test_show_powered_by_disabled():
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
            json.dump({"show_powered_by": False}, f)
        b = load_branding()
        assert b["show_powered_by"] is False
    finally:
        if original_exists and original_content is not None:
            with open(str(BRANDING_CONFIG_PATH), "w") as f:
                f.write(original_content)
        elif BRANDING_CONFIG_PATH.exists():
            os.unlink(str(BRANDING_CONFIG_PATH))
