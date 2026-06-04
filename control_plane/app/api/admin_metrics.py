# Owner: platform-ops
import asyncio
import json
import logging
import subprocess
from datetime import datetime, timezone
from typing import AsyncGenerator

import psutil
from app.api.deps import get_db_session, get_inference_proxy
from app.models.inference_backend import InferenceBackend
from app.models.request_log import RequestLog
from app.services.inference_proxy import InferenceProxy
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/metrics", tags=["admin-metrics"])

logger = logging.getLogger(__name__)

def get_gpu_metrics():
    """Attempt to get GPU metrics via nvidia-smi."""
    try:
        # Simplified nvidia-smi call
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu", "--format=csv,noheader,nounits"],
            encoding="utf-8"
        )
        lines = output.strip().split("\n")
        gpus = []
        for line in lines:
            util, mem_used, mem_total, temp = line.split(", ")
            gpus.append({
                "utilization": float(util),
                "memory_used": float(mem_used),
                "memory_total": float(mem_total),
                "temperature": float(temp)
            })
        return gpus
    except Exception:
        # Fallback if nvidia-smi is not available
        return []

async def get_system_metrics():
    return {
        "cpu": psutil.cpu_percent(interval=None),
        "ram": psutil.virtual_memory().percent,
        "gpus": get_gpu_metrics(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

async def get_inference_metrics(proxy: InferenceProxy, session: AsyncSession):
    # Queue metrics from proxy
    queue_snapshot = proxy.queue_manager.get_snapshot()
    
    # Latency metrics from RequestLog (last 100 requests in last 5 minutes)
    # This is a bit heavy for every 2s, so maybe we only compute it every 10s
    # but for the SSE stream we can just send the last known values.
    return {
        "queue": {
            "depth": queue_snapshot.get("total_queued", 0),
            "active_requests": queue_snapshot.get("total_running", 0),
            "avg_wait_time_ms": queue_snapshot.get("avg_wait_ms", 0)
        }
    }

async def get_latency_stats(session: AsyncSession):
    # Simplified p50/p95/p99 calculation from last 100 successful requests
    try:
        stmt = (
            select(RequestLog.total_duration_ms)
            .where(RequestLog.status_code == 200)
            .order_by(RequestLog.created_at.desc())
            .limit(100)
        )
        result = await session.execute(stmt)
        durations = sorted([r[0] for r in result.all() if r[0] is not None])
        
        if not durations:
            return {"p50": 0, "p95": 0, "p99": 0}
            
        def percentile(data, p):
            idx = int(len(data) * p)
            return data[min(idx, len(data) - 1)]

        return {
            "p50": percentile(durations, 0.5),
            "p95": percentile(durations, 0.95),
            "p99": percentile(durations, 0.99)
        }
    except Exception as e:
        logger.error(f"Error calculating latency stats: {e}")
        return {"p50": 0, "p95": 0, "p99": 0}

from app.models.security_event import SecurityEvent

# ... (previous functions remain the same)

async def get_backend_health(proxy: InferenceProxy, session: AsyncSession):
    try:
        backend_rows = (await session.execute(select(InferenceBackend).where(InferenceBackend.is_active == True))).scalars().all()
        results = await asyncio.gather(*[proxy.health_backend(b) for b in backend_rows])
        return [
            {
                "id": str(b.id),
                "name": b.name,
                "provider": b.provider,
                "ok": h.get("ok", False),
                "latency_ms": h.get("latency_ms", 0)
            }
            for b, h in zip(backend_rows, results)
        ]
    except Exception:
        return []

async def get_latest_security_events(session: AsyncSession):
    try:
        stmt = select(SecurityEvent).order_by(SecurityEvent.created_at.desc()).limit(5)
        result = await session.execute(stmt)
        return [
            {
                "id": str(e.id),
                "type": e.event_type,
                "severity": e.severity,
                "message": e.description,
                "timestamp": e.created_at.isoformat()
            }
            for e in result.scalars().all()
        ]
    except Exception:
        return []

@router.get("/stream")
async def stream_metrics(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    proxy: InferenceProxy = Depends(get_inference_proxy),
):
    async def event_generator() -> AsyncGenerator[str, None]:
        counter = 0
        last_latency_stats = {"p50": 0, "p95": 0, "p99": 0}
        last_backend_health = []
        
        while True:
            if await request.is_disconnected():
                break

            system = await get_system_metrics()
            inference = await get_inference_metrics(proxy, session)
            
            # Heavy stats every 10s
            if counter % 5 == 0:
                last_latency_stats = await get_latency_stats(session)
                last_backend_health = await get_backend_health(proxy, session)
            
            # Security events every 4s
            security_events = []
            if counter % 2 == 0:
                security_events = await get_latest_security_events(session)

            payload = {
                "system": system,
                "inference": inference,
                "latency": last_latency_stats,
                "backends": last_backend_health,
                "security": security_events,
                "timestamp": system["timestamp"]
            }
            
            yield f"data: {json.dumps(payload)}\n\n"
            
            counter += 1
            await asyncio.sleep(2)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
