from types import SimpleNamespace

from app.services.operations.compatibility_contracts.receipts import (
    build_contract_receipt,
    build_deprecation_receipt,
    build_negotiation_receipt,
    build_verification_receipt,
)


def test_receipts_include_required_fields():
    contract = SimpleNamespace(
        id="c1",
        client_id="tenant",
        immutable_hash="ih1",
        contract_hash="ph1",
        deterministic_version="v1",
    )
    negotiation = SimpleNamespace(
        id="n1",
        client_id="tenant",
        immutable_hash="ih2",
        source_version="1.0.0",
        target_version="1.1.0",
        negotiated_version="1.0.0",
        negotiation_status="accepted",
    )
    verification = SimpleNamespace(
        id="v1",
        client_id="tenant",
        immutable_hash="ih3",
        verification_type="contract",
        verification_status="passed",
        compatibility_summary="ok",
    )
    deprecation = SimpleNamespace(
        id="d1",
        client_id="tenant",
        immutable_hash="ih4",
        contract_id="c1",
        deprecation_status="announced",
        migration_required=True,
    )
    for receipt in (
        build_contract_receipt(contract),
        build_negotiation_receipt(negotiation),
        build_verification_receipt(verification),
        build_deprecation_receipt(deprecation),
    ):
        assert isinstance(receipt["signature"], str) and len(receipt["signature"]) > 0
        assert receipt["deterministic_version"] == "v1"
