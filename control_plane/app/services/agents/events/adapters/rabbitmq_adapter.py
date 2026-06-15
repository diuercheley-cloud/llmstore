# Owner: agent-platform
import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

try:
    from aio_pika import IncomingMessage, Message, connect_robust
    from aio_pika.abc import AbstractIncomingMessage

    HAS_RABBITMQ = True
except ImportError:
    HAS_RABBITMQ = False
    logger.info("aio-pika not installed; RabbitMQ adapter will use simulated mode")


class RabbitMQAdapter:
    """
    Adapter for RabbitMQ event triggering.
    Supports both real (aio-pika) and simulated modes.
    """

    def __init__(self):
        self.settings = get_settings()
        self._connection = None
        self._channel = None
        self._queue = None
        self._running = False
        self._task: asyncio.Task | None = None
        self._callback: Callable[[dict[str, Any]], Awaitable[None]] | None = None

    def _is_enabled(self) -> bool:
        return getattr(
            self.settings,
            "rabbitmq_trigger_enabled",
            getattr(self.settings, "agent_event_driven_enabled", False),
        )

    async def start_consumer(
        self, queue: str, callback: Callable[[dict[str, Any]], Awaitable[None]]
    ):
        if not self._is_enabled():
            logger.warning("RabbitMQ trigger is disabled. Skipping consumer start.")
            return

        self._callback = callback
        self._running = True

        if HAS_RABBITMQ:
            amqp_url = getattr(self.settings, "rabbitmq_url", "amqp://guest:guest@localhost:5672/")
            self._connection = await connect_robust(amqp_url)
            self._channel = await self._connection.channel()
            self._queue = await self._channel.declare_queue(queue, durable=True)
            self._task = asyncio.create_task(self._consume_loop())
            logger.info(f"RabbitMQ consumer started for queue: {queue}")
        else:
            logger.info(f"RabbitMQ consumer started in simulated mode for queue: {queue}")

    async def _consume_loop(self):
        async with self._queue.iterator() as queue_iter:
            async for message in queue_iter:
                if not self._running:
                    break
                async with message.process(requeue=True):
                    try:
                        body = json.loads(message.body.decode("utf-8"))
                        await self._callback(body)
                    except Exception as e:
                        logger.error(f"RabbitMQ callback error: {e}")

    async def stop_consumer(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._connection:
            await self._connection.close()
            self._connection = None
        logger.info("RabbitMQ consumer stopped")
