import hashlib
import uuid
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.mlops import MLDataset, MLDatasetVersion
from app.models.admin_rbac import AdminAuditEvent
from app.core.time import utc_now


async def log_mlops_audit(
    session: AsyncSession,
    event_type: str,
    status: str,
    target_type: str,
    target_id: str,
    details: Dict[str, Any],
    admin_user_id: Optional[uuid.UUID] = None,
) -> None:
    audit_event = AdminAuditEvent(
        id=uuid.uuid4(),
        admin_user_id=admin_user_id,
        event_type=event_type,
        status=status,
        target_type=target_type,
        target_id=target_id,
        metadata_json=details,
        created_at=utc_now(),
    )
    session.add(audit_event)
    await session.flush()


class DatasetRegistry:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_dataset(
        self,
        name: str,
        description: Optional[str] = None,
        is_production: bool = False,
        admin_user_id: Optional[uuid.UUID] = None,
    ) -> MLDataset:
        # If is_production, require explicit approval. Otherwise default is approved.
        is_approved = not is_production

        dataset = MLDataset(
            id=uuid.uuid4(),
            name=name,
            description=description,
            is_production=is_production,
            is_approved=is_approved,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        self.session.add(dataset)
        await self.session.flush()

        await log_mlops_audit(
            self.session,
            event_type="dataset_create",
            status="success",
            target_type="ml_datasets",
            target_id=str(dataset.id),
            details={"name": name, "is_production": is_production, "is_approved": is_approved},
            admin_user_id=admin_user_id,
        )
        return dataset

    async def approve_dataset(
        self,
        dataset_id: uuid.UUID,
        admin_user_id: Optional[uuid.UUID] = None,
    ) -> MLDataset:
        result = await self.session.execute(
            select(MLDataset).where(MLDataset.id == dataset_id)
        )
        dataset = result.scalar_one_or_none()
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        dataset.is_approved = True
        dataset.updated_at = utc_now()

        await log_mlops_audit(
            self.session,
            event_type="dataset_approve",
            status="success",
            target_type="ml_datasets",
            target_id=str(dataset.id),
            details={"name": dataset.name, "is_approved": True},
            admin_user_id=admin_user_id,
        )
        return dataset

    async def create_version(
        self,
        dataset_id: uuid.UUID,
        version: str,
        checksum: str,
        provenance: str,
        redaction_status: str = "none",
        consent_metadata: Optional[Dict[str, Any]] = None,
        content_bytes: Optional[bytes] = None,  # optional content to verify checksum
        admin_user_id: Optional[uuid.UUID] = None,
    ) -> MLDatasetVersion:
        result = await self.session.execute(
            select(MLDataset).where(MLDataset.id == dataset_id)
        )
        dataset = result.scalar_one_or_none()
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        # Approval check for production datasets
        if dataset.is_production and not dataset.is_approved:
            await log_mlops_audit(
                self.session,
                event_type="dataset_version_create",
                status="failed",
                target_type="ml_datasets",
                target_id=str(dataset.id),
                details={"reason": "unapproved_production_dataset"},
                admin_user_id=admin_user_id,
            )
            raise HTTPException(status_code=403, detail="Production datasets must be approved before adding versions.")

        # Checksum validation
        if content_bytes is not None:
            expected_checksum = hashlib.sha256(content_bytes).hexdigest()
            if checksum != expected_checksum:
                await log_mlops_audit(
                    self.session,
                    event_type="dataset_version_create",
                    status="failed",
                    target_type="ml_datasets",
                    target_id=str(dataset.id),
                    details={"reason": "invalid_checksum", "provided": checksum, "expected": expected_checksum},
                    admin_user_id=admin_user_id,
                )
                raise HTTPException(status_code=400, detail="Invalid dataset checksum detected.")

        db_version = MLDatasetVersion(
            id=uuid.uuid4(),
            dataset_id=dataset_id,
            version=version,
            checksum=checksum,
            provenance=provenance,
            redaction_status=redaction_status,
            consent_metadata=consent_metadata,
            created_at=utc_now(),
        )
        self.session.add(db_version)
        await self.session.flush()

        await log_mlops_audit(
            self.session,
            event_type="dataset_version_create",
            status="success",
            target_type="ml_dataset_versions",
            target_id=str(db_version.id),
            details={
                "dataset_id": str(dataset_id),
                "version": version,
                "checksum": checksum,
                "redaction_status": redaction_status,
            },
            admin_user_id=admin_user_id,
        )
        return db_version

    async def list_datasets(self) -> List[MLDataset]:
        result = await self.session.execute(select(MLDataset))
        return list(result.scalars().all())
