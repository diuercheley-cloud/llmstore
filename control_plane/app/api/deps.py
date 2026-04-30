from functools import lru_cache

from app.services.backend_slot_manager import BackendSlotManager
from app.services.circuit_breaker import CircuitBreaker
from app.services.inference_proxy import InferenceProxy
from app.services.queue_manager import QueueManager


@lru_cache
def get_queue_manager() -> QueueManager:
    return QueueManager(get_backend_slot_manager())


@lru_cache
def get_backend_slot_manager() -> BackendSlotManager:
    return BackendSlotManager()


@lru_cache
def get_circuit_breaker() -> CircuitBreaker:
    return CircuitBreaker()


@lru_cache
def get_inference_proxy() -> InferenceProxy:
    return InferenceProxy(get_queue_manager(), get_circuit_breaker())
