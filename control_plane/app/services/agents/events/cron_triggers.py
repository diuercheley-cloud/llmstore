import logging
import asyncio
import zoneinfo
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agent_events import AgentEventTrigger, AgentScheduledTrigger
from app.services.agents.events.event_triggers import fire_trigger
from app.core.time import utc_now
from app.db.session import SessionLocal
from app.core.config import get_settings

# Optional: try to import croniter, if not available use a placeholder
try:
    from croniter import croniter
except ImportError:
    croniter = None

logger = logging.getLogger(__name__)

async def evaluate_schedules():
    """
    Background task to check for due scheduled triggers.
    """
    settings = get_settings()
    if not settings.agent_event_driven_enabled or not settings.agent_cron_triggers_enabled:
        logger.info("Cron triggers or Event-driven execution is disabled. Scheduler loop will not run.")
        return

    if croniter is None:
        logger.error("croniter not installed. Scheduled triggers will not work.")
        return

    while True:
        try:
            async with SessionLocal() as db:
                await check_and_fire_schedules(db)
            await asyncio.sleep(60) # Check every minute
        except Exception as e:
            logger.error(f"Error in evaluate_schedules loop: {e}")
            await asyncio.sleep(60)

async def check_and_fire_schedules(db: AsyncSession):
    now = utc_now()
    
    # Find all active scheduled triggers that are due
    # Durable Scheduler hardening: Use SELECT FOR UPDATE SKIP LOCKED to prevent double firing
    stmt = (
        select(AgentScheduledTrigger)
        .join(AgentEventTrigger, AgentEventTrigger.id == AgentScheduledTrigger.trigger_id)
        .where(
            AgentEventTrigger.is_paused == False,
            AgentScheduledTrigger.next_run_at <= now
        )
        .with_for_update(skip_locked=True)
    )
    result = await db.execute(stmt)
    schedules = result.scalars().all()
    
    for schedule in schedules:
        logger.info(f"Firing scheduled trigger {schedule.trigger_id} (next_run_at: {schedule.next_run_at})")
        
        # Fire the trigger
        payload = {
            "source": "cron",
            "scheduled_at": schedule.next_run_at.isoformat() if schedule.next_run_at else now.isoformat(),
            "fired_at": now.isoformat()
        }
        await fire_trigger(db, schedule.trigger_id, payload)
        
        # Calculate next run time
        next_run = calculate_next_run(schedule.cron_expression, now, schedule.timezone)
        schedule.next_run_at = next_run
        
    await db.commit()

def calculate_next_run(cron_expression: str, start_time: datetime, timezone_str: str = "UTC") -> datetime:
    """
    Calculates the next run time for a cron expression using the specified timezone,
    returning a UTC datetime.
    """
    if croniter is None:
        return start_time + timedelta(days=365) # Fallback
        
    try:
        tz = zoneinfo.ZoneInfo(timezone_str)
    except Exception:
        logger.warning(f"Invalid timezone: {timezone_str}, falling back to UTC")
        tz = zoneinfo.ZoneInfo("UTC")
        
    # Convert start_time to the target timezone
    local_start = start_time.astimezone(tz)
    
    iter = croniter(cron_expression, local_start)
    next_local = iter.get_next(datetime)
    
    # Convert back to UTC for standard storage
    return next_local.astimezone(zoneinfo.ZoneInfo("UTC"))
