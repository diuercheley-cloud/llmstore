import uuid
from datetime import timedelta
from typing import List

from app.core.time import utc_now
from app.models.commercial.commercial_crypto_trust import (
    CommercialKeyMaterial,
    CommercialKeyRotationSchedule,
    KeyUsageStatus,
)
from app.services.security.crypto_provider_registry import CryptoProviderRegistry
from app.services.security.kms_runtime import KMSRuntime
from sqlalchemy.orm import Session


class KeyRotationService:
    def __init__(self, db: Session):
        self.db = db
        self.kms_runtime = KMSRuntime(db)

    def get_keys_pending_rotation(self) -> List[CommercialKeyRotationSchedule]:
        now = utc_now()
        schedules = self.db.query(CommercialKeyRotationSchedule).filter(
            CommercialKeyRotationSchedule.next_rotation_at <= now
        ).all()
        return schedules

    async def rotate_key(self, schedule_id: uuid.UUID) -> CommercialKeyMaterial:
        schedule = self.db.query(CommercialKeyRotationSchedule).filter(
            CommercialKeyRotationSchedule.id == schedule_id
        ).first()

        if not schedule:
            raise ValueError("Schedule not found")

        old_key = schedule.key
        provider_config = self.kms_runtime.get_provider_config(old_key.provider_id)
        provider = CryptoProviderRegistry.get_provider(provider_config.provider_type)

        # Generate new key material
        new_key_data = await provider.generate_key(old_key.key_type)

        # Create new key record
        new_key = CommercialKeyMaterial(
            provider_id=old_key.provider_id,
            tenant_id=old_key.tenant_id,
            key_alias=f"{old_key.key_alias}_rot_{utc_now().strftime('%Y%m%d%H%M%S')}",
            key_type=old_key.key_type,
            status=KeyUsageStatus.ACTIVE,
            encrypted_key_blob=new_key_data.get("material") # Or encrypted equivalent
        )
        self.db.add(new_key)

        # Update old key status
        old_key.status = KeyUsageStatus.ROTATED
        # In a real system, you might set an expiration date for the old key

        # Update schedule
        schedule.key_id = new_key.id
        schedule.last_rotated_at = utc_now()
        schedule.next_rotation_at = schedule.last_rotated_at + timedelta(days=schedule.rotation_interval_days)

        self.db.commit()
        self.db.refresh(new_key)
        return new_key

    async def process_rotations(self):
        schedules = self.get_keys_pending_rotation()
        results = []
        for schedule in schedules:
            try:
                new_key = await self.rotate_key(schedule.id)
                results.append({"schedule_id": str(schedule.id), "status": "success", "new_key_id": str(new_key.id)})
            except Exception as e:
                results.append({"schedule_id": str(schedule.id), "status": "failed", "error": str(e)})
        return results
