import asyncio
import logging
from contextlib import asynccontextmanager

from app.api.deps import get_inference_proxy
from app.core.config import get_settings
from app.db.session import SessionLocal, engine, redis_client
from app.services.agents.tool_adapters import register_all_adapters
from app.services.billing_scheduler import billing_scheduler_loop
from app.services.models.runtime_integrity_monitor import (
    runtime_integrity_monitor_loop,
    scan_registered_models,
)
from app.services.routing.commercial_federation import sync_federation_clusters
from app.services.routing.commercial_node_heartbeat import commercial_distributed_analytics_loop
from app.services.routing.commercial_report_scheduler import commercial_report_scheduler_loop
from app.services.seed import seed_defaults
from fastapi import FastAPI

logger = logging.getLogger(__name__)
settings = get_settings()


def _flag(name: str, default: bool = False) -> bool:
    return bool(getattr(settings, name, default))


async def sync_federation_clusters_loop(stop_event: asyncio.Event) -> None:
    if not settings.commercial_federation_enabled:
        return
    while not stop_event.is_set():
        try:
            async with SessionLocal() as session:
                await sync_federation_clusters(session, sync_type="scheduled", settings=settings)
                await session.commit()
        except Exception as exc:
            logging.getLogger(__name__).exception(
                "federation sync loop failed", extra={"extra_data": {"error": str(exc)}}
            )
        try:
            await asyncio.wait_for(
                stop_event.wait(), timeout=settings.commercial_federation_sync_interval_seconds
            )
        except TimeoutError:
            continue


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Initialize Tool Adapters
    if _flag("agent_runtime_enabled") or _flag("agent_tool_adapters_enabled"):
        register_all_adapters()

    if getattr(settings, "create_tables_on_startup", False):
        from app.db.base import Base

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        try:
            await seed_defaults(session)
        except Exception as exc:
            logger.warning("Seed defaults skipped during startup: %s", exc)
        if _flag("commercial_model_integrity_monitor_enabled") and _flag(
            "commercial_model_integrity_boot_scan_enabled"
        ):
            try:
                await scan_registered_models(session)
            except Exception as exc:
                logger.warning("Model integrity boot scan skipped during startup: %s", exc)

    # Agent Embedded Worker (dev mode only, off by default)
    agent_worker_task = None
    if _flag("agent_embedded_worker_enabled") and _flag("agent_worker_enabled"):
        from app.services.agents.agent_worker import AgentWorkerService

        embedded_worker = AgentWorkerService(worker_id="embedded-dev")
        agent_worker_task = asyncio.create_task(embedded_worker.start())
        logger.info("Embedded agent worker started (AGENT_EMBEDDED_WORKER_ENABLED=true)")

    # Workflow Scheduler
    workflow_scheduler_task = None
    if _flag("agent_stateful_workflows_enabled"):
        from app.services.agents.workflows.workflow_scheduler import WorkflowScheduler

        scheduler = WorkflowScheduler()
        workflow_scheduler_task = asyncio.create_task(scheduler.start())
        logger.info("Stateful Workflow Scheduler started")

    # Agent Event-Driven Background Tasks
    cron_task = None
    pubsub_task = None
    if _flag("agent_event_driven_enabled"):
        if _flag("agent_cron_triggers_enabled"):
            from app.services.agents.events.cron_triggers import evaluate_schedules

            cron_task = asyncio.create_task(evaluate_schedules())
            logger.info("Agent Cron Trigger Service started")

        if _flag("agent_pubsub_triggers_enabled"):
            from app.services.agents.events.pubsub_triggers import start_pubsub_listener

            pubsub_task = asyncio.create_task(start_pubsub_listener())
            logger.info("Agent Pub/Sub Listener started")

    stop_event = asyncio.Event()
    billing_task = asyncio.create_task(billing_scheduler_loop(stop_event))
    analytics_task = asyncio.create_task(commercial_distributed_analytics_loop(stop_event))
    federation_task = asyncio.create_task(sync_federation_clusters_loop(stop_event))
    report_task = asyncio.create_task(commercial_report_scheduler_loop(stop_event))
    integrity_task = asyncio.create_task(runtime_integrity_monitor_loop(stop_event))

    yield

    stop_event.set()
    if agent_worker_task:
        agent_worker_task.cancel()
    if workflow_scheduler_task:
        workflow_scheduler_task.cancel()
    if cron_task:
        cron_task.cancel()
    if pubsub_task:
        pubsub_task.cancel()
    billing_task.cancel()
    analytics_task.cancel()
    federation_task.cancel()
    report_task.cancel()
    integrity_task.cancel()

    try:
        await billing_task
    except asyncio.CancelledError:
        pass
    try:
        await analytics_task
    except asyncio.CancelledError:
        pass
    try:
        await report_task
    except asyncio.CancelledError:
        pass
    try:
        await federation_task
    except asyncio.CancelledError:
        pass
    try:
        await integrity_task
    except asyncio.CancelledError:
        pass
    await get_inference_proxy().close()
    await redis_client.aclose()
    await engine.dispose()
