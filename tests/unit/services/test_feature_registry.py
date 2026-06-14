import os
from typing import Any, Dict, List

import pytest

from app.services.feature_registry import FeatureRegistry, _SURFACE_AREA_MAP

_VALID_LEVELS = {"core", "supported", "beta", "experimental", "deprecated"}
_VALID_STATUSES = {"supported", "beta", "experimental", "deprecated"}


@pytest.fixture
def registry() -> FeatureRegistry:
    return FeatureRegistry()


def test_registry_loads_capabilities(registry: FeatureRegistry):
    caps = registry._load()
    assert len(caps) > 0, "supported-surface.yaml must contain capabilities"


def test_registry_loads_known_capabilities(registry: FeatureRegistry):
    caps = registry._load()
    ids = {c.get("id") for c in caps}
    for expected in {"openai-api", "billing", "rag", "tts", "plugin-runtime"}:
        assert expected in ids, f"Missing expected capability: {expected}"


def test_public_capabilities_excludes_internal(registry: FeatureRegistry):
    caps = registry.get_public_capabilities()
    for c in caps:
        assert c["status"] != "internal", f"Internal capability leaked: {c['id']}"
        assert c["capability_level"] != "internal"


def test_public_capabilities_each_has_required_fields(registry: FeatureRegistry):
    caps = registry.get_public_capabilities()
    assert len(caps) > 0
    for c in caps:
        assert "id" in c, f"Missing id in {c}"
        assert "name" in c, f"Missing name in {c}"
        assert "status" in c, f"Missing status in {c}"
        assert "capability_level" in c, f"Missing capability_level in {c}"
        assert "limitations" in c, f"Missing limitations in {c}"
        assert "docs_url" in c, f"Missing docs_url in {c}"


def test_no_partial_feature_appears_as_supported_or_core(registry: FeatureRegistry):
    caps = registry.get_public_capabilities()
    for c in caps:
        if c["capability_level"] in ("beta", "experimental"):
            continue
        if c["status"] in ("beta", "experimental"):
            continue
        assert c["capability_level"] in ("core", "supported"), (
            f"Feature {c['id']} ({c['name']}) has capability_level={c['capability_level']} "
            f"but should be core/supported"
        )


def test_disabled_features_excluded_when_flag_off(monkeypatch):
    from app.core.config import get_settings
    get_settings.cache_clear()

    monkeypatch.setenv("AGENT_RUNTIME_ENABLED", "false")
    monkeypatch.setenv("AGENT_STUDIO_ENABLED", "false")
    monkeypatch.setenv("AGENT_MEMORY_ENABLED", "false")
    monkeypatch.setenv("AGENT_MCP_ENABLED", "false")
    monkeypatch.setenv("AGENT_WORKER_ENABLED", "false")

    get_settings.cache_clear()
    reg = FeatureRegistry()
    caps = reg.get_public_capabilities()
    cap_ids = {c["id"] for c in caps}

    assert "agentic-runtime" not in cap_ids, (
        "agentic-runtime should be excluded when AGENT_RUNTIME_ENABLED=false"
    )
    assert "agent-studio" not in cap_ids, (
        "agent-studio should be excluded when AGENT_STUDIO_ENABLED=false"
    )
    assert "agent-memory" not in cap_ids, (
        "agent-memory should be excluded when AGENT_MEMORY_ENABLED=false"
    )


def test_enabled_features_included_when_flag_on(monkeypatch):
    from app.core.config import get_settings
    get_settings.cache_clear()

    monkeypatch.setenv("AGENT_RUNTIME_ENABLED", "true")
    monkeypatch.setenv("AGENT_MEMORY_ENABLED", "true")
    monkeypatch.setenv("AGENT_MCP_ENABLED", "true")

    get_settings.cache_clear()
    reg = FeatureRegistry()
    caps = reg.get_public_capabilities()
    cap_ids = {c["id"] for c in caps}

    assert "agentic-runtime" in cap_ids, (
        "agentic-runtime should be included when AGENT_RUNTIME_ENABLED=true"
    )
    assert "agent-memory" in cap_ids, (
        "agent-memory should be included when AGENT_MEMORY_ENABLED=true"
    )


def test_capability_level_matches_surface_status(registry: FeatureRegistry):
    caps = registry._load()
    for c in caps:
        surface_status = c.get("status", "")
        level = _SURFACE_AREA_MAP.get(surface_status)
        if level is None:
            continue
        if surface_status == "internal":
            continue
        expected_status = "supported" if surface_status in ("production_core", "production_optional") else surface_status
        public = registry._compute_api_status(surface_status)
        assert public == expected_status, (
            f"Capability {c['id']}: surface_status={surface_status} "
            f"should map to status={expected_status}, got {public}"
        )


def test_all_features_have_valid_level_and_status(registry: FeatureRegistry):
    caps = registry.get_public_capabilities()
    for c in caps:
        assert c["capability_level"] in _VALID_LEVELS, (
            f"Feature {c['id']}: invalid capability_level={c['capability_level']}"
        )
        assert c["status"] in _VALID_STATUSES, (
            f"Feature {c['id']}: invalid status={c['status']}"
        )
