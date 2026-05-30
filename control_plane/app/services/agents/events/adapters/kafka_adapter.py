# Owner: agent-platform
import logging
from typing import Dict, Any, Callable, Awaitable
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class KafkaAdapter:
    """
    Adapter for Kafka event triggering.
    """
    def __init__(self):
        self.settings = get_settings()

    async def start_consumer(self, topic: str, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        if not self.settings.kafka_trigger_enabled:
            logger.warning("Kafka trigger is disabled. Skipping consumer start.")
            return

        logger.info(f"Starting Kafka consumer for topic: {topic}")
        # Simulated consumer loop
        # In real life: from aiokafka import AIOKafkaConsumer
        pass

    async def stop_consumer(self):
        pass
