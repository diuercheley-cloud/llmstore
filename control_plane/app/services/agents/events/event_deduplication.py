import hashlib
import logging
from datetime import timedelta
from typing import Any

from app.core.time import utc_now
from app.models.agents.agent_events import AgentEventDedupKey
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def is_duplicate(db: AsyncSession, event_id: str, ttl_minutes: int = 60) -> bool:
    """
    Checks if an event_id has already been processed within the TTL window.
    """
    if not event_id:
        return False

    # Clean up expired keys first (simple opportunistic cleanup)
    # In production, this might be a background task
    now = utc_now()
    cleanup_stmt = delete(AgentEventDedupKey).where(AgentEventDedupKey.expires_at <= now)
    await db.execute(cleanup_stmt)

    # Check if key exists
    stmt = select(AgentEventDedupKey).where(AgentEventDedupKey.key == event_id)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        logger.info(f"Duplicate event detected: {event_id}")
        return True

    # Record new key
    expires_at = now + timedelta(minutes=ttl_minutes)
    new_key = AgentEventDedupKey(key=event_id, expires_at=expires_at)
    db.add(new_key)
    # We don't commit here, let the caller decide
    return False


def generate_dedup_key(payload: dict) -> str:
    """
    Generates a deterministic hash from a payload to use as a dedup key if no explicit event ID is provided.
    """
    import json

    serialized = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def sanitize_payload(payload: Any) -> Any:
    """
    Recursively redacts secrets, passwords, tokens, and other credentials from the event payload.
    """
    if isinstance(payload, dict):
        sanitized = {}
        for k, v in payload.items():
            k_lower = k.lower()
            if any(
                secret in k_lower
                for secret in [
                    "secret",
                    "password",
                    "token",
                    "key",
                    "auth",
                    "authorization",
                    "signature",
                    "private",
                ]
            ):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_payload(v)
        return sanitized
    elif isinstance(payload, list):
        return [sanitize_payload(x) for x in payload]
    return payload
