from app.core.time import utc_now
from app.models.operations.adapter_registry import (
    AdapterRegistryAllowlistEntry,
    AdapterRegistryBlocklistEntry,
    AdapterRegistryDecision,
    AdapterRegistryPolicy,
    AdapterRegistryReceipt,
    SignedAdapterRegistryEntry,
)
from app.services.operations.adapter_registry.hash_utils import canonical_json, sha256_hex


def build_registry_entry_receipt(entry: SignedAdapterRegistryEntry) -> AdapterRegistryReceipt:
    payload = {
        "id": str(entry.id),
        "adapter_name": entry.adapter_name,
        "adapter_version": entry.adapter_version,
        "manifest_hash": entry.manifest_hash,
        "registry_hash": entry.registry_hash,
    }
    payload_hash = sha256_hex(canonical_json(payload))
    # Deterministic immutable_hash
    immutable_hash = sha256_hex(f"receipt_entry_{entry.immutable_hash}")

    return AdapterRegistryReceipt(
        client_id=entry.client_id,
        registry_entry_id=entry.id,
        receipt_type="adapter_registry_entry",
        payload_hash=payload_hash,
        immutable_hash=immutable_hash,
        signature=f"receipt_sig_{payload_hash[:16]}",
        generated_at=utc_now(),
    )


def build_registry_decision_receipt(decision: AdapterRegistryDecision) -> AdapterRegistryReceipt:
    payload = {
        "id": str(decision.id),
        "registry_entry_id": str(decision.registry_entry_id),
        "decision_type": decision.decision_type,
        "decision_status": decision.decision_status,
    }
    payload_hash = sha256_hex(canonical_json(payload))
    # Deterministic immutable_hash
    immutable_hash = sha256_hex(f"receipt_decision_{decision.immutable_hash}")

    return AdapterRegistryReceipt(
        client_id=decision.client_id,
        registry_entry_id=decision.registry_entry_id,
        receipt_type="adapter_registry_decision",
        payload_hash=payload_hash,
        immutable_hash=immutable_hash,
        signature=f"receipt_sig_{payload_hash[:16]}",
        generated_at=utc_now(),
    )


def build_policy_receipt(policy: AdapterRegistryPolicy) -> dict:
    # This might return a dict since there's no subject_id in the receipt model for policies
    # but the requirement says "build_policy_receipt".
    # I'll return a dict representation or a receipt if I can link it.
    # The requirement says receipts are for actions on registry entries.
    return {
        "receipt_type": "adapter_registry_policy",
        "client_id": str(policy.client_id),
        "subject_id": str(policy.id),
        "payload_hash": policy.immutable_hash,
        "signature": f"policy_sig_{policy.immutable_hash[:16]}",
        "generated_at": utc_now().isoformat(),
    }


def build_allowlist_receipt(item: AdapterRegistryAllowlistEntry) -> dict:
    return {
        "receipt_type": "adapter_registry_allowlist",
        "client_id": str(item.client_id),
        "subject_id": str(item.id),
        "payload_hash": item.immutable_hash,
        "signature": f"allow_sig_{item.immutable_hash[:16]}",
        "generated_at": utc_now().isoformat(),
    }


def build_blocklist_receipt(item: AdapterRegistryBlocklistEntry) -> dict:
    return {
        "receipt_type": "adapter_registry_blocklist",
        "client_id": str(item.client_id),
        "subject_id": str(item.id),
        "payload_hash": item.immutable_hash,
        "signature": f"block_sig_{item.immutable_hash[:16]}",
        "generated_at": utc_now().isoformat(),
    }
