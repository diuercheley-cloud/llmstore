from app.services.operations.disaster_recovery.recovery_plan_service import build_recovery_hash
from app.services.operations.disaster_recovery.recovery_replay_verifier import verify_recovery_replay


def test_disaster_recovery_is_dry_run_replay_safe():
    payload = {
        "client_id": "tenant-1",
        "recovery_scope": "control-plane",
        "recovery_strategy": "manifest_replay",
        "dry_run": True,
    }
    recovery_hash = build_recovery_hash(**payload)
    result = verify_recovery_replay(payload, recovery_hash)
    assert result["verification_status"] == "passed"
    assert result["replay_safe"] is True
