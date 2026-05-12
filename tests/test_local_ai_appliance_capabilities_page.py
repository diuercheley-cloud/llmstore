import os
import pytest

CAPABILITIES_HTML = "control_plane/app/static/www/capabilities.html"
PUBLIC_API = "control_plane/app/api/public.py"

def test_capabilities_html_mentions_local_ai_appliance():
    assert os.path.exists(CAPABILITIES_HTML)
    with open(CAPABILITIES_HTML, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Local AI Appliance" in content

def test_public_api_mentions_limitations():
    assert os.path.exists(PUBLIC_API)
    with open(PUBLIC_API, "r", encoding="utf-8") as f:
        content = f.read()
    assert "PSP real" in content
    assert "PIX real" in content
