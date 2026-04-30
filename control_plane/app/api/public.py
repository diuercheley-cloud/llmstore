from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db_session
from app.schemas.public import PublicSignupRequest, PublicSignupResponse
from app.services.public_onboarding import create_public_signup, list_public_plans

router = APIRouter(tags=["public"])
settings = get_settings()
static_dir = Path(__file__).resolve().parents[1] / "static" / "www"


def _base_url(request: Request) -> str:
    if settings.public_base_url:
        return settings.public_base_url.rstrip("/")
    return str(request.base_url).rstrip("/")


@router.get("/", include_in_schema=False)
async def landing_page():
    return FileResponse(static_dir / "index.html")


@router.get("/pricing", include_in_schema=False)
async def pricing_page():
    return FileResponse(static_dir / "pricing.html")


@router.get("/signup", include_in_schema=False)
async def signup_page():
    return FileResponse(static_dir / "signup.html")


@router.get("/public/plans")
async def public_plans(session: AsyncSession = Depends(get_db_session)):
    return {"brand_name": settings.public_brand_name, "plans": await list_public_plans(session)}


@router.post("/public/signup", response_model=PublicSignupResponse, status_code=201)
async def public_signup(
    payload: PublicSignupRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    if not settings.public_signup_enabled:
        raise HTTPException(status_code=404, detail="public signup disabled")
    client, plan, api_key, plaintext = await create_public_signup(session, payload)
    base_url = _base_url(request)
    return PublicSignupResponse(
        client_id=str(client.id),
        account_name=client.name,
        plan_code=plan.code,
        plan_name=plan.name,
        api_key=plaintext,
        api_key_prefix=api_key.key_prefix,
        portal_url=f"{base_url}/client-portal",
        api_base_url=f"{base_url}/v1",
        support_email=settings.public_support_email,
        next_steps=[
            "Open the client portal with the API key returned in this response.",
            "Call /v1/models to confirm access and list enabled models.",
            "Store the API key now. It is only returned once.",
        ],
    )
