# Owner: agent-platform
import logging
from typing import Dict, Any, Callable, Awaitable
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class RabbitMQAdapter:
    """
    Adapter for RabbitMQ event triggering.
    """
    def __init__(self):
        self.settings = get_settings()

    async def start_consumer(self, queue: str, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        if not self.settings.rabbitmq_trigger_enabled:
            logger.warning("RabbitMQ trigger is disabled. Skipping consumer start.")
            return

        logger.info(f"Starting RabbitMQ consumer for queue: {queue}")
        # Simulated consumer loop
        # In real life: import aio_pika
        pass

    async def stop_consumer(self):
        pass
