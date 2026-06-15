"""
Owner: agent-platform
Status: beta
"""

import logging
import uuid
from typing import Any

from app.core.time import utc_now
from app.models.agents.agents import AgentEvalDataset, AgentEvalDatasetVersion
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)


class EvalDatasetRegistryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_dataset(
        self, agent_id: uuid.UUID, name: str, description: str | None = None
    ) -> AgentEvalDataset:
        dataset = AgentEvalDataset(
            id=uuid.uuid4(),
            agent_id=agent_id,
            name=name,
            description=description,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        self.db.add(dataset)
        await self.db.commit()
        await self.db.refresh(dataset)
        return dataset

    async def get_dataset(self, dataset_id: uuid.UUID) -> AgentEvalDataset | None:
        res = await self.db.execute(
            select(AgentEvalDataset).where(AgentEvalDataset.id == dataset_id)
        )
        return res.scalar_one_or_none()

    async def get_dataset_by_agent(self, agent_id: uuid.UUID) -> list[AgentEvalDataset]:
        res = await self.db.execute(
            select(AgentEvalDataset).where(AgentEvalDataset.agent_id == agent_id)
        )
        return list(res.scalars().all())

    async def create_dataset_version(
        self, dataset_id: uuid.UUID, version: str, cases_json: list[dict[str, Any]]
    ) -> AgentEvalDatasetVersion:
        # Check if version already exists (Dataset versions are immutable)
        res = await self.db.execute(
            select(AgentEvalDatasetVersion)
            .where(AgentEvalDatasetVersion.dataset_id == dataset_id)
            .where(AgentEvalDatasetVersion.version == version)
        )
        existing = res.scalar_one_or_none()
        if existing:
            raise ValueError(f"Dataset version {version} already exists and is immutable.")

        ds_version = AgentEvalDatasetVersion(
            id=uuid.uuid4(),
            dataset_id=dataset_id,
            version=version,
            cases_json=cases_json,
            created_at=utc_now(),
        )
        self.db.add(ds_version)

        # Update parent dataset updated_at
        res_ds = await self.db.execute(
            select(AgentEvalDataset).where(AgentEvalDataset.id == dataset_id)
        )
        dataset = res_ds.scalar_one_or_none()
        if dataset:
            dataset.updated_at = utc_now()

        await self.db.commit()
        await self.db.refresh(ds_version)
        return ds_version

    async def get_latest_version(self, dataset_id: uuid.UUID) -> AgentEvalDatasetVersion | None:
        res = await self.db.execute(
            select(AgentEvalDatasetVersion)
            .where(AgentEvalDatasetVersion.dataset_id == dataset_id)
            .order_by(AgentEvalDatasetVersion.created_at.desc())
        )
        return res.scalars().first()

    async def get_dataset_version_by_id(
        self, version_id: uuid.UUID
    ) -> AgentEvalDatasetVersion | None:
        res = await self.db.execute(
            select(AgentEvalDatasetVersion).where(AgentEvalDatasetVersion.id == version_id)
        )
        return res.scalar_one_or_none()
