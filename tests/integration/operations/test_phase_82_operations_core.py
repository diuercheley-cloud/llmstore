from app.services.operations.events.event_recorder import build_event_hash
from app.services.operations.observability.timeline_builder import build_timeline_hash


def test_phase_82_operations_core_hashes_are_deterministic():
    event_hash = build_event_hash("tenant", "ops.event", "1.0", "workflow", "wf-1", None)
    assert event_hash == build_event_hash("tenant", "ops.event", "1.0", "workflow", "wf-1", None)
    timeline_hash = build_timeline_hash("tenant", "ops", "control", [event_hash])
    assert timeline_hash == build_timeline_hash("tenant", "ops", "control", [event_hash])
