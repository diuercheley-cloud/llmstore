from app.services.governance.policy_engine.policy_parser import hash_payload


def build_trace_hash(client_id: str, trace_name: str, trace_scope: str, subject_ref: str) -> str:
    return hash_payload(
        {
            "client_id": client_id,
            "trace_name": trace_name,
            "trace_scope": trace_scope,
            "subject_ref": subject_ref,
        }
    )
