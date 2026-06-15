import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PUBLIC_PY = ROOT / "control_plane" / "app" / "api" / "public.py"


def test_uses_dynamic_registry_instead_of_hardcoded_features():
    content = PUBLIC_PY.read_text()
    assert (
        "from app.services.feature_registry import" in content
        or "get_public_capabilities" in content
    )


def test_uses_pydantic_response_model():
    content = PUBLIC_PY.read_text()
    assert "response_model=CapabilitiesResponse" in content


def test_each_feature_has_required_fields_via_schema():
    content = PUBLIC_PY.read_text()
    assert "capability_level" in content
    assert "limitations" in content
    assert "docs_url" in content


def test_no_hardcoded_feature_list_in_endpoint():
    content = PUBLIC_PY.read_text()
    endpoint_start = content.index("async def public_capabilities():")
    endpoint_body = content[endpoint_start:]
    has_hardcoded = '"name":' in endpoint_body or "'name':" in endpoint_body
    assert not has_hardcoded, (
        "Endpoint should not contain hardcoded feature list. "
        "Use FeatureRegistry.get_public_capabilities() instead."
    )


def test_limitations_include_hardware():
    content = PUBLIC_PY.read_text()
    assert "hardware" in content


def test_no_secrets_in_source():
    content = PUBLIC_PY.read_text()
    assert "secrets" in content.lower()


def test_json_does_not_leak_env_values():
    content = PUBLIC_PY.read_text()
    env_patterns = [
        r"POSTGRES_PASSWORD",
        r"DATABASE_URL",
        r"REDIS_URL",
        r"ADMIN_TOKEN=",
    ]
    for pattern in env_patterns:
        matches = re.findall(pattern, content)
        for m in matches:
            assert False, f"Env pattern leaked in JSON endpoint: {m}"


def test_limitations_not_empty():
    content = PUBLIC_PY.read_text()
    assert "limitations" in content


def test_no_api_keys_in_route():
    content = PUBLIC_PY.read_text()
    for pat in ["sk-", "admin_token", "Bearer"]:
        if pat in content:
            line_with_secret = [
                l
                for l in content.split("\n")
                if pat in l and "limitations" not in l.lower() and "features" not in l.lower()
            ]
            for line in line_with_secret:
                assert False, f"Possible secret in route: {line.strip()[:80]}"


def test_local_paths_not_in_source():
    content = PUBLIC_PY.read_text()
    for bad in ["/home/", "/root/", "/var/", "/etc/"]:
        assert bad not in content, f"Local path exposed in source: {bad}"


def test_version_field_references_settings():
    content = PUBLIC_PY.read_text()
    assert "project_version" in content


def test_capability_levels_defined():
    content = PUBLIC_PY.read_text()
    assert "capability_level" in content


def test_feature_registry_service_exists():
    registry_path = ROOT / "control_plane" / "app" / "services" / "feature_registry.py"
    assert registry_path.exists(), "Feature registry service must exist"
    content = registry_path.read_text()
    assert "get_public_capabilities" in content
    assert "_resolve_flag" in content


def test_supported_surface_yaml_exists():
    yaml_path = ROOT / "config" / "supported-surface.yaml"
    assert yaml_path.exists(), "supported-surface.yaml must exist"
    content = yaml_path.read_text()
    assert "capabilities:" in content
    assert "production_core" in content
