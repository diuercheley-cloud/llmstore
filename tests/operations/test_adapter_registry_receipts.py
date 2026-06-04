import uuid

from app.models.operations.adapter_registry import (
    AdapterRegistryDecision,
    SignedAdapterRegistryEntry,
)
from app.services.operations.adapter_registry.receipts import (
    build_registry_decision_receipt,
    build_registry_entry_receipt,
)


class TestAdapterRegistryReceipts:
    def test_build_entry_receipt(self):
        client_id = uuid.uuid4()
        entry = SignedAdapterRegistryEntry(
            id=uuid.uuid4(),
            client_id=client_id,
            adapter_name="test",
            adapter_version="1.0",
            manifest_hash="mhash",
            registry_hash="rhash"
        )
        receipt = build_registry_entry_receipt(entry)
        assert receipt.receipt_type == "adapter_registry_entry"
        assert receipt.client_id == client_id
        assert receipt.signature.startswith("receipt_sig_")

    def test_build_decision_receipt(self):
        client_id = uuid.uuid4()
        decision = AdapterRegistryDecision(
            id=uuid.uuid4(),
            client_id=client_id,
            registry_entry_id=uuid.uuid4(),
            decision_type="approve",
            decision_status="accepted"
        )
        receipt = build_registry_decision_receipt(decision)
        assert receipt.receipt_type == "adapter_registry_decision"
        assert receipt.client_id == client_id
        assert receipt.signature.startswith("receipt_sig_")
