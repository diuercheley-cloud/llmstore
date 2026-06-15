from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ActiveInjection:
    def __init__(self, injection_type: str, config: dict[str, Any]):
        self.injection_type = injection_type
        self.config = config


class ChaosInjectionRegistry:
    _instance = None
    _injections: list[ActiveInjection] = []

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def add_injection(self, injection_type: str, config: dict[str, Any]):
        self._injections.append(ActiveInjection(injection_type, config))
        logger.warning(f"CHAOS INJECTION ACTIVATED: {injection_type} with {config}")

    def clear_injections(self):
        self._injections = []
        logger.info("All chaos injections cleared.")

    def get_injections_by_type(self, injection_type: str) -> list[ActiveInjection]:
        return [i for i in self._injections if i.injection_type == injection_type]


async def inject_chaos(injection_type: str):
    settings = get_settings()
    if not settings.chaos_enabled:
        return

    registry = ChaosInjectionRegistry.get_instance()
    injections = registry.get_injections_by_type(injection_type)

    for inj in injections:
        ratio = inj.config.get("ratio", 1.0)
        if random.random() > ratio:
            continue

        if injection_type == "data_plane_latency":
            latency_ms = inj.config.get("latency_ms", 0)
            if latency_ms > 0:
                logger.warning(f"CHAOS: Injecting {latency_ms}ms latency")
                await asyncio.sleep(latency_ms / 1000.0)

        elif injection_type == "provider_timeout":
            timeout = inj.config.get("timeout", 30)
            logger.warning(f"CHAOS: Simulating provider timeout ({timeout}s)")
            await asyncio.sleep(timeout)
            raise TimeoutError("Simulated chaos timeout")

        elif injection_type == "redis_failure":
            logger.warning("CHAOS: Simulating Redis failure")
            raise ConnectionError("Simulated chaos Redis connection failure")

        elif injection_type == "db_outage":
            logger.warning("CHAOS: Simulating DB outage")
            raise RuntimeError("Simulated chaos Database outage")


async def inject_chaos_db():
    await inject_chaos("db_outage")
