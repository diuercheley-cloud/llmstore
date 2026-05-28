"""
Owner: agent-platform
Status: beta
"""
import asyncio
import logging
import uuid
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.core.config import get_settings
from app.core.time import utc_now
from app.db.session import SessionLocal
from app.services.agents.events.cron_triggers import check_and_fire_schedules
from app.models.agent_execution import AgentWorkerHeartbeat # Re-using worker heartbeats for simple leader election or just use row-level locking on triggers

logger = logging.getLogger(__name__)

class AgentScheduler:
    """
    Secure and Durable Scheduler for Agent Runs.
    Manages cron triggers and scheduled tasks for agents.
    Ensures single-instance execution using row-level locking on triggers.
    """
    def __init__(self, poll_interval: int = 30):
        self.poll_interval = poll_interval
        self.settings = get_settings()
        self.is_running = False
        self._main_task = None

    async def start(self):
        if not self.settings.agent_execution_plane_enabled:
            logger.warning("Agent Execution Plane is disabled. AgentScheduler will not start.")
            return

        if not self.settings.agent_cron_triggers_enabled:
            logger.info("Agent Cron Triggers disabled. AgentScheduler not starting.")
            return

        self.is_running = True
        logger.info("Starting Agent Scheduler...")
        self._main_task = asyncio.create_task(self._scheduler_loop())

    async def stop(self):
        self.is_running = False
        if self._main_task:
            self._main_task.cancel()
        logger.info("Stopped Agent Scheduler.")

    async def _scheduler_loop(self):
        while self.is_running:
            try:
                async with SessionLocal() as db:
                    # check_and_fire_schedules should use row-level locking (SELECT FOR UPDATE SKIP LOCKED)
                    # to ensure multiple scheduler instances don't fire the same trigger.
                    await check_and_fire_schedules(db)
                    await db.commit()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Error in Agent Scheduler loop")
            
            await asyncio.sleep(self.poll_interval)

    async def run_once(self):
        """Used for manual triggering or tests."""
        async with SessionLocal() as db:
            await check_and_fire_schedules(db)
            await db.commit()
