# Owner: agent-platform
import asyncio
import logging

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.agents.workflows.workflow_engine import WorkflowEngine
from app.services.agents.workflows.workflow_timers import WorkflowTimerManager

logger = logging.getLogger(__name__)

class WorkflowScheduler:
    """
    Background scheduler that wakes up workflows.
    """
    def __init__(self, poll_interval: int = 5):
        self.poll_interval = poll_interval
        self.settings = get_settings()

    async def start(self):
        if not self.settings.agent_stateful_workflows_enabled:
            logger.info("Stateful workflows disabled. Scheduler not starting.")
            return

        logger.info("Starting Workflow Scheduler...")
        while True:
            try:
                async with SessionLocal() as db:
                    engine = WorkflowEngine(db)
                    timers = WorkflowTimerManager(db)
                    
                    # 1. Fire timers
                    fired_timers = await timers.get_fired_timers()
                    for timer in fired_timers:
                        logger.info(f"Firing timer {timer.timer_name} for run {timer.run_id}")
                        await engine.signal_run(timer.run_id, f"timer_{timer.timer_name}", {})
                        await timers.mark_fired(timer.id)
                    
                    # 2. Process ready runs
                    await engine.process_ready_runs()
                    
            except Exception:
                logger.exception("Error in Workflow Scheduler loop")
            
            await asyncio.sleep(self.poll_interval)
