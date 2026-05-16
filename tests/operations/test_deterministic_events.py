from app.services.operations.events.event_lineage import build_lineage
from app.services.operations.events.event_recorder import build_event_hash
from app.services.operations.events.event_replay_verifier import verify_event_replay


def test_deterministic_event_hash_replays_cleanly():
    payload = {
        "client_id": "tenant-1",
        "event_name": "workflow.approved",
        "event_version": "1.0",
        "subject_type": "workflow",
        "subject_ref": "wf-1",
        "previous_event_hash": None,
    }
    event_hash = build_event_hash(**payload)
    result = verify_event_replay(payload, event_hash)
    assert result["verification_status"] == "passed"


def test_event_lineage_preserves_order():
    lineage = build_lineage([{"event_hash": "a"}, {"event_hash": "b"}])
    assert lineage == ["a", "b"]

