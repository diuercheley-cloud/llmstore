from app.services.governance.policy_engine.policy_parser import hash_payload


def build_lineage_hash(client_id: str, source_ref: str, target_ref: str) -> str:
    return hash_payload({"client_id": client_id, "source_ref": source_ref, "target_ref": target_ref})

