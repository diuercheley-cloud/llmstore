# Owner: Architecture
# Surface: admin

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.services.auth import require_admin
from app.services.admin_rbac import record_admin_audit_event
from app.services.runtime_profiles import RuntimeProfilesService

router = APIRouter(
    prefix="/admin/runtime-profiles",
    tags=["admin", "runtime-profiles"],
    dependencies=[Depends(require_admin)],
)

service = RuntimeProfilesService()

class ValidateRequest(BaseModel):
    profile_id: str

class ApplyRequest(BaseModel):
    profile_id: Optional[str] = None
    dry_run: bool = True
    rollback: bool = False

@router.get("", response_model=List[Dict[str, Any]])
async def list_profiles():
    """
    List all available runtime profiles.
    """
    return service.get_all_profiles()

@router.get("/current", response_model=Dict[str, Any])
async def get_current_runtime_config():
    """
    Retrieve the current active runtime configurations.
    """
    return service.get_current_settings()

@router.post("/validate")
async def validate_profile(payload: ValidateRequest):
    """
    Validate if a profile settings match valid Pydantic settings.
    """
    is_valid, errors = service.validate_profile(payload.profile_id)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail={"errors": errors}
        )
    return {"status": "valid", "profile_id": payload.profile_id}

@router.post("/apply")
async def apply_profile(
    payload: ApplyRequest,
    request: Request,
    admin: Any = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Apply a runtime profile or perform a rollback to the backup configuration.
    """
    # 1. Rollback logic
    if payload.rollback:
        try:
            before, after, msg = service.rollback(dry_run=payload.dry_run)
            
            # Record audit event on successful live rollback
            if not payload.dry_run:
                # admin object could be a dict (legacy) or admin user model
                admin_user = admin if hasattr(admin, "user") else None
                await record_admin_audit_event(
                    session,
                    event_type="runtime_profile.rollback",
                    status="success",
                    request=request,
                    admin=admin_user,
                    actor_identifier="admin_api",
                    target_type="runtime_profile",
                    target_id="rollback",
                    metadata={"before": before, "after": after, "message": msg}
                )
            
            return {
                "status": "success",
                "dry_run": payload.dry_run,
                "message": msg,
                "diff": {
                    "before": before,
                    "after": after
                }
            }
        except Exception as e:
            # Audit failed rollback
            if not payload.dry_run:
                admin_user = admin if hasattr(admin, "user") else None
                await record_admin_audit_event(
                    session,
                    event_type="runtime_profile.rollback",
                    status="failed",
                    request=request,
                    admin=admin_user,
                    actor_identifier="admin_api",
                    target_type="runtime_profile",
                    target_id="rollback",
                    metadata={"error": str(e)}
                )
            
            raise HTTPException(
                status_code=400 if isinstance(e, FileNotFoundError) else 403,
                detail=str(e)
            )

    # 2. Regular Apply logic
    if not payload.profile_id:
        raise HTTPException(
            status_code=400,
            detail="profile_id is required unless rollback is true."
        )

    try:
        before, after, msg = service.apply_profile(payload.profile_id, dry_run=payload.dry_run)
        
        # Record audit event on successful live apply
        if not payload.dry_run:
            admin_user = admin if hasattr(admin, "user") else None
            await record_admin_audit_event(
                session,
                event_type="runtime_profile.apply",
                status="success",
                request=request,
                admin=admin_user,
                actor_identifier="admin_api",
                target_type="runtime_profile",
                target_id=payload.profile_id,
                metadata={"before": before, "after": after, "message": msg}
            )

        return {
            "status": "success",
            "dry_run": payload.dry_run,
            "message": msg,
            "diff": {
                "before": before,
                "after": after
            }
        }
    except Exception as e:
        # Audit failed apply
        if not payload.dry_run:
            admin_user = admin if hasattr(admin, "user") else None
            await record_admin_audit_event(
                session,
                event_type="runtime_profile.apply",
                status="failed",
                request=request,
                admin=admin_user,
                actor_identifier="admin_api",
                target_type="runtime_profile",
                target_id=payload.profile_id,
                metadata={"error": str(e)}
            )
        
        raise HTTPException(
            status_code=400 if isinstance(e, ValueError) else 403,
            detail=str(e)
        )
