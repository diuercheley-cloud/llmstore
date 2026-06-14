import secrets
from datetime import datetime, timedelta, timezone

import httpx
from app.core.config import get_settings
from app.services.runtime_dependencies import get_db_session
from app.models.core.auth import OAuthState, UserSession
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["auth"])


class AuthURLResponse(BaseModel):
    url: str
    state: str


class LoginResponse(BaseModel):
    token: str
    email: str
    name: str | None
    role: str = "admin"


class ErrorResponse(BaseModel):
    detail: str


def _generate_session_token() -> str:
    return "sess_" + secrets.token_hex(32)


@router.get("/login/{provider}", response_model=AuthURLResponse)
async def login_oauth(provider: str, request: Request, session: AsyncSession = Depends(get_db_session)):
    settings = get_settings()

    if provider == "google":
        client_id = settings.oauth_google_client_id
        auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        scope = "openid email profile"
    elif provider == "github":
        client_id = settings.oauth_github_client_id
        auth_url = "https://github.com/login/oauth/authorize"
        scope = "read:user user:email"
    else:
        raise HTTPException(status_code=400, detail=f"unsupported provider: {provider}")

    if not client_id:
        raise HTTPException(status_code=501, detail=f"OAuth {provider} not configured")

    state_value = secrets.token_urlsafe(32)
    redirect_uri = str(request.base_url).rstrip("/") + f"/auth/callback/{provider}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    oauth_state = OAuthState(
        provider=provider,
        state=state_value,
        redirect_uri=redirect_uri,
        expires_at=expires_at,
    )
    session.add(oauth_state)
    await session.commit()

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "state": state_value,
        "access_type": "online",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return AuthURLResponse(url=f"{auth_url}?{query}", state=state_value)


class CallbackRequest(BaseModel):
    code: str
    state: str


@router.post("/callback/{provider}")
async def callback_oauth(
    provider: str,
    payload: CallbackRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    settings = get_settings()

    result = await session.execute(
        select(OAuthState).where(
            OAuthState.provider == provider,
            OAuthState.state == payload.state,
            OAuthState.used == False,
            OAuthState.expires_at > datetime.now(timezone.utc),
        )
    )
    oauth_state = result.scalar_one_or_none()
    if not oauth_state:
        raise HTTPException(status_code=400, detail="invalid or expired state")

    oauth_state.used = True

    if provider == "google":
        token_data = {
            "code": payload.code,
            "client_id": settings.oauth_google_client_id,
            "client_secret": settings.oauth_google_client_secret,
            "redirect_uri": oauth_state.redirect_uri,
            "grant_type": "authorization_code",
        }
        async with httpx.AsyncClient() as client:
            token_resp = await client.post("https://oauth2.googleapis.com/token", data=token_data)
            if not token_resp.is_success:
                raise HTTPException(status_code=400, detail="token exchange failed")
            token_json = token_resp.json()
            access_token = token_json.get("access_token")

            user_resp = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if not user_resp.is_success:
                raise HTTPException(status_code=400, detail="failed to get user info")
            user_info = user_resp.json()

        provider_user_id = user_info.get("id")
        email = user_info.get("email", "")
        name = user_info.get("name", "")
        avatar = user_info.get("picture")

    elif provider == "github":
        token_data = {
            "code": payload.code,
            "client_id": settings.oauth_github_client_id,
            "client_secret": settings.oauth_github_client_secret,
            "redirect_uri": oauth_state.redirect_uri,
        }
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                "https://github.com/login/oauth/access_token",
                data=token_data,
                headers={"Accept": "application/json"},
            )
            if not token_resp.is_success:
                raise HTTPException(status_code=400, detail="token exchange failed")
            token_json = token_resp.json()
            access_token = token_json.get("access_token")

            user_resp = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            if not user_resp.is_success:
                raise HTTPException(status_code=400, detail="failed to get user info")
            user_info = user_resp.json()

        provider_user_id = str(user_info.get("id"))
        email = user_info.get("email", "")
        name = user_info.get("login", "")
        avatar = user_info.get("avatar_url")

        if not email:
            emails_resp = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if emails_resp.is_success:
                emails = emails_resp.json()
                primary = next((e for e in emails if e.get("primary")), None)
                if primary:
                    email = primary.get("email", "")
    else:
        raise HTTPException(status_code=400, detail=f"unsupported provider: {provider}")

    if not email:
        raise HTTPException(status_code=400, detail="email not provided by provider")

    session_token = _generate_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    user_session = UserSession(
        provider=provider,
        provider_user_id=provider_user_id,
        email=email,
        name=name,
        avatar_url=avatar,
        session_token=session_token,
        expires_at=expires_at,
    )
    session.add(user_session)
    await session.commit()

    frontend_url = str(request.base_url).rstrip("/") + "/admin-dashboard/login"
    return RedirectResponse(
        url=f"{frontend_url}#sso_token={session_token}&email={email}",
        status_code=302,
    )


@router.get("/me")
async def get_current_session(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    token = request.headers.get("x-session-token", "")
    if not token:
        raise HTTPException(status_code=401, detail="missing session token")
    result = await session.execute(
        select(UserSession).where(
            UserSession.session_token == token,
            UserSession.is_active == True,
            UserSession.expires_at > datetime.now(timezone.utc),
        )
    )
    user_session = result.scalar_one_or_none()
    if not user_session:
        raise HTTPException(status_code=401, detail="invalid or expired session")
    user_session.last_used_at = datetime.now(timezone.utc)
    await session.commit()
    return {
        "email": user_session.email,
        "name": user_session.name,
        "provider": user_session.provider,
        "avatar_url": user_session.avatar_url,
    }
