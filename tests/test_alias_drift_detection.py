import pytest
from app.models.commercial_model_supply_chain import CommercialModelIntegrityEvent
from app.models.model_registry import ModelRegistry
from app.services.models.runtime_attestation import collect_runtime_attestation
from app.services.models.runtime_integrity_monitor import detect_alias_drift, scan_registered_models
from app.services.models.signed_model_registry import register_model_manifest
from sqlalchemy import select


def _runtime_model(path: str, *, alias: str, model_id: str) -> ModelRegistry:
    return ModelRegistry(
        model_id=model_id,
        model_alias=alias,
        provider="llama.cpp",
        model_file=path,
        context_length=4096,
        is_active=True,
        is_default=True,
        status="configured",
    )


@pytest.mark.asyncio
async def test_alias_drift_detected_for_different_file(session, tmp_path):
    expected_file = tmp_path / "expected.gguf"
    runtime_file = tmp_path / "runtime.gguf"
    expected_file.write_bytes(b"expected")
    runtime_file.write_bytes(b"runtime")
    model = _runtime_model(str(runtime_file), alias="shared-alias", model_id="alias/runtime")
    session.add(model)
    await session.flush()
    entry = await register_model_manifest(
        session,
        model_name=model.model_id,
        model_alias=model.model_alias,
        model_file_path=str(expected_file),
        model_format="gguf",
    )
    attestation = await collect_runtime_attestation(session, model=model, entry=entry)

    result = await detect_alias_drift(session, model=model, entry=entry, attestation=attestation)

    assert result["alias_drift"] is True
    assert "alias_points_to_different_file" in result["reasons"]


@pytest.mark.asyncio
async def test_alias_drift_event_recorded(session, tmp_path):
    expected_file = tmp_path / "expected-2.gguf"
    runtime_file = tmp_path / "runtime-2.gguf"
    expected_file.write_bytes(b"expected")
    runtime_file.write_bytes(b"runtime")
    model = _runtime_model(str(runtime_file), alias="alias-event", model_id="alias/event")
    session.add(model)
    await session.flush()
    entry = await register_model_manifest(
        session,
        model_name=model.model_id,
        model_alias=model.model_alias,
        model_file_path=str(expected_file),
        model_format="gguf",
    )

    await scan_registered_models(session, scan_type="manual")
    events = (await session.execute(select(CommercialModelIntegrityEvent))).scalars().all()

    assert any(item.event_type == "alias_drift_detected" for item in events)
