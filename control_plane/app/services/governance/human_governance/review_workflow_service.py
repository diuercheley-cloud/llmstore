from app.services.governance.policy_engine.policy_parser import hash_payload


def build_workflow_hash(client_id: str, workflow_name: str, subject_type: str, subject_ref: str, workflow_status: str) -> str:
    return hash_payload(
        {
            "client_id": client_id,
            "workflow_name": workflow_name,
            "subject_type": subject_type,
            "subject_ref": subject_ref,
            "workflow_status": workflow_status,
        }
    )

