import uuid
from unittest.mock import patch

import pytest
import pytest_asyncio
from app.core.config import get_settings
from app.main import app
from app.models.agents import AgentDefinition, AgentRun
from app.models.api_key import ApiKey
from app.models.billing_plan import BillingPlan
from app.models.client import Client
from app.models.multimodal import MultimodalAsset, MultimodalUsageEvent
from sqlalchemy import select


@pytest_asyncio.fixture
async def test_env_setup(admin_client, monkeypatch):
    # Set env variables so any new get_settings() instances see them
    monkeypatch.setenv("MULTIMODAL_ENABLED", "true")
    monkeypatch.setenv("VISION_INPUT_ENABLED", "true")
    monkeypatch.setenv("IMAGE_GENERATION_ENABLED", "true")
    monkeypatch.setenv("SPEECH_TO_TEXT_ENABLED", "true")
    monkeypatch.setenv("REALTIME_AUDIO_ENABLED", "true")

    # Clear cache to force settings reload with our new env variables
    get_settings.cache_clear()
    get_settings()

    from app.db.session import get_db_session
    db_session_override = app.dependency_overrides[get_db_session]
    
    async for db in db_session_override():
        # Setup test plan
        plan = BillingPlan(
            id=uuid.uuid4(),
            code="multimodal_plan",
            name="Multimodal Plan",
            rate_limit_per_minute=100,
            daily_token_quota=100000,
            weekly_token_quota=500000,
            monthly_token_quota=1000000,
            max_output_tokens=1024
        )
        db.add(plan)
        await db.commit()

        # Setup Tenant A
        client_a = Client(
            id=uuid.uuid4(),
            name="tenant-a",
            billing_status="active",
            billing_plan_id=plan.id,
            is_blocked=False
        )
        db.add(client_a)
        
        # Setup Tenant B
        client_b = Client(
            id=uuid.uuid4(),
            name="tenant-b",
            billing_status="active",
            billing_plan_id=plan.id,
            is_blocked=False
        )
        db.add(client_b)
        await db.commit()

        # API Keys for Tenants
        prefix_a = "sk-tenant-a1"
        key_a = ApiKey(
            client_id=client_a.id,
            name="key_a",
            key_prefix=prefix_a,
            key_hash="hash_a",
            is_active=True
        )
        db.add(key_a)

        prefix_b = "sk-tenant-b1"
        key_b = ApiKey(
            client_id=client_b.id,
            name="key_b",
            key_prefix=prefix_b,
            key_hash="hash_b",
            is_active=True
        )
        db.add(key_b)
        await db.commit()

        yield {
            "client": admin_client,
            "db": db,
            "client_a": client_a,
            "client_b": client_b,
            "headers_a": {"Authorization": f"Bearer {prefix_a}.val"},
            "headers_b": {"Authorization": f"Bearer {prefix_b}.val"},
        }
        
    get_settings.cache_clear()


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_multimodal_disabled_bloqueia(mock_verify, test_env_setup, monkeypatch):
    setup = test_env_setup
    client = setup["client"]
    
    # Disable multimodal for this test
    monkeypatch.setenv("MULTIMODAL_ENABLED", "false")
    get_settings.cache_clear()

    # Base64 representing a 1x1 dummy PNG
    b64_image = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkY"
        "AAAAAYAAjCB0C8AAAAASUVORK5CYII="
    )
    response = await client.post(
        "/v1/multimodal/vision",
        headers=setup["headers_a"],
        data={"base64_data": b64_image}
    )
    assert response.status_code == 403
    assert "capabilities are disabled" in response.text


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_image_upload_gera_asset_id_exif_sanitizado(mock_verify, test_env_setup):
    setup = test_env_setup
    client = setup["client"]
    db = setup["db"]

    b64_image = (
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAA"
        "AC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    )
    response = await client.post(
        "/v1/multimodal/vision",
        headers=setup["headers_a"],
        data={"base64_data": b64_image}
    )
    assert response.status_code == 200
    res_data = response.json()
    assert "asset_id" in res_data
    assert res_data["description"] is not None

    asset_id = uuid.UUID(res_data["asset_id"])
    stmt = select(MultimodalAsset).where(MultimodalAsset.id == asset_id)
    res = await db.execute(stmt)
    asset = res.scalar_one_or_none()
    assert asset is not None
    assert asset.exif_sanitized is True


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_tenant_isolation_asset_access(mock_verify, test_env_setup):
    setup = test_env_setup
    client = setup["client"]

    b64_image = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkY"
        "AAAAAYAAjCB0C8AAAAASUVORK5CYII="
    )
    response = await client.post(
        "/v1/multimodal/vision",
        headers=setup["headers_a"],
        data={"base64_data": b64_image}
    )
    assert response.status_code == 200
    asset_id = response.json()["asset_id"]

    response_b = await client.get(
        f"/v1/multimodal/assets/{asset_id}",
        headers=setup["headers_b"]
    )
    assert response_b.status_code == 403
    assert "belongs to another tenant" in response_b.text

    response_a = await client.get(
        f"/v1/multimodal/assets/{asset_id}",
        headers=setup["headers_a"]
    )
    assert response_a.status_code == 200


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_image_generation_mock(mock_verify, test_env_setup):
    setup = test_env_setup
    client = setup["client"]

    response = await client.post(
        "/v1/multimodal/image-generation",
        headers=setup["headers_a"],
        json={"prompt": "A beautiful blue sky", "size": "512x512", "provider": "mock"}
    )
    assert response.status_code == 200
    res_data = response.json()
    assert "asset_id" in res_data
    assert "generated_mock" in res_data["provenance"]


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_speech_to_text_mock(mock_verify, test_env_setup):
    setup = test_env_setup
    client = setup["client"]

    # Base64 representing a 1x1 dummy WAV file
    b64_audio = (
        "UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA="
    )
    response = await client.post(
        "/v1/multimodal/speech-to-text",
        headers=setup["headers_a"],
        data={"base64_audio": b64_audio, "save_audio": False}
    )
    assert response.status_code == 200
    res_data = response.json()
    assert "text" in res_data
    assert "duration" in res_data
    assert res_data["language"] == "pt-BR"
    assert res_data["confidence"] > 0.9


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_agent_run_accepts_asset_id(mock_verify, test_env_setup):
    db = test_env_setup["db"]

    asset = MultimodalAsset(
        id=uuid.uuid4(),
        client_id=test_env_setup["client_a"].id,
        asset_type="image",
        storage_path="/tmp/dummy.png",
        file_size_bytes=100,
        mime_type="image/png",
        file_hash="dummy_hash",
        provenance="uploaded"
    )
    db.add(asset)
    
    agent_def = AgentDefinition(
        id=uuid.uuid4(),
        name="Test Agent",
        model_id="mock-model",
        instructions="Test instructions",
        version="1.0.0",
        owner="test-owner"
    )
    db.add(agent_def)
    await db.commit()

    run = AgentRun(
        id=uuid.uuid4(),
        agent_id=agent_def.id,
        tenant_id=str(test_env_setup["client_a"].id),
        multimodal_asset_id=asset.id,
        status="queued"
    )
    db.add(run)
    await db.commit()

    stmt = select(AgentRun).where(AgentRun.id == run.id)
    res = await db.execute(stmt)
    saved_run = res.scalar_one()
    assert saved_run.multimodal_asset_id == asset.id


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_quotas_bloqueiam_excesso(mock_verify, test_env_setup):
    setup = test_env_setup
    client = setup["client"]
    db = setup["db"]
    client_a_id = setup["client_a"].id

    usage = MultimodalUsageEvent(
        id=uuid.uuid4(),
        client_id=client_a_id,
        feature="vision",
        unit_count=550,
        estimated_cost=11.00
    )
    db.add(usage)
    await db.commit()

    b64_image = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkY"
        "AAAAAYAAjCB0C8AAAAASUVORK5CYII="
    )
    response = await client.post(
        "/v1/multimodal/vision",
        headers=setup["headers_a"],
        data={"base64_data": b64_image}
    )
    assert response.status_code == 429
    assert "Quota exceeded" in response.text


@pytest.mark.asyncio
@patch("app.services.auth.verify_secret", return_value=True)
async def test_admin_usage_api(mock_verify, test_env_setup, admin_token_headers):
    setup = test_env_setup
    client = setup["client"]
    db = setup["db"]
    client_a_id = setup["client_a"].id

    usage = MultimodalUsageEvent(
        id=uuid.uuid4(),
        client_id=client_a_id,
        feature="speech-to-text",
        unit_count=10,
        estimated_cost=0.06
    )
    db.add(usage)
    await db.commit()

    response = await client.get(
        "/admin/multimodal/usage",
        headers=admin_token_headers
    )
    assert response.status_code == 200
    res_data = response.json()
    assert len(res_data) > 0
    assert res_data[0]["feature"] == "speech-to-text"
