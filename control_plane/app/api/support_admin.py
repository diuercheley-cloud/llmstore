# Owner: Platform Operations
# Surface: admin

import os

from app.api.deps import get_admin_token
from app.services.runtime_dependencies import get_db_session
from app.services.support_bundle import SupportBundleService
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/support", tags=["Support"])

@router.post("/bundle", status_code=status.HTTP_201_CREATED)
async def create_support_bundle(
    admin_token: str = Depends(get_admin_token),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Generate a new support bundle for diagnostic purposes.
    The bundle is sanitized and does not contain sensitive data.
    """
    service = SupportBundleService(db)
    try:
        bundle_path = await service.generate_bundle()
        return {"message": "Support bundle generated successfully", "path": bundle_path, "filename": os.path.basename(bundle_path)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate support bundle: {str(e)}"
        )

@router.get("/bundle/latest")
async def get_latest_support_bundle(
    admin_token: str = Depends(get_admin_token)
):
    """
    Retrieve the latest generated support bundle.
    """
    service = SupportBundleService()
    bundle_path = service.get_latest_bundle()
    if not bundle_path or not os.path.exists(bundle_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No support bundle found. Please generate one first."
        )
    
    return FileResponse(
        path=bundle_path,
        filename=os.path.basename(bundle_path),
        media_type="application/gzip"
    )
