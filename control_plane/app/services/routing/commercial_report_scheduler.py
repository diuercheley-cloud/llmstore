from __future__ import annotations

import asyncio
import logging
import uuid

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.routing.commercial_auto_apply import CommercialAutoApplyService
from app.services.routing.commercial_calibration import generate_calibration_report
from app.services.routing.commercial_canary_promotion import CommercialCanaryPromotionService
from app.services.routing.commercial_leader_election import (
    renew_leader_lease,
    try_acquire_leader,
    validate_fencing_token,
)
from app.services.routing.commercial_node_heartbeat import resolve_node_identity
from app.services.routing.commercial_report_export import CommercialReportExportService

logger = logging.getLogger(__name__)


async def run_commercial_report_schedules_once(
    *,
    cluster_id: str | None = None,
    node_id: str | None = None,
    lease_token: int | None = None,
) -> list[dict]:
    async with SessionLocal() as session:
        if lease_token is not None and cluster_id and node_id:
            valid = await validate_fencing_token(
                session,
                cluster_id=cluster_id,
                leader_role="reporter",
                lease_token=lease_token,
                node_id=node_id,
            )
            if not valid:
                await session.commit()
                return []
        service = CommercialReportExportService(session)
        result = await service.run_due_schedules_once()
        await session.commit()
        return result


async def run_commercial_calibration_once(
    *,
    cluster_id: str,
    node_id: str,
    lease_token: int,
) -> dict:
    async with SessionLocal() as session:
        valid = await validate_fencing_token(
            session,
            cluster_id=cluster_id,
            leader_role="calibration",
            lease_token=lease_token,
            node_id=node_id,
        )
        if not valid:
            await session.commit()
            return {"executed": False, "reason": "fencing_rejected"}
        report = await generate_calibration_report(session)
        recommendations = report.get("recommended_cost_multipliers", [])
        service = CommercialAutoApplyService(session)
        applied = 0
        for recommendation in recommendations:
            created = await service.run_auto_apply(
                recommendation["provider"],
                recommendation["model"],
                {
                    "confidence": recommendation.get("confidence", "low"),
                    "sample_count": recommendation.get("sample_count", 0),
                    "cost_error_percent": recommendation.get("avg_cost_error_percent", 0),
                    "recommended_multiplier": recommendation.get("recommended_cost_multiplier"),
                },
            )
            applied += int(created is not None)
        await session.commit()
        return {"executed": True, "recommendations": len(recommendations), "auto_applied": applied}


async def run_commercial_canary_jobs_once(
    *,
    cluster_id: str,
    node_id: str,
    lease_token: int,
) -> dict:
    async with SessionLocal() as session:
        valid = await validate_fencing_token(
            session,
            cluster_id=cluster_id,
            leader_role="canary",
            lease_token=lease_token,
            node_id=node_id,
        )
        if not valid:
            await session.commit()
            return {"executed": False, "reason": "fencing_rejected"}
        service = CommercialCanaryPromotionService(session)
        promotions = await service.list_active_promotions()
        results = []
        for promotion in promotions:
            config_id = promotion.get("config_id") or promotion.get("id")
            if not config_id:
                continue
            config_uuid = uuid.UUID(str(config_id))
            rollback = await service.auto_rollback_if_unhealthy(config_uuid)
            results.append(rollback)
            if rollback.get("action") == "rolled_back":
                continue
            if get_settings().commercial_canary_auto_promotion_enabled:
                results.append(await service.promote_canary_step(config_uuid))
        await session.commit()
        return {"executed": True, "promotions_checked": len(promotions), "results": results}


