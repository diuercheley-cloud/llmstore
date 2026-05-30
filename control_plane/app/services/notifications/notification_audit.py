import json
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class NotificationAuditService:
    @classmethod
    def generate_receipt(
        cls,
        tenant_id: str,
        run_id: Optional[str],
        channel: str,
        recipient: str,
        title: str,
        body: str,
        status: str,
        additional_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generates a cryptographic audit receipt and hash for a notification dispatch."""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Calculate SHA256 of message content
        content_payload = f"{title}|||{body}"
        content_hash = hashlib.sha256(content_payload.encode("utf-8")).hexdigest()

        receipt_body = {
            "tenant_id": tenant_id,
            "run_id": run_id or "none",
            "channel": channel,
            "recipient": recipient,
            "content_hash": content_hash,
            "status": status,
            "timestamp": timestamp,
            "additional_info": additional_info or {}
        }

        # Compute signature of receipt body
        serialized = json.dumps(receipt_body, sort_keys=True)
        receipt_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        signature = f"notif_receipt_sig_{receipt_hash[:16]}"

        return {
            "audit_hash": receipt_hash,
            "signature": signature,
            "receipt": receipt_body
        }
