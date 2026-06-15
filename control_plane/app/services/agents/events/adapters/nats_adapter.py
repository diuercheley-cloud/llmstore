import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

try:
    import nats
    from nats.errors import ConnectionClosedError, TimeoutError

    HAS_NATS = True
except ImportError:
    HAS_NATS = False


class NATSAdapter:
    """
    Adapter for NATS event triggering.
    Supports both real (nats-py) and simulated modes.
    """

    def __init__(self):
        self.settings = get_settings()
        self._nc: Any | None = None
        self._sub: Any | None = None
        self._running = False
        self._task: asyncio.Task | None = None
        self._callback: Callable[[dict[str, Any]], Awaitable[None]] | None = None

    def _is_enabled(self) -> bool:
        return getattr(
            self.settings,
            "nats_trigger_enabled",
            getattr(self.settings, "agent_event_driven_enabled", False),
        )

    async def start_consumer(
        self, subject: str, callback: Callable[[dict[str, Any]], Awaitable[None]]
    ):
        if not self._is_enabled():
            logger.warning("NATS trigger is disabled. Skipping consumer start.")
            return

        self._callback = callback
        self._running = True

        if HAS_NATS:
            nats_url = getattr(self.settings, "nats_url", "nats://localhost:4222")
            try:
                self._nc = await nats.connect(nats_url)
                self._sub = await self._nc.subscribe(subject)
                self._task = asyncio.create_task(self._consume_loop())
                logger.info(f"NATS consumer started for subject: {subject}")
            except Exception as e:
                logger.error(f"NATS connection failed: {e}")
                logger.info(f"NATS consumer started in simulated mode for subject: {subject}")
        else:
            logger.info(f"NATS consumer started in simulated mode for subject: {subject}")

    async def _consume_loop(self):
        async for msg in self._sub:
            if not self._running:
                break
            try:
                body = json.loads(msg.data.decode("utf-8"))
                await self._callback(body)
            except Exception as e:
                logger.error(f"NATS callback error: {e}")

    async def stop_consumer(self):
        self._running = False
        if self._sub:
            await self._sub.unsubscribe()
            self._sub = None
        if self._nc:
            await self._nc.close()
            self._nc = None
        logger.info("NATS consumer stopped")

    async def publish(self, subject: str, data: dict[str, Any]):
        if self._nc:
            await self._nc.publish(subject, json.dumps(data).encode("utf-8"))
        else:
            logger.info(f"NATS simulated publish to {subject}: {data}")
