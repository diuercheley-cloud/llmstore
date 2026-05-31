# Owner: agent-platform
import asyncio
import json
import logging
from typing import Dict, Any, Callable, Awaitable, Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)

try:
    from aiokafka import AIOKafkaConsumer
    HAS_KAFKA = True
except ImportError:
    HAS_KAFKA = False
    logger.info("aiokafka not installed; Kafka adapter will use simulated mode")


class KafkaAdapter:
    """
    Adapter for Kafka event triggering.
    Supports both real (aiokafka) and simulated modes.
    """
    def __init__(self):
        self.settings = get_settings()
        self._consumer: Optional[Any] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None

    def _is_enabled(self) -> bool:
        return getattr(self.settings, 'kafka_trigger_enabled',
                       getattr(self.settings, 'agent_event_driven_enabled', False))

    async def start_consumer(self, topic: str, callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        if not self._is_enabled():
            logger.warning("Kafka trigger is disabled. Skipping consumer start.")
            return

        self._callback = callback
        self._running = True

        if HAS_KAFKA:
            bootstrap = getattr(self.settings, 'kafka_bootstrap_servers', 'localhost:9092')
            group_id = getattr(self.settings, 'kafka_group_id', 'agent-platform')

            self._consumer = AIOKafkaConsumer(
                topic,
                bootstrap_servers=bootstrap,
                group_id=group_id,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                enable_auto_commit=True,
            )
            await self._consumer.start()
            self._task = asyncio.create_task(self._consume_loop())
            logger.info(f"Kafka consumer started for topic: {topic} (bootstrap: {bootstrap})")
        else:
            logger.info(f"Kafka consumer started in simulated mode for topic: {topic}")

    async def _consume_loop(self):
        try:
            async for msg in self._consumer:
                if not self._running:
                    break
                try:
                    await self._callback(msg.value)
                except Exception as e:
                    logger.error(f"Kafka callback error: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Kafka consumer loop error: {e}")
        finally:
            logger.info("Kafka consumer loop ended")

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
            await self._consumer.stop()
            self._consumer = None
        logger.info("Kafka consumer stopped")
