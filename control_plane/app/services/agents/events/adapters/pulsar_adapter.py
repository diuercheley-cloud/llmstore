import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

try:
    from pulsar import Client as PulsarClient
    from pulsar.schema import BytesSchema

    HAS_PULSAR = True
except ImportError:
    HAS_PULSAR = False


class PulsarAdapter:
    """
    Adapter for Apache Pulsar event triggering.
    Supports both real (pulsar-client) and simulated modes.
    """

    def __init__(self):
        self.settings = get_settings()
        self._client: Any | None = None
        self._consumer: Any | None = None
        self._running = False
        self._task: asyncio.Task | None = None
        self._callback: Callable[[dict[str, Any]], Awaitable[None]] | None = None

    def _is_enabled(self) -> bool:
        return getattr(
            self.settings,
            "pulsar_trigger_enabled",
            getattr(self.settings, "agent_event_driven_enabled", False),
        )

    async def start_consumer(
        self, topic: str, subscription: str, callback: Callable[[dict[str, Any]], Awaitable[None]]
    ):
        if not self._is_enabled():
            logger.warning("Pulsar trigger is disabled. Skipping consumer start.")
            return

        self._callback = callback
        self._running = True

        if HAS_PULSAR:
            pulsar_url = getattr(self.settings, "pulsar_url", "pulsar://localhost:6650")
            try:
                self._client = PulsarClient(pulsar_url)
                self._consumer = self._client.subscribe(
                    topic,
                    subscription_name=subscription,
                    schema=BytesSchema(),
                )
                self._task = asyncio.create_task(self._consume_loop())
                logger.info(
                    f"Pulsar consumer started for topic: {topic}, subscription: {subscription}"
                )
            except Exception as e:
                logger.error(f"Pulsar connection failed: {e}")
                logger.info(f"Pulsar consumer started in simulated mode for topic: {topic}")
        else:
            logger.info(f"Pulsar consumer started in simulated mode for topic: {topic}")

    async def _consume_loop(self):
        while self._running:
            try:
                msg = self._consumer.receive(timeout_millis=5000)
                if msg:
                    body = json.loads(msg.data().decode("utf-8"))
                    await self._callback(body)
                    self._consumer.acknowledge(msg)
            except Exception as e:
                if "timeout" not in str(e).lower():
                    logger.error(f"Pulsar receive error: {e}")
                await asyncio.sleep(0.1)

    async def stop_consumer(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._consumer:
            self._consumer.close()
            self._consumer = None
        if self._client:
            self._client.close()
            self._client = None
        logger.info("Pulsar consumer stopped")