async def commercial_report_scheduler_loop(stop_event: asyncio.Event) -> None:
    cfg = get_settings()
    identity = resolve_node_identity(cfg)
    scheduler_lease_token: int | None = None
    report_lease_token: int | None = None
    calibration_lease_token: int | None = None
    canary_lease_token: int | None = None
    while not stop_event.is_set():
        try:
            async with SessionLocal() as session:
                scheduler_lease = await try_acquire_leader(
                    session,
                    cluster_id=cfg.cluster_id,
                    leader_role="scheduler",
                    node_id=identity["node_id"],
                    metadata_json={"job": "commercial_scheduler_coordinator"},
                    settings=cfg,
                )
                report_lease = await try_acquire_leader(
                    session,
                    cluster_id=cfg.cluster_id,
                    leader_role="reporter",
                    node_id=identity["node_id"],
                    metadata_json={"job": "report_scheduler"},
                    settings=cfg,
                )
                calibration_lease = await try_acquire_leader(
                    session,
                    cluster_id=cfg.cluster_id,
                    leader_role="calibration",
                    node_id=identity["node_id"],
                    metadata_json={"job": "calibration_scheduler"},
                    settings=cfg,
                )
                canary_lease = await try_acquire_leader(
                    session,
                    cluster_id=cfg.cluster_id,
                    leader_role="canary",
                    node_id=identity["node_id"],
                    metadata_json={"job": "canary_scheduler"},
                    settings=cfg,
                )
                if scheduler_lease.get("acquired"):
                    scheduler_lease_token = int(scheduler_lease["lease"]["lease_token"])
                    await renew_leader_lease(
                        session,
                        cluster_id=cfg.cluster_id,
                        leader_role="scheduler",
                        node_id=identity["node_id"],
                        lease_token=scheduler_lease_token,
                        metadata_json={"job": "commercial_scheduler_coordinator"},
                        settings=cfg,
                    )
                else:
                    scheduler_lease_token = None
                if report_lease.get("acquired"):
                    report_lease_token = int(report_lease["lease"]["lease_token"])
                    await renew_leader_lease(
                        session,
                        cluster_id=cfg.cluster_id,
                        leader_role="reporter",
                        node_id=identity["node_id"],
                        lease_token=report_lease_token,
                        metadata_json={"job": "report_scheduler"},
                        settings=cfg,
                    )
                else:
                    report_lease_token = None
                if calibration_lease.get("acquired"):
                    calibration_lease_token = int(calibration_lease["lease"]["lease_token"])
                    await renew_leader_lease(
                        session,
                        cluster_id=cfg.cluster_id,
                        leader_role="calibration",
                        node_id=identity["node_id"],
                        lease_token=calibration_lease_token,
                        metadata_json={"job": "calibration_scheduler"},
                        settings=cfg,
                    )
                else:
                    calibration_lease_token = None
                if canary_lease.get("acquired"):
                    canary_lease_token = int(canary_lease["lease"]["lease_token"])
                    await renew_leader_lease(
                        session,
                        cluster_id=cfg.cluster_id,
                        leader_role="canary",
                        node_id=identity["node_id"],
                        lease_token=canary_lease_token,
                        metadata_json={"job": "canary_scheduler"},
                        settings=cfg,
                    )
                else:
                    canary_lease_token = None
                await session.commit()
            result = []
            if report_lease_token is not None:
                result = await run_commercial_report_schedules_once(
                    cluster_id=cfg.cluster_id,
                    node_id=identity["node_id"],
                    lease_token=report_lease_token,
                )
            if result:
                logger.info("commercial report scheduler executed", extra={"extra_data": {"runs": result}})
            if calibration_lease_token is not None:
                calibration_result = await run_commercial_calibration_once(
                    cluster_id=cfg.cluster_id,
                    node_id=identity["node_id"],
                    lease_token=calibration_lease_token,
                )
                if calibration_result and (calibration_result.get("recommendations", 0) > 0 or calibration_result.get("auto_applied", 0) > 0):
                    logger.info("commercial calibration scheduler evaluated", extra={"extra_data": calibration_result})
                else:
                    logger.debug("commercial calibration scheduler evaluated", extra={"extra_data": calibration_result})
            if canary_lease_token is not None:
                canary_result = await run_commercial_canary_jobs_once(
                    cluster_id=cfg.cluster_id,
                    node_id=identity["node_id"],
                    lease_token=canary_lease_token,
                )
                if canary_result and (canary_result.get("promotions_checked", 0) > 0 or len(canary_result.get("results", [])) > 0):
                    logger.info("commercial canary scheduler evaluated", extra={"extra_data": canary_result})
                else:
                    logger.debug("commercial canary scheduler evaluated", extra={"extra_data": canary_result})
        except Exception as exc:
            logger.exception("commercial report scheduler failed", extra={"extra_data": {"error": str(exc)}})
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=max(30, cfg.commercial_lease_heartbeat_seconds))
        except asyncio.TimeoutError:
            continue
