import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class ConnectorAuditLog:
    """
    Handles auditing for SaaS Connector actions.
    """
    @staticmethod
    def log_action(
        tenant_id: str,
        connector_name: str,
        action: str,
        request_params: Dict[str, Any],
        response: Dict[str, Any],
        risk_level: str,
        is_dry_run: bool = False,
        status: str = "success"
    ) -> str:
        invocation_id = str(uuid.uuid4())
        
        audit_event = {
            "invocation_id": invocation_id,
            "timestamp": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id,
            "connector": connector_name,
            "action": action,
            "risk_level": risk_level,
            "is_dry_run": is_dry_run,
            "status": status,
            # We explicitly redact sensitive info if it were present in request_params
            "request_summary": {k: v for k, v in request_params.items() if "token" not in k.lower() and "secret" not in k.lower()},
            "response_summary": {k: v for k, v in response.items() if "token" not in k.lower() and "secret" not in k.lower()}
        }
        
        # Log to structural logger
        logger.info(f"CONNECTOR_AUDIT: {audit_event}")
        
        return invocation_id

connector_audit = ConnectorAuditLog()
