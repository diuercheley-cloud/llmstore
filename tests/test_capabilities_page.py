import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HTML_FILE = ROOT / "control_plane" / "app" / "static" / "www" / "capabilities.html"
PUBLIC_PY = ROOT / "control_plane" / "app" / "api" / "public.py"
INDEX_HTML = ROOT / "control_plane" / "app" / "static" / "www" / "index.html"


def test_html_file_exists():
    assert HTML_FILE.exists(), f"{HTML_FILE} not found"


def test_html_is_valid():
    content = HTML_FILE.read_text()
    assert "<!doctype html>" in content
    assert "</html>" in content


def test_route_handler_exists():
    content = PUBLIC_PY.read_text()
    assert "def capabilities_page" in content
    assert "def public_capabilities" in content


def test_route_returns_fileresponse():
    content = PUBLIC_PY.read_text()
    assert "capabilities.html" in content


def test_landing_page_links_capabilities():
    content = INDEX_HTML.read_text()
    assert "/capabilities" in content


REQUIRED_FEATURES = [
    "OpenAI-compatible",
    "Chat Completions",
    "Streaming",
    "Models API",
    "Embeddings",
    "Responses API",
    "RAG",
    "TTS",
    "Client Portal",
    "Admin Dashboard",
    "Admin Lab",
    "Billing",
    "Security Report",
    "Production Readiness",
    "Backup / Restore",
    "Upgrade / Rollback",
    "Demo Pack",
]


def test_all_features_listed():
    content = HTML_FILE.read_text()
    for feature in REQUIRED_FEATURES:
        assert feature.lower() in content.lower(), f"Feature missing: {feature}"


REQUIRED_LIMITATIONS = [
    "PSP",
    "PIX",
    "Tools",
    "Function Calling",
    "hardware",
    "HTTPS",
    "seguranca absoluta",
]


def test_all_limitations_listed():
    content = HTML_FILE.read_text()
    for limit in REQUIRED_LIMITATIONS:
        assert limit.lower() in content.lower(), f"Limitation missing: {limit}"


def test_no_sensitive_paths():
    content = HTML_FILE.read_text()
    sensitive = ["/home/", "/root/", "/var/", "/etc/", "/models/", "/data/"]
    for path in sensitive:
        assert path not in content, f"Sensitive path exposed: {path}"


def test_no_secrets_in_html():
    content = HTML_FILE.read_text()
    patterns = [
        r"ADMIN_TOKEN",
        r"sk-[a-zA-Z0-9]",
        r"Bearer\s+[a-zA-Z0-9._-]{20,}",
        r"-----BEGIN",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, content)
        for m in matches:
            if "example" not in m.lower() and "masked" not in m:
                assert False, f"Potential secret found: {m[:50]}"


def test_html_has_version_loading():
    content = HTML_FILE.read_text()
    assert "version" in content
    assert "fetch" in content or "XMLHttpRequest" in content


def test_html_has_status_css():
    content = HTML_FILE.read_text()
    assert "cap-status" in content


def test_html_has_limits_box():
    content = HTML_FILE.read_text()
    assert "limits-box" in content


def test_html_has_call_to_action_links():
    content = HTML_FILE.read_text()
    for link in ["/client-portal", "/admin-dashboard", "/admin-lab", "/docs"]:
        assert link in content, f"Missing link: {link}"


def test_json_endpoint_has_no_secrets_note():
    content = PUBLIC_PY.read_text()
    assert "secrets" in content.lower() and "expostos" in content.lower()


def test_json_endpoint_has_features():
    content = PUBLIC_PY.read_text()
    assert "features" in content


def test_json_endpoint_has_limitations():
    content = PUBLIC_PY.read_text()
    assert "limitations" in content


def test_json_endpoint_has_version():
    content = PUBLIC_PY.read_text()
    assert "project_version" in content


def test_json_endpoint_has_appliance_mode():
    content = PUBLIC_PY.read_text()
    assert "local_appliance_mode" in content


def test_html_nav_links():
    content = HTML_FILE.read_text()
    for link in ["/", "/docs", "/client-portal", "/admin-dashboard", "/admin-lab"]:
        assert link in content, f"Missing nav link: {link}"


def test_each_feature_has_status_class():
    content = HTML_FILE.read_text()
    for status in ["supported", "partial", "unsupported"]:
        assert f"cap-status {status}" in content, f"Missing status class: {status}"
