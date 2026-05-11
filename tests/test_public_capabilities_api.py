import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_PY = ROOT / "control_plane" / "app" / "api" / "public.py"


def test_json_response_structure():
    content = PUBLIC_PY.read_text()
    assert '"version":' in content or "'version':" in content
    assert '"local_appliance_mode":' in content or "'local_appliance_mode':" in content
    assert '"features":' in content or "'features':" in content
    assert '"limitations":' in content or "'limitations':" in content
    assert '"note":' in content or "'note':" in content


def test_version_field():
    content = PUBLIC_PY.read_text()
    assert "project_version" in content


def test_features_is_list():
    content = PUBLIC_PY.read_text()
    assert '"features"' in content or "'features'" in content


def test_each_feature_has_name_status_stage():
    content = PUBLIC_PY.read_text()
    assert '"name":' in content or "'name':" in content
    assert '"status":' in content or "'status':" in content
    assert '"stage":' in content or "'stage':" in content


def test_tools_partial_noted():
    content = PUBLIC_PY.read_text()
    assert "Tools" in content or "tools" in content
    assert "unsupported" in content or "partial" in content


def test_limitations_include_psp():
    content = PUBLIC_PY.read_text()
    assert "PSP" in content or "psp" in content


def test_limitations_include_pix():
    content = PUBLIC_PY.read_text()
    assert "PIX" in content or "pix" in content


def test_limitations_include_https():
    content = PUBLIC_PY.read_text()
    assert "HTTPS" in content or "https" in content


def test_limitations_include_hardware():
    content = PUBLIC_PY.read_text()
    assert "hardware" in content


def test_no_secrets_in_json_response():
    content = PUBLIC_PY.read_text()
    assert "secrets" in content.lower() and "expostos" in content.lower()


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


def test_has_ga_beta_and_partial():
    content = PUBLIC_PY.read_text()
    assert "ga" in content.lower()
    assert "beta" in content.lower()
    assert "future" in content.lower()


def test_limitations_not_empty():
    content = PUBLIC_PY.read_text()
    assert "limitations" in content


def test_features_not_empty():
    content = PUBLIC_PY.read_text()
    assert "features" in content


def test_no_api_keys_in_route():
    content = PUBLIC_PY.read_text()
    for pat in ["sk-", "admin_token", "Bearer"]:
        if pat in content:
            line_with_secret = [
                l for l in content.split("\n") if pat in l and "limitations" not in l.lower() and "features" not in l.lower()
            ]
            for line in line_with_secret:
                assert False, f"Possible secret in route: {line.strip()[:80]}"


def test_local_paths_not_in_json():
    content = PUBLIC_PY.read_text()
    for bad in ["/home/", "/root/", "/var/", "/etc/"]:
        assert bad not in content, f"Local path exposed in JSON: {bad}"
