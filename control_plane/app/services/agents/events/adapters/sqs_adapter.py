# Owner: agent-platform
import logging
from typing import Dict, Any, Callable, Awaitable
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class SQSAdapter:
    """
    Adapter for AWS SQS event triggering.
    """
    def __init__(self):
        self.settings = get_settings()

    async def start_consumer(self, queue_url: str, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        if not self.settings.sqs_trigger_enabled:
            logger.warning("SQS trigger is disabled. Skipping consumer start.")
            return

        logger.info(f"Starting SQS consumer for queue: {queue_url}")
        # Simulated consumer loop
        # In real life: import aioboto3
        pass

    async def stop_consumer(self):
        pass
