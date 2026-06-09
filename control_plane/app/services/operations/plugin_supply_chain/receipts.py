from datetime import datetime
from typing import Any

from app.core.time import utc_now
from app.models.operations.plugin_supply_chain import PluginSupplyChainReceipt
from app.services.operations.plugin_supply_chain.hash_utils import sha256_hex


def build_supply_chain_receipt(
    receipt_type: str,
    provenance_record: Any,
    payload_hash: str,
    signature_scope: str = "provenance_record",
) -> PluginSupplyChainReceipt:
    generated_at = utc_now()
    logical_payload = {
        "receipt_type": receipt_type,
        "client_id": str(provenance_record.client_id),
        "provenance_record_id": provenance_record.id,
        "payload_hash": payload_hash,
        "signature_scope": signature_scope,
    }
    from app.core.config import get_settings
    from app.services.inference.cryptographic_receipts import sign_payload
    is_prod = get_settings().app_env == "production"
    if is_prod:
        signature = sign_payload(payload_hash)
    else:
        signature = sign_payload(f"{receipt_type}:{payload_hash[:16]}")
        
    receipt = PluginSupplyChainReceipt(
        id=sha256_hex({"kind": "plugin_supply_chain_receipt_id", **logical_payload}),
        client_id=provenance_record.client_id,
        provenance_record_id=provenance_record.id,
        receipt_type=receipt_type,
        payload_hash=payload_hash,
        immutable_hash=sha256_hex({"kind": "plugin_supply_chain_receipt_immutable", **logical_payload}),
        signature=signature,
        generated_at=generated_at if isinstance(generated_at, datetime) else utc_now(),
    )
    receipt._logical_payload = logical_payload
    return receipt
