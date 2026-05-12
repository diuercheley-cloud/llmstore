import json
import os
import pytest
from app.services.branding import DEFAULT_BRANDING

BRANDING_JSON = "config/branding.example.json"

def test_branding_json_exists():
    assert os.path.exists(BRANDING_JSON)

def test_branding_json_mentions_local_ai_appliance():
    with open(BRANDING_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "Local AI Appliance" in data.get("product_name", "")

def test_default_branding_python_mentions_local_ai_appliance():
    assert "Local AI Appliance" in DEFAULT_BRANDING.get("product_name", "")
