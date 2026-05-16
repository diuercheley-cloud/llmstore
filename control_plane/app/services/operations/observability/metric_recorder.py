from app.services.governance.data_governance.data_minimization_checker import check_payload_for_sensitive_keys
from app.services.governance.policy_engine.policy_parser import hash_payload


def build_metric_hash(client_id: str, metric_name: str, metric_scope: str, metric_value: str) -> str:
    return hash_payload(
        {
            "client_id": client_id,
            "metric_name": metric_name,
            "metric_scope": metric_scope,
            "metric_value": metric_value,
        }
    )


def validate_metric_payload(payload: dict) -> list[str]:
    return check_payload_for_sensitive_keys(payload)

