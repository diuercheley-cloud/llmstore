import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.contracts.event import EventContract, PlatformEvent, EventCapabilities
from app.services.security_monitor import log_security_event, list_security_events, serialize_security_event

logger = logging.getLogger(__name__)

class EventService(EventContract):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_event(self, event: PlatformEvent) -> bool:
        try:
            await log_security_event(
                self.db,
                event_type=event.event_type,
                severity=event.severity,
                title=event.title,
                client_id=event.client_id,
                request_log_id=event.request_id,
                details=event.details
            )
            return True
        except Exception as e:
            logger.error(f"Failed to log event: {e}")
            return False

    async def list_events(self, limit: int = 100) -> List[PlatformEvent]:
        events = await list_security_events(self.db)
        return [
            PlatformEvent(
                event_type=e["event_type"],
                severity=e["severity"],
                title=e["title"],
                details=e["details"],
                timestamp=e["created_at"],
                client_id=e["client_id"],
                request_id=e["request_log_id"]
            )
            for e in events[:limit]
        ]

    def capabilities(self) -> EventCapabilities:
        return EventCapabilities(
            async_logging=True,
            persistence=True,
            realtime_streaming=False
        )

    def validate_contract(self) -> bool:
        return True
