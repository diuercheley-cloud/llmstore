# Owner: platform-ops
import uuid

from app.api.dependencies import get_current_admin, get_db
from app.services.plugins.plugin_marketplace import PluginMarketplaceService
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/plugins", tags=["plugin_marketplace"])


class ReviewCreate(BaseModel):
    version: str
    rating: int = Field(..., ge=1, le=5)
    review_text: str | None = None


class PluginSettingsUpdate(BaseModel):
    config: dict | None = None


@router.get("/marketplace")
async def list_marketplace(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin),
):
    service = PluginMarketplaceService(db)
    return await service.list_marketplace()


@router.post("/install")
async def install_plugin(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin),
):
    service = PluginMarketplaceService(db)
    content = await file.read()
    try:
        install = await service.install_plugin(content, file.filename or "plugin.zip")
        return install
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{install_id}/enable")
async def enable_plugin(
    install_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin),
):
    service = PluginMarketplaceService(db)
    try:
        await service.enable_plugin(install_id)
        return {"status": "enabled"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{install_id}/disable")
async def disable_plugin(
    install_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin),
):
    service = PluginMarketplaceService(db)
    try:
        await service.disable_plugin(install_id)
        return {"status": "disabled"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{install_id}/upgrade")
async def upgrade_plugin(
    install_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin),
):
    service = PluginMarketplaceService(db)
    content = await file.read()
    try:
        install = await service.upgrade_plugin(install_id, content, file.filename or "plugin.zip")
        return install
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{install_id}")
async def uninstall_plugin(
    install_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin),
):
    service = PluginMarketplaceService(db)
    try:
        await service.uninstall_plugin(install_id)
        return {"status": "uninstalled"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{install_id}/trust-report")
async def get_trust_report(
    install_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin),
):
    service = PluginMarketplaceService(db)
    report = await service.get_trust_report(install_id)
    if not report:
        raise HTTPException(
            status_code=404, detail="Trust report not found for this plugin version"
        )
    return report


@router.get("/{entry_id}/versions")
async def list_plugin_versions(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin),
):
    service = PluginMarketplaceService(db)
    return await service.list_versions(entry_id)


@router.get("/installs")
async def list_installs(
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin),
):
    service = PluginMarketplaceService(db)
    return await service.list_installs()


@router.post("/{entry_id}/reviews")
async def add_plugin_review(
    entry_id: uuid.UUID,
    review: ReviewCreate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin),
):
    service = PluginMarketplaceService(db)
    try:
        created = await service.add_review(
            entry_id,
            version=review.version,
            rating=review.rating,
            review_text=review.review_text,
        )
        return created
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{entry_id}/reviews")
async def list_plugin_reviews(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin),
):
    service = PluginMarketplaceService(db)
    return await service.list_reviews(entry_id)
