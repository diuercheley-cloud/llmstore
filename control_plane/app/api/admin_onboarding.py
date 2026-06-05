# Owner: platform-ops
import json
from datetime import datetime, timezone

from app.api.deps import require_admin
from app.db.session import get_redis
from app.schemas.admin import OnboardingStatusRead, OnboardingStatusUpdate
from fastapi import APIRouter, Depends
from redis.asyncio import Redis

router = APIRouter(prefix="/admin/onboarding", tags=["admin-onboarding"], dependencies=[Depends(require_admin)])

REDIS_KEY = "admin:onboarding:status"

@router.get("/status", response_model=OnboardingStatusRead)
async def get_onboarding_status(redis: Redis = Depends(get_redis)):
    data = await redis.get(REDIS_KEY)
    if not data:
        # Default to finished so the admin UI is usable on fresh stacks.
        # The wizard can still be re-enabled explicitly from the UI.
        return OnboardingStatusRead(is_finished=True)
    
    status_dict = json.loads(data)
    return OnboardingStatusRead(**status_dict)

@router.post("/status", response_model=OnboardingStatusRead)
async def update_onboarding_status(
    payload: OnboardingStatusUpdate,
    redis: Redis = Depends(get_redis)
):
    status_dict = {
        "is_finished": payload.is_finished,
        "finished_at": datetime.now(timezone.utc).isoformat() if payload.is_finished else None,
        "metadata_json": payload.metadata_json
    }
    await redis.set(REDIS_KEY, json.dumps(status_dict))
    return OnboardingStatusRead(**status_dict)
