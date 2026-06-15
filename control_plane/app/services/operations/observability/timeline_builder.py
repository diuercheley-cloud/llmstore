from app.services.governance.policy_engine.policy_parser import hash_payload


def build_timeline_hash(
    client_id: str, timeline_name: str, timeline_scope: str, item_hashes: list[str]
) -> str:
    return hash_payload(
        {
            "client_id": client_id,
            "timeline_name": timeline_name,
            "timeline_scope": timeline_scope,
            "item_hashes": sorted(item_hashes),
        }
    )
