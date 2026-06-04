import asyncio
import json
import logging

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.agents.events.event_bus import event_bus
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

async def start_pubsub_listener():
    """
    Listens for messages on Redis streams and publishes them to the internal EventBus.
    """
    settings = get_settings()
    if not settings.agent_event_driven_enabled or not settings.agent_pubsub_triggers_enabled:
        logger.info("Pub/Sub triggers or Event-driven execution is disabled. Listener will not run.")
        return

    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    stream_name = "agent_events_stream"
    group_name = "agent_event_processors"
    consumer_name = f"processor-{id(asyncio.get_event_loop())}"

    # Ensure group exists
    try:
        await redis.xgroup_create(stream_name, group_name, mkstream=True)
    except Exception:
        # Group might already exist
        pass

    logger.info(f"Started Pub/Sub listener on stream: {stream_name}")

    while True:
        try:
            # Read from stream
            messages = await redis.xreadgroup(group_name, consumer_name, {stream_name: ">"}, count=10, block=5000)
            
            if not messages:
                continue

            async with SessionLocal() as db:
                for stream, msg_list in messages:
                    for msg_id, payload in msg_list:
                        # Payload is a dict from Redis stream
                        event_type = payload.get("event_type", "unknown")
                        tenant_id = payload.get("tenant_id", "default")
                        
                        # Data might be json encoded in a 'data' field
                        event_data = payload.get("data", "{}")
                        if isinstance(event_data, str):
                            try:
                                event_data = json.loads(event_data)
                            except:
                                event_data = {"raw": event_data}
                        
                        await event_bus.publish(db, event_type, event_data, tenant_id)
                        
                        # Acknowledge message
                        await redis.xack(stream_name, group_name, msg_id)
                        
                await db.commit()
                
        except Exception as e:
            logger.error(f"Error in pubsub_listener loop: {e}")
            await asyncio.sleep(5)
