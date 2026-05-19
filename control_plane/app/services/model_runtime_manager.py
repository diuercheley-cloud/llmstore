import asyncio
import logging
import os
import signal
import subprocess
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import httpx
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.operations.model_runtime import ModelRuntimeInstance
from app.models.model_registry import ModelRegistry
from app.core.time import utc_now

logger = logging.getLogger(__name__)

from app.contracts.model_runtime import ModelRuntimeContract, ModelInstance, ModelRuntimeCapabilities

class ModelRuntimeManager(ModelRuntimeContract):
    _processes: Dict[uuid.UUID, subprocess.Popen] = {}

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    def capabilities(self) -> ModelRuntimeCapabilities:
        return ModelRuntimeCapabilities(
            hot_swap=self.settings.model_hot_swap_enabled,
            multi_instance=True,
            automatic_health_checks=True
        )

    def validate_contract(self) -> bool:
        return True

    async def list_loaded_models(self) -> List[ModelRuntimeInstance]:
        result = await self.db.execute(select(ModelRuntimeInstance))
        return list(result.scalars().all())

    async def _find_free_port(self) -> int:
        result = await self.db.execute(select(ModelRuntimeInstance.port))
        used_ports = set(result.scalars().all())
        
        for port in range(self.settings.model_runtime_port_start, self.settings.model_runtime_port_end + 1):
            if port not in used_ports:
                # Double check with OS if possible, but for now trust DB
                return port
        raise RuntimeError("No free ports available for model runtime")

    async def load_model(self, model_id: uuid.UUID, backend_id: uuid.UUID, model_path: str, runtime_config: dict = None) -> ModelRuntimeInstance:
        if not self.settings.model_hot_swap_enabled:
            raise HTTPException(status_code=403, detail="Model hot swap is disabled")

        # Validation
        p = Path(model_path)
        if not p.exists():
            # Try relative to /models if it's just a filename
            p = Path("/models") / model_path
            if not p.exists():
                raise ValueError(f"Model file not found: {model_path}")
        
        if p.suffix.lower() != ".gguf":
            raise ValueError("Only .gguf models are supported for hot swap")

        port = await self._find_free_port()
        
        instance = ModelRuntimeInstance(
            model_id=model_id,
            backend_id=backend_id,
            model_path=str(p),
            port=port,
            status="loading",
            health_status="unknown"
        )
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)

        # Start process
        try:
            cmd = [
                "llama-server", # Assumes llama-server is in PATH
                "-m", str(p),
                "--port", str(port),
                "--host", "0.0.0.0"
            ]
            
            # Add extra params from config
            if runtime_config:
                for key, value in runtime_config.items():
                    if key.startswith("--"):
                        cmd.extend([key, str(value)])
            
            logger.info(f"Starting model runtime: {' '.join(cmd)}")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid # Create process group
            )
            self._processes[instance.id] = process
            
            # Start background health check
            asyncio.create_task(self._monitor_instance(instance.id, port))
            
            return instance
        except Exception as e:
            logger.error(f"Failed to start model runtime: {e}")
            instance.status = "failed"
            instance.last_error = str(e)
            await self.db.commit()
            raise

    async def _monitor_instance(self, instance_id: uuid.UUID, port: int):
        timeout = self.settings.model_load_timeout_seconds
        start_time = utc_now()
        
        while (utc_now() - start_time).total_seconds() < timeout:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(f"http://localhost:{port}/health", timeout=2.0)
                    if resp.status_code == 200:
                        await self._update_instance_status(instance_id, "ready", "healthy")
                        return
            except Exception:
                pass
            
            # Check if process is still alive
            process = self._processes.get(instance_id)
            if process and process.poll() is not None:
                _, stderr = process.communicate()
                error_msg = stderr.decode() if stderr else "Process exited unexpectedly"
                await self._update_instance_status(instance_id, "failed", "unhealthy", error_msg)
                return
                
            await asyncio.sleep(2)
            
        await self._update_instance_status(instance_id, "failed", "unhealthy", "Timed out waiting for health check")

    async def _update_instance_status(self, instance_id: uuid.UUID, status: str, health: str, error: str = None):
        if status == "failed":
            try:
                from app.core.metrics import record_hot_swap_failure
                record_hot_swap_failure(model_id=str(instance_id), reason=error or "unknown")
            except Exception:
                pass

        # We need a new session here as this is a background task
        from app.db.session import SessionLocal
        async with SessionLocal() as session:
            await session.execute(
                update(ModelRuntimeInstance)
                .where(ModelRuntimeInstance.id == instance_id)
                .values(status=status, health_status=health, last_error=error, updated_at=utc_now())
            )
            await session.commit()

    async def unload_model(self, instance_id: uuid.UUID):
        result = await self.db.execute(select(ModelRuntimeInstance).where(ModelRuntimeInstance.id == instance_id))
        instance = result.scalars().first()
        if not instance:
            return

        instance.status = "unloading"
        await self.db.commit()

        process = self._processes.get(instance_id)
        if process:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                # Wait a bit
                for _ in range(5):
                    if process.poll() is not None:
                        break
                    await asyncio.sleep(1)
                else:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except Exception as e:
                logger.error(f"Error killing process {process.pid}: {e}")
            
            del self._processes[instance_id]

        instance.status = "stopped"
        instance.is_active = False
        await self.db.commit()

    async def activate_model(self, instance_id: uuid.UUID):
        result = await self.db.execute(select(ModelRuntimeInstance).where(ModelRuntimeInstance.id == instance_id))
        instance = result.scalars().first()
        if not instance:
            raise ValueError("Instance not found")
            
        if instance.status != "ready":
            raise ValueError(f"Instance is not ready (status: {instance.status})")

        # Deactivate others for same model/backend
        await self.db.execute(
            update(ModelRuntimeInstance)
            .where(ModelRuntimeInstance.model_id == instance.model_id)
            .where(ModelRuntimeInstance.backend_id == instance.backend_id)
            .where(ModelRuntimeInstance.id != instance_id)
            .values(is_active=False)
        )
        
        instance.is_active = True
        await self.db.commit()

    async def rollback_active_model(self, model_id: uuid.UUID, backend_id: uuid.UUID):
        # Find the latest ready but not active instance
        result = await self.db.execute(
            select(ModelRuntimeInstance)
            .where(ModelRuntimeInstance.model_id == model_id)
            .where(ModelRuntimeInstance.backend_id == backend_id)
            .where(ModelRuntimeInstance.status == "ready")
            .where(ModelRuntimeInstance.is_active == False)
            .order_by(ModelRuntimeInstance.updated_at.desc())
        )
        previous = result.scalars().first()
        if not previous:
            raise ValueError("No previous ready instance found for rollback")
            
        await self.activate_model(previous.id)

    async def get_model_health(self, instance_id: uuid.UUID) -> dict:
        result = await self.db.execute(select(ModelRuntimeInstance).where(ModelRuntimeInstance.id == instance_id))
        instance = result.scalars().first()
        if not instance:
            return {"status": "not_found"}
            
        return {
            "instance_id": str(instance.id),
            "status": instance.status,
            "health_status": instance.health_status,
            "last_error": instance.last_error,
            "port": instance.port
        }
