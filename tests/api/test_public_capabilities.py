import pytest

VALID_LEVELS = {"core", "supported", "beta", "experimental", "deprecated"}
VALID_STATUSES = {"supported", "beta", "experimental", "deprecated"}


@pytest.mark.asyncio
async def test_public_capabilities_response_structure(async_client):
    response = await async_client.get("/public/capabilities")
    assert response.status_code == 200
    payload = response.json()

    assert "version" in payload
    assert "local_appliance_mode" in payload
    assert "features" in payload
    assert isinstance(payload["features"], list)
    assert "limitations" in payload
    assert "note" in payload


@pytest.mark.asyncio
async def test_public_capabilities_features_have_required_fields(async_client):
    response = await async_client.get("/public/capabilities")
    payload = response.json()

    for feature in payload["features"]:
        assert "id" in feature, f"Missing id in {feature}"
        assert "name" in feature, f"Missing name in {feature}"
        assert "status" in feature, f"Missing status in {feature}"
        assert "capability_level" in feature, f"Missing capability_level in {feature}"
        assert "limitations" in feature, f"Missing limitations in {feature}"
        assert "docs_url" in feature, f"Missing docs_url in {feature}"


@pytest.mark.asyncio
async def test_no_feature_is_supported_with_partial_implementation(async_client):
    response = await async_client.get("/public/capabilities")
    payload = response.json()

    for feature in payload["features"]:
        level = feature["capability_level"]
        status = feature["status"]

        if level in ("beta", "experimental"):
            continue
        if status in ("beta", "experimental"):
            continue
        assert level in ("core", "supported"), (
            f"Feature {feature['id']} ({feature['name']}) has "
            f"capability_level={level} but should be core/supported"
        )


@pytest.mark.asyncio
async def test_all_capability_levels_are_valid(async_client):
    response = await async_client.get("/public/capabilities")
    payload = response.json()

    for feature in payload["features"]:
        assert feature["capability_level"] in VALID_LEVELS, (
            f"Invalid capability_level={feature['capability_level']} for feature {feature['id']}"
        )
        assert feature["status"] in VALID_STATUSES, (
            f"Invalid status={feature['status']} for feature {feature['id']}"
        )


@pytest.mark.asyncio
async def test_capabilities_includes_openai_api(async_client):
    response = await async_client.get("/public/capabilities")
    payload = response.json()
    ids = {f["id"] for f in payload["features"]}
    assert "openai-api" in ids, "openai-api must be present as a core capability"


@pytest.mark.asyncio
async def test_capabilities_respects_feature_flags(monkeypatch, async_client):
    from app.core.config import get_settings

    get_settings.cache_clear()

    monkeypatch.setenv("AGENT_RUNTIME_ENABLED", "false")
    monkeypatch.setenv("AGENT_STUDIO_ENABLED", "false")

    get_settings.cache_clear()

    response = await async_client.get("/public/capabilities")
    payload = response.json()
    ids = {f["id"] for f in payload["features"]}

    assert "agentic-runtime" not in ids, (
        "agentic-runtime should be excluded when AGENT_RUNTIME_ENABLED=false"
    )
    assert "agent-studio" not in ids, (
        "agent-studio should be excluded when AGENT_STUDIO_ENABLED=false"
    )
