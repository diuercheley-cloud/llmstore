from unittest.mock import MagicMock

from app.services.queue_manager import QueueManager


def test_plan_to_queue_name():
    qm = QueueManager(MagicMock())
    # Standard mapping
    assert qm._resolve_queue_name("free") == "inference_free"
    assert qm._resolve_queue_name("basic") == "inference_basic"
    assert qm._resolve_queue_name("pro") == "inference_premium"
    assert qm._resolve_queue_name("enterprise") == "inference_premium"

    # Admin mapping
    assert qm._resolve_queue_name("free", is_admin=True) == "inference_admin"
    assert qm._resolve_queue_name("enterprise", is_admin=True) == "inference_admin"

    # Default to free
    assert qm._resolve_queue_name("unknown-plan") == "inference_free"
    assert qm._resolve_queue_name(None) == "inference_free"


def test_queue_config_loaded():
    qm = QueueManager(MagicMock())
    assert "inference_admin" in qm.queues
    assert "inference_premium" in qm.queues
    assert "inference_basic" in qm.queues
    assert "inference_free" in qm.queues

    assert qm.queues["inference_admin"]["priority"] == 0
    assert qm.queues["inference_free"]["priority"] == 3
