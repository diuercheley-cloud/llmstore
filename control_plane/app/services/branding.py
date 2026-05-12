import json
import os
import re
from pathlib import Path

BRANDING_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent.parent / "config" / "branding.local.json"

HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

DEFAULT_BRANDING = {
    "product_name": "LLM Inference Stack",
    "company_name": "LLM Inference Stack",
    "tagline": "LLM Local para Empresas",
    "support_email": "suporte@example.com",
    "primary_color": "#c84c2f",
    "secondary_color": "#0f766e",
    "footer_text": "© 2026 LLM Inference Stack. Todos os direitos reservados.",
    "show_powered_by": True,
    "capabilities_title": "Capabilities & Features",
}


def _sanitize_string(value: str, max_length: int = 200) -> str:
    if not isinstance(value, str):
        return ""
    value = value.strip()
    if len(value) > max_length:
        value = value[:max_length]
    # Remove HTML tags and control characters
    value = re.sub(r"<[^>]*>", "", value)
    value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", value)
    return value


def _validate_hex_color(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if HEX_COLOR_RE.match(value):
        return value.lower()
    return None


def load_branding() -> dict:
    branding = dict(DEFAULT_BRANDING)

    if not BRANDING_CONFIG_PATH.exists():
        return branding

    try:
        with open(BRANDING_CONFIG_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError):
        return branding

    if not isinstance(raw, dict):
        return branding

    string_fields = [
        "product_name", "company_name", "tagline",
        "support_email", "footer_text", "capabilities_title",
    ]
    for field in string_fields:
        if field in raw and isinstance(raw[field], str):
            sanitized = _sanitize_string(raw[field])
            if sanitized:
                branding[field] = sanitized

    if "primary_color" in raw:
        color = _validate_hex_color(str(raw["primary_color"]))
        if color:
            branding["primary_color"] = color

    if "secondary_color" in raw:
        color = _validate_hex_color(str(raw["secondary_color"]))
        if color:
            branding["secondary_color"] = color

    if "show_powered_by" in raw and isinstance(raw["show_powered_by"], bool):
        branding["show_powered_by"] = raw["show_powered_by"]

    return branding


def get_safe_branding() -> dict:
    branding = load_branding()
    return {
        "product_name": branding["product_name"],
        "company_name": branding["company_name"],
        "tagline": branding["tagline"],
        "support_email": branding["support_email"],
        "primary_color": branding["primary_color"],
        "secondary_color": branding["secondary_color"],
        "footer_text": branding["footer_text"],
        "show_powered_by": branding["show_powered_by"],
        "capabilities_title": branding["capabilities_title"],
    }
