import hashlib
import json
from datetime import UTC, datetime
from typing import Any


class ReleaseReceiptService:
    def generate_receipt(
        self, baseline_id: str, receipt_type: str, manifest: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Generates a release receipt.
        """
        payload = {
            "baseline_id": baseline_id,
            "manifest_hash": manifest["manifest_hash"],
            "version": manifest["version"],
            "timestamp": manifest["timestamp"],
        }

        payload_json = json.dumps(payload, sort_keys=True)
        payload_hash = hashlib.sha256(payload_json.encode()).hexdigest()

        receipt = {
            "baseline_id": baseline_id,
            "receipt_type": receipt_type,
            "payload_hash": payload_hash,
            "immutable_hash": hashlib.sha256((payload_hash + receipt_type).encode()).hexdigest(),
            "signature": "[OFFLINE_GOVERNANCE_SIGNATURE_PENDING]",
            "generated_at": datetime.now(UTC).isoformat(),
        }

        return receipt

    def verify_receipt(self, receipt: dict[str, Any], payload: dict[str, Any]) -> bool:
        """
        Verifies a release receipt against its payload.
        """
        payload_json = json.dumps(payload, sort_keys=True)
        payload_hash = hashlib.sha256(payload_json.encode()).hexdigest()

        return receipt["payload_hash"] == payload_hash
