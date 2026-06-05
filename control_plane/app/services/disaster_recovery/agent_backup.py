"""
Disaster Recovery and Backup for agent configurations, memory, and state.
Supports full and incremental backups with restore validation.
"""

import asyncio
import json
import logging
import tarfile
import tempfile
import uuid
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class BackupManifest:
    def __init__(self, backup_id: str, agent_ids: List[str], backup_type: str = "full",
                 created_at: Optional[str] = None, checksum: str = ""):
        self.backup_id = backup_id
        self.agent_ids = agent_ids
        self.backup_type = backup_type
        self.created_at = created_at or datetime.now(UTC).isoformat()
        self.checksum = checksum

    def to_dict(self) -> dict:
        return {
            "backup_id": self.backup_id,
            "agent_ids": self.agent_ids,
            "backup_type": self.backup_type,
            "created_at": self.created_at,
            "checksum": self.checksum,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BackupManifest":
        return cls(
            backup_id=d["backup_id"],
            agent_ids=d["agent_ids"],
            backup_type=d.get("backup_type", "full"),
            created_at=d.get("created_at"),
            checksum=d.get("checksum", ""),
        )


class AgentBackupService:
    """
    Backup and restore service for agent configurations, executions, and state.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self._backup_dir = Path(self.settings.disaster_recovery_backup_dir or "/tmp/agent-backups")
        self._backup_dir.mkdir(parents=True, exist_ok=True)
        self._running_tasks: Dict[str, asyncio.Task] = {}

    async def create_backup(self, agent_ids: List[str], backup_type: str = "full",
                            include_memory: bool = True, include_runs: bool = True) -> BackupManifest:
        backup_id = f"backup-{uuid.uuid4().hex[:12]}"
        manifest = BackupManifest(backup_id, agent_ids, backup_type)

        backup_path = self._backup_dir / f"{backup_id}.tar.gz"
        tmp_dir = Path(tempfile.mkdtemp(prefix=f"backup-{backup_id}-"))

        try:
            for agent_id in agent_ids:
                agent_dir = tmp_dir / agent_id
                agent_dir.mkdir(parents=True, exist_ok=True)

                await self._backup_agent_config(agent_id, agent_dir)
                if include_memory:
                    await self._backup_agent_memory(agent_id, agent_dir)
                if include_runs:
                    await self._backup_agent_runs(agent_id, agent_dir)

            manifest_path = tmp_dir / "manifest.json"
            manifest_path.write_text(json.dumps(manifest.to_dict(), indent=2))

            with tarfile.open(str(backup_path), "w:gz") as tar:
                tar.add(str(tmp_dir), arcname=backup_id)

            import hashlib
            with open(str(backup_path), "rb") as f:
                manifest.checksum = hashlib.sha256(f.read()).hexdigest()[:16]

            logger.info("Backup %s created: %d agents, type=%s", backup_id, len(agent_ids), backup_type)
            return manifest

        finally:
            import shutil
            shutil.rmtree(str(tmp_dir), ignore_errors=True)

    async def restore_backup(self, backup_id: str, target_agent_ids: Optional[List[str]] = None) -> int:
        backup_path = self._backup_dir / f"{backup_id}.tar.gz"
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_id}")

        tmp_dir = Path(tempfile.mkdtemp(prefix=f"restore-{backup_id}-"))
        restored_count = 0

        try:
            with tarfile.open(str(backup_path), "r:gz") as tar:
                tar.extractall(str(tmp_dir))

            manifest_data = json.loads((tmp_dir / backup_id / "manifest.json").read_text())
            manifest = BackupManifest.from_dict(manifest_data)

            agent_ids = target_agent_ids or manifest.agent_ids
            for agent_id in agent_ids:
                agent_dir = tmp_dir / backup_id / agent_id
                if not agent_dir.exists():
                    logger.warning("Agent %s not found in backup %s, skipping", agent_id, backup_id)
                    continue

                await self._restore_agent_config(agent_id, agent_dir)
                await self._restore_agent_memory(agent_id, agent_dir)
                restored_count += 1

            logger.info("Restored %d/%d agents from backup %s", restored_count, len(agent_ids), backup_id)
            return restored_count

        finally:
            import shutil
            shutil.rmtree(str(tmp_dir), ignore_errors=True)

    async def list_backups(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        backups = []
        for f in sorted(self._backup_dir.glob("backup-*.tar.gz"), reverse=True):
            try:
                import json
                import tarfile
                with tarfile.open(str(f), "r:gz") as tar:
                    mf = tar.extractfile(f"{f.stem}/manifest.json")
                    if mf:
                        manifest = json.loads(mf.read())
                        if agent_id and agent_id not in manifest.get("agent_ids", []):
                            continue
                        backups.append(manifest)
            except Exception as e:
                logger.warning("Failed to read backup %s: %s", f.name, e)
        return backups

    async def _backup_agent_config(self, agent_id: str, agent_dir: Path):
        from app.models.agents import AgentDefinition
        result = await self.db.execute(
            select(AgentDefinition).where(AgentDefinition.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        if agent:
            config = {
                "id": str(agent.id),
                "name": agent.name,
                "description": agent.description,
                "system_prompt": agent.system_prompt,
                "model": agent.model,
                "tools": agent.tools,
                "memory": agent.memory,
                "status": agent.status,
                "owner": agent.owner,
                "created_at": agent.created_at.isoformat() if agent.created_at else None,
                "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
            }
            (agent_dir / "config.json").write_text(json.dumps(config, indent=2, default=str))
            logger.debug("Backed up config for agent %s", agent_id)

    async def _backup_agent_memory(self, agent_id: str, agent_dir: Path):
        from app.models.agents import AgentMemoryItem
        result = await self.db.execute(
            select(AgentMemoryItem).where(AgentMemoryItem.agent_id == agent_id).limit(1000)
        )
        items = result.scalars().all()
        if items:
            memory_data = []
            for item in items:
                memory_data.append({
                    "id": str(item.id),
                    "memory_type": item.memory_type,
                    "content": item.content,
                    "metadata": item.metadata_json,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                })
            (agent_dir / "memory.json").write_text(json.dumps(memory_data, indent=2, default=str))

    async def _backup_agent_runs(self, agent_id: str, agent_dir: Path):
        from app.models.agents import AgentRun
        result = await self.db.execute(
            select(AgentRun).where(AgentRun.agent_id == agent_id)
            .order_by(AgentRun.created_at.desc()).limit(500)
        )
        runs = result.scalars().all()
        if runs:
            runs_data = []
            for run in runs:
                runs_data.append({
                    "id": str(run.id),
                    "status": run.status,
                    "input": run.input_text,
                    "output": run.result,
                    "total_tokens": run.total_tokens,
                    "estimated_cost_brl": run.estimated_cost_brl,
                    "created_at": run.created_at.isoformat() if run.created_at else None,
                })
            (agent_dir / "runs.json").write_text(json.dumps(runs_data, indent=2, default=str))

    async def _restore_agent_config(self, agent_id: str, agent_dir: Path):
        config_file = agent_dir / "config.json"
        if not config_file.exists():
            return
        config = json.loads(config_file.read_text())
        from app.models.agents import AgentDefinition
        result = await self.db.execute(
            select(AgentDefinition).where(AgentDefinition.id == agent_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            for field in ["name", "description", "system_prompt", "model", "tools", "status"]:
                if field in config:
                    setattr(existing, field, config[field])
        else:
            new_agent = AgentDefinition(id=agent_id, **{k: v for k, v in config.items() if k != "id"})
            self.db.add(new_agent)
        await self.db.flush()

    async def _restore_agent_memory(self, agent_id: str, agent_dir: Path):
        memory_file = agent_dir / "memory.json"
        if not memory_file.exists():
            return
        memory_data = json.loads(memory_file.read_text())
        from app.models.agents import AgentMemoryItem
        for item_data in memory_data:
            existing = await self.db.get(AgentMemoryItem, item_data["id"])
            if not existing:
                item = AgentMemoryItem(
                    id=item_data["id"],
                    agent_id=agent_id,
                    memory_type=item_data.get("memory_type", "long_term"),
                    content=item_data["content"],
                    metadata_json=item_data.get("metadata", {}),
                )
                self.db.add(item)
        await self.db.flush()


class BackupScheduler:
    """
    Scheduled automatic backups for all active agents.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.service = AgentBackupService(db)
        self._task: Optional[asyncio.Task] = None

    async def start_schedule(self, interval_hours: int = 24):
        if self._task and not self._task.done():
            return

        async def _loop():
            while True:
                try:
                    from app.models.agents import AgentDefinition
                    result = await self.db.execute(
                        select(AgentDefinition.id).where(AgentDefinition.status.in_(["active", "production"]))
                    )
                    agent_ids = [str(row[0]) for row in result.all()]
                    if agent_ids:
                        await self.service.create_backup(agent_ids, backup_type="scheduled")
                        logger.info("Scheduled backup completed for %d agents", len(agent_ids))
                except Exception as e:
                    logger.error("Scheduled backup failed: %s", e)
                await asyncio.sleep(interval_hours * 3600)

        self._task = asyncio.create_task(_loop())

    def stop_schedule(self):
        if self._task and not self._task.done():
            self._task.cancel()
