import logging
import uuid
from datetime import datetime

from app.core.config import get_settings
from app.core.time import utc_now
from app.models.core.multimodal import (
    MultimodalAsset,
    MultimodalPolicyEvent,
    MultimodalUsageEvent,
)
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Banned words list for simple content safety hook
BANNED_WORDS = {"harmful", "illegal", "unsafe", "violence", "exploit", "weapons", "drugs"}


class MultimodalPolicyException(HTTPException):
    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(status_code=status_code, detail=detail)


class MultimodalPolicyService:
    @property
    def settings(self):
        return get_settings()

    async def check_policy(
        self, db: AsyncSession, client_id: uuid.UUID, feature: str, input_text: str = None
    ) -> None:
        # 1. Global Multimodal enabled check
        if not self.settings.multimodal_enabled:
            await self.log_policy_event(
                db,
                client_id,
                feature,
                "access_denied",
                {"reason": "MULTIMODAL_ENABLED feature flag is false"},
            )
            raise MultimodalPolicyException(
                "Multimodal capabilities are disabled on this server.", status_code=403
            )

        # 2. Specific feature enabled check
        feature_flag_map = {
            "vision": self.settings.vision_input_enabled,
            "image-generation": self.settings.image_generation_enabled,
            "speech-to-text": self.settings.speech_to_text_enabled,
            "audio-streaming": self.settings.realtime_audio_enabled,
        }

        if not feature_flag_map.get(feature, False):
            await self.log_policy_event(
                db,
                client_id,
                feature,
                "access_denied",
                {"reason": f"Feature flag for '{feature}' is disabled"},
            )
            raise MultimodalPolicyException(
                f"Multimodal feature '{feature}' is disabled.", status_code=403
            )

        # 3. Content Safety Hook
        if input_text:
            text_lower = input_text.lower()
            for word in BANNED_WORDS:
                if word in text_lower:
                    await self.log_policy_event(
                        db,
                        client_id,
                        feature,
                        "content_safety_blocked",
                        {
                            "reason": f"Input content matched banned word: {word}",
                            "input_text_redacted": input_text[:50] + "...",
                        },
                    )
                    raise MultimodalPolicyException(
                        "Content safety violation: input contains unsafe or "
                        "policy-violating terms.",
                        status_code=400,
                    )

        # 4. Quota/Budget check
        await self.enforce_quota_limits(db, client_id, feature)

        # 5. Audit Receipt (log allowed access)
        await self.log_policy_event(
            db, client_id, feature, "access_granted", {"timestamp": utc_now().isoformat()}
        )

    async def check_asset_access(
        self, db: AsyncSession, client_id: uuid.UUID, asset_id: uuid.UUID
    ) -> MultimodalAsset:
        """
        Enforce tenant isolation. Tenant A must NOT read or use assets of Tenant B.
        """
        stmt = select(MultimodalAsset).where(MultimodalAsset.id == asset_id)
        res = await db.execute(stmt)
        asset = res.scalar_one_or_none()
        if not asset:
            raise MultimodalPolicyException("Asset not found.", status_code=404)

        if asset.client_id != client_id:
            await self.log_policy_event(
                db,
                client_id,
                asset.asset_type,
                "access_denied",
                {
                    "reason": "Tenant isolation violation - attempted to access "
                    "asset of another tenant",
                    "asset_id": str(asset_id),
                },
            )
            raise MultimodalPolicyException(
                "Access denied: asset belongs to another tenant.", status_code=403
            )

        return asset

    async def enforce_quota_limits(
        self, db: AsyncSession, client_id: uuid.UUID, feature: str
    ) -> None:
        """
        Check estimated cost for this month to ensure budget is not exceeded.
        """
        now = utc_now()
        month_start = datetime(now.year, now.month, 1, tzinfo=now.tzinfo)

        stmt = select(func.sum(MultimodalUsageEvent.estimated_cost)).where(
            MultimodalUsageEvent.client_id == client_id,
            MultimodalUsageEvent.created_at >= month_start,
        )
        res = await db.execute(stmt)
        cost_sum = res.scalar() or 0.0

        budget_limit = 10.00
        if cost_sum >= budget_limit:
            await self.log_policy_event(
                db,
                client_id,
                feature,
                "quota_exceeded",
                {"current_spending": cost_sum, "budget_limit": budget_limit},
            )
            raise MultimodalPolicyException(
                f"Quota exceeded: Monthly budget of ${budget_limit:.2f} for "
                f"multimodal services has been reached (Current spending: "
                f"${cost_sum:.2f}).",
                status_code=429,
            )

    async def log_policy_event(
        self, db: AsyncSession, client_id: uuid.UUID, feature: str, event_type: str, details: dict
    ) -> None:
        event = MultimodalPolicyEvent(
            id=uuid.uuid4(),
            client_id=client_id,
            feature=feature,
            event_type=event_type,
            details=details,
        )
        db.add(event)
        await db.commit()
