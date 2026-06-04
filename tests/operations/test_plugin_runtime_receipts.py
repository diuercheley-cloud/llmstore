from types import SimpleNamespace

from app.services.operations.plugin_runtime.receipts import (
    build_abi_contract_receipt,
    build_compatibility_receipt,
    build_federation_compatibility_receipt,
    build_load_plan_receipt,
    build_replay_verification_receipt,
)


def test_plugin_runtime_receipts_have_placeholders():
    contract = SimpleNamespace(client_id="client", id="contract", immutable_hash="a" * 64, contract_hash="b" * 64, deterministic_version="v1")
    load_plan = SimpleNamespace(client_id="client", id="plan", immutable_hash="c" * 64, load_plan_hash="d" * 64)
    compatibility = SimpleNamespace(client_id="client", id="check", immutable_hash="e" * 64, compatibility_status="compatible", runtime_version="1.0.0", reason="ok")
    replay = SimpleNamespace(client_id="client", id="replay", immutable_hash="f" * 64, replay_hash="g" * 64)
    federation = SimpleNamespace(client_id="client", id="fed", immutable_hash="h" * 64, compatibility_hash="i" * 64)
    assert build_abi_contract_receipt(contract)["signature"].startswith("placeholder-signature:")
    assert build_load_plan_receipt(load_plan)["receipt_type"] == "load_plan_receipt"
    assert build_compatibility_receipt(compatibility)["receipt_type"] == "compatibility_receipt"
    assert build_replay_verification_receipt(replay)["receipt_type"] == "replay_verification_receipt"
    assert build_federation_compatibility_receipt(federation)["receipt_type"] == "federation_compatibility_receipt"
