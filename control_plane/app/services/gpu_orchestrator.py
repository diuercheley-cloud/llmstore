import logging
import subprocess
import uuid
from typing import Any, Dict, List, Optional

from app.core.metrics import (
    LLM_AUTOSCALING_DECISIONS_TOTAL,
    LLM_AUTOSCALING_REPLICAS_CURRENT,
    LLM_AUTOSCALING_REPLICAS_DESIRED,
    LLM_GPU_DEVICES_TOTAL,
    LLM_GPU_MEMORY_PRESSURE_RATIO,
    LLM_GPU_MEMORY_TOTAL_BYTES,
    LLM_GPU_MEMORY_USED_BYTES,
    LLM_GPU_TEMPERATURE_CELSIUS,
    LLM_GPU_UTILIZATION_RATIO,
)
from app.core.time import utc_now
from app.models.runtime.gpu_orchestration import (
    AutoscalingEvent,
    AutoscalingPolicy,
    GpuAllocation,
    GpuDevice,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class GpuOrchestrator:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def sync_local_gpus(self, node_id: uuid.UUID) -> List[GpuDevice]:
        """Collects GPU info from nvidia-smi (if available) and syncs to DB"""
        gpus = []
        try:
            query = "index,name,memory.total,memory.used,utilization.gpu,temperature.gpu"
            result = subprocess.run(
                ["nvidia-smi", f"--query-gpu={query}", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, check=True
            )
            lines = result.stdout.strip().split("\n")
            for line in lines:
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 6:
                    gpus.append({
                        "index": int(parts[0]),
                        "name": parts[1],
                        "memory_total": int(parts[2]),
                        "memory_used": int(parts[3]),
                        "utilization": float(parts[4]),
                        "temperature": float(parts[5])
                    })
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("nvidia-smi not found or failed, using mock GPU info if in dev mode")
            # For CI/Dev, we might return a mock GPU if configured
            return []

        synced_gpus = []
        for gpu_data in gpus:
            # Check if exists
            query = select(GpuDevice).where(
                GpuDevice.runtime_node_id == node_id,
                GpuDevice.gpu_index == gpu_data["index"]
            )
            result = await self.db.execute(query)
            device = result.scalars().first()

            if device:
                device.memory_used_mb = gpu_data["memory_used"]
                device.utilization_percent = gpu_data["utilization"]
                device.temperature_c = gpu_data["temperature"]
                device.updated_at = utc_now()
            else:
                device = GpuDevice(
                    runtime_node_id=node_id,
                    gpu_index=gpu_data["index"],
                    name=gpu_data["name"],
                    memory_total_mb=gpu_data["memory_total"],
                    memory_used_mb=gpu_data["memory_used"],
                    utilization_percent=gpu_data["utilization"],
                    temperature_c=gpu_data["temperature"]
                )
                self.db.add(device)
            synced_gpus.append(device)
            
            # Update metrics
            node_id_str = str(node_id)
            gpu_idx_str = str(gpu_data["index"])
            LLM_GPU_MEMORY_USED_BYTES.labels(node_id=node_id_str, gpu_index=gpu_idx_str).set(gpu_data["memory_used"] * 1024 * 1024)
            LLM_GPU_MEMORY_TOTAL_BYTES.labels(node_id=node_id_str, gpu_index=gpu_idx_str).set(gpu_data["memory_total"] * 1024 * 1024)
            LLM_GPU_UTILIZATION_RATIO.labels(node_id=node_id_str, gpu_index=gpu_idx_str).set(gpu_data["utilization"] / 100.0)
            LLM_GPU_TEMPERATURE_CELSIUS.labels(node_id=node_id_str, gpu_index=gpu_idx_str).set(gpu_data["temperature"])
            
            if gpu_data["memory_total"] > 0:
                pressure = gpu_data["memory_used"] / gpu_data["memory_total"]
                LLM_GPU_MEMORY_PRESSURE_RATIO.labels(node_id=node_id_str, gpu_id=gpu_idx_str).set(pressure)

        LLM_GPU_DEVICES_TOTAL.labels(node_id=str(node_id), status="active").set(len(synced_gpus))
        await self.db.commit()
        return synced_gpus

    async def get_node_gpu_capacity(self, node_id: uuid.UUID) -> Dict[str, Any]:
        query = select(GpuDevice).where(GpuDevice.runtime_node_id == node_id)
        result = await self.db.execute(query)
        devices = result.scalars().all()
        
        total_mem = sum(d.memory_total_mb for d in devices)
        used_mem = sum(d.memory_used_mb for d in devices)
        avg_util = sum(d.utilization_percent for d in devices) / len(devices) if devices else 0
        
        return {
            "total_memory_mb": total_mem,
            "used_memory_mb": used_mem,
            "free_memory_mb": total_mem - used_mem,
            "avg_utilization": avg_util,
            "gpu_count": len(devices)
        }

    async def allocate_gpu_for_model(self, model_id: uuid.UUID, memory_required_mb: int) -> Optional[GpuDevice]:
        # Find a GPU with enough free memory
        query = select(GpuDevice).where(GpuDevice.status == "active").order_by(GpuDevice.memory_used_mb.asc())
        result = await self.db.execute(query)
        devices = result.scalars().all()
        
        for device in devices:
            if (device.memory_total_mb - device.memory_used_mb) >= memory_required_mb:
                allocation = GpuAllocation(
                    gpu_device_id=device.id,
                    model_registry_id=model_id,
                    allocated_memory_mb=memory_required_mb
                )
                device.memory_used_mb += memory_required_mb
                self.db.add(allocation)
                await self.db.commit()
                return device
        return None

    async def evaluate_autoscaling(self):
        """Runs periodic check for autoscaling policies"""
        query = select(AutoscalingPolicy).where(AutoscalingPolicy.is_active == True)
        result = await self.db.execute(query)
        policies = result.scalars().all()

        for policy in policies:
            decision = await self._check_policy(policy)
            
            # Update metrics
            policy_id_str = str(policy.id)
            LLM_AUTOSCALING_REPLICAS_DESIRED.labels(policy_id=policy_id_str).set(decision["replicas_after"])
            LLM_AUTOSCALING_REPLICAS_CURRENT.labels(policy_id=policy_id_str).set(decision["replicas_before"])

            if decision["action"] != "no_op":
                event = AutoscalingEvent(
                    policy_id=policy.id,
                    event_type=decision["action"],
                    reason=decision["reason"],
                    replicas_before=decision["replicas_before"],
                    replicas_after=decision["replicas_after"],
                    metrics_snapshot=decision["metrics"]
                )
                self.db.add(event)
                LLM_AUTOSCALING_DECISIONS_TOTAL.labels(policy_id=policy_id_str, action=decision["action"]).inc()
                logger.info(f"Autoscaling Decision for {policy.name}: {decision['action']} - {decision['reason']}")
        
        await self.db.commit()

    async def _check_policy(self, policy: AutoscalingPolicy) -> Dict[str, Any]:
        # Get current metrics for the model
        # This would integrate with Prometheus or internal stats
        # For now, we mock/placeholder some logic
        
        current_replicas = 1 # Placeholder, should count ready placements
        
        metrics = {
            "queue_depth": 0,
            "latency_p95": 0.0,
            "gpu_pressure": 0.0
        }
        
        action = "no_op"
        reason = "Stable"
        target_replicas = current_replicas

        if policy.strategy == "queue_depth":
            # mock value
            metrics["queue_depth"] = 10 # Should come from Redis/DB
            if metrics["queue_depth"] > policy.target_value:
                action = "scale_up"
                target_replicas = min(current_replicas + 1, policy.max_replicas)
                reason = f"Queue depth {metrics['queue_depth']} > target {policy.target_value}"
            elif metrics["queue_depth"] < (policy.target_value / 2):
                action = "scale_down"
                target_replicas = max(current_replicas - 1, policy.min_replicas)
                reason = f"Queue depth {metrics['queue_depth']} is low"

        return {
            "action": action if target_replicas != current_replicas else "no_op",
            "reason": reason,
            "replicas_before": current_replicas,
            "replicas_after": target_replicas,
            "metrics": metrics
        }
