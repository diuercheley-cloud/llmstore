from app.services.governance.policy_engine.policy_parser import hash_payload


def build_bundle_hash(policy_hashes: list[str]) -> str:
    return hash_payload({"policy_hashes": sorted(policy_hashes)})

