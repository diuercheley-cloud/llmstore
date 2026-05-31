"""
Enterprise SSO providers: SAML 2.0, Azure AD (OIDC), Okta (OIDC).
Extends the existing OAuth2 flow (Google/GitHub) in auth.py.
"""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.auth import OAuthState, UserSession

router = APIRouter(prefix="/auth", tags=["auth"])


class AuthURLResponse(BaseModel):
    url: str
    state: str


class LoginResponse(BaseModel):
    token: str
    email: str
    name: str | None
    role: str = "admin"


PROVIDER_CONFIGS = {
    "azure-ad": {
        "auth_endpoint": "/oauth2/v2.0/authorize",
        "token_endpoint": "/oauth2/v2.0/token",
        "scope": "openid email profile",
        "userinfo_endpoint": "/oauth2/v2.0/userinfo",
        "name_field": "name",
        "email_field": "email",
    },
    "okta": {
        "auth_endpoint": "/oauth2/v1/authorize",
        "token_endpoint": "/oauth2/v1/token",
        "scope": "openid email profile",
        "userinfo_endpoint": "/oauth2/v1/userinfo",
        "name_field": "name",
        "email_field": "email",
    },
    "saml": {
        "type": "saml",
    },
}


class EnterpriseSSOService:
    """
    Handles SAML 2.0 and OIDC (Azure AD, Okta) enterprise SSO flows.
    """

    def __init__(self):
        self.settings = get_settings()

    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        if provider not in PROVIDER_CONFIGS:
            raise HTTPException(status_code=400, detail=f"Unsupported enterprise SSO provider: {provider}")

        base = PROVIDER_CONFIGS[provider]
        tenant_id = self.settings.enterprise_sso_tenant_id or "common"

        if provider == "azure-ad":
            base = dict(base)
            base["base_url"] = f"https://login.microsoftonline.com/{tenant_id}"
        elif provider == "okta":
            domain = self.settings.enterprise_sso_okta_domain or "dev-123456.okta.com"
            base = dict(base)
            base["base_url"] = f"https://{domain}"
        elif provider == "saml":
            base = dict(base)
            base["sso_url"] = self.settings.enterprise_sso_saml_sso_url or ""
            base["entity_id"] = self.settings.enterprise_sso_saml_entity_id or ""
            base["certificate"] = self.settings.enterprise_sso_saml_certificate or ""

        return base

    def build_login_url(self, provider: str, redirect_uri: str, state: str) -> str:
        config = self.get_provider_config(provider)

        if provider == "saml":
            import base64
            saml_request = self._build_saml_request(config["entity_id"], config["sso_url"])
            encoded = base64.b64encode(saml_request.encode()).decode()
            return f"{config['sso_url']}?SAMLRequest={encoded}&RelayState={state}"

        client_id = self._get_client_id(provider)
        base_url = config["base_url"]
        auth_url = f"{base_url}{config['auth_endpoint']}"
        scope = config["scope"]

        return (
            f"{auth_url}?client_id={client_id}"
            f"&response_type=code"
            f"&redirect_uri={redirect_uri}"
            f"&scope={scope}"
            f"&state={state}"
            f"&response_mode=query"
        )

    async def exchange_code(self, provider: str, code: str, redirect_uri: str) -> Dict[str, Any]:
        config = self.get_provider_config(provider)

        if provider == "saml":
            return await self._handle_saml_response(code)

        client_id = self._get_client_id(provider)
        client_secret = self._get_client_secret(provider)
        base_url = config["base_url"]

        token_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{base_url}{config['token_endpoint']}",
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=401, detail=f"Token exchange failed: {resp.text}")

            token_json = resp.json()
            access_token = token_json.get("access_token")

            user_resp = await client.get(
                f"{base_url}{config['userinfo_endpoint']}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if user_resp.status_code != 200:
                raise HTTPException(status_code=401, detail="Userinfo fetch failed")

            user_info = user_resp.json()
            return {
                "email": user_info.get(config["email_field"], ""),
                "name": user_info.get(config["name_field"], ""),
                "provider_user_id": user_info.get("sub", user_info.get("oid", "")),
            }

    def _build_saml_request(self, entity_id: str, acs_url: str) -> str:
        import uuid
        request_id = f"_{uuid.uuid4().hex}"
        return (
            f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<saml2p:AuthnRequest xmlns:saml2p="urn:oasis:names:tc:SAML:2.0:protocol" '
            f'ID="{request_id}" Version="2.0" '
            f'IssueInstant="{datetime.utcnow().isoformat()}Z" '
            f'Destination="{acs_url}" '
            f'AssertionConsumerServiceURL="{acs_url}">'
            f'<saml2:Issuer xmlns:saml2="urn:oasis:names:tc:SAML:2.0:assertion">{entity_id}</saml2:Issuer>'
            f'<saml2p:NameIDPolicy Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"/>'
            f'</saml2p:AuthnRequest>'
        )

    async def _handle_saml_response(self, saml_response: str) -> Dict[str, Any]:
        import base64
        from xml.etree import ElementTree

        try:
            decoded = base64.b64decode(saml_response).decode("utf-8")
            root = ElementTree.fromstring(decoded)
            ns = {
                "saml2": "urn:oasis:names:tc:SAML:2.0:assertion",
                "saml2p": "urn:oasis:names:tc:SAML:2.0:protocol",
            }
            attribute_stmt = root.find(".//saml2:AttributeStatement", ns)
            email = ""
            name = ""
            name_id = root.find(".//saml2:NameID", ns)
            if name_id is not None:
                email = name_id.text or ""

            if attribute_stmt is not None:
                for attr in attribute_stmt.findall("saml2:Attribute", ns):
                    attr_name = attr.get("Name", "")
                    attr_value = attr.find("saml2:AttributeValue", ns)
                    val = attr_value.text if attr_value is not None else ""
                    if "email" in attr_name.lower():
                        email = val
                    elif "name" in attr_name.lower():
                        name = val

            return {
                "email": email,
                "name": name,
                "provider_user_id": email,
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"SAML response parsing failed: {e}")

    def _get_client_id(self, provider: str) -> str:
        if provider == "azure-ad":
            return self.settings.enterprise_sso_azure_client_id or ""
        elif provider == "okta":
            return self.settings.enterprise_sso_okta_client_id or ""
        return ""

    def _get_client_secret(self, provider: str) -> str:
        if provider == "azure-ad":
            return self.settings.enterprise_sso_azure_client_secret or ""
        elif provider == "okta":
            return self.settings.enterprise_sso_okta_client_secret or ""
        return ""


@router.get("/enterprise/login/{provider}", response_model=AuthURLResponse)
async def enterprise_login(provider: str, request: Request, session: AsyncSession = Depends(get_db_session)):
    settings = get_settings()
    if not settings.enterprise_sso_enabled:
        raise HTTPException(status_code=501, detail="Enterprise SSO is disabled")

    svc = EnterpriseSSOService()
    state_value = secrets.token_urlsafe(32)
    redirect_uri = str(request.base_url).rstrip("/") + f"/auth/enterprise/callback/{provider}"

    try:
        login_url = svc.build_login_url(provider, redirect_uri, state_value)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build login URL: {e}")

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    db_state = OAuthState(
        provider=provider,
        state=state_value,
        redirect_uri=redirect_uri,
        expires_at=expires_at,
    )
    session.add(db_state)
    await session.commit()

    return AuthURLResponse(url=login_url, state=state_value)


@router.get("/enterprise/callback/{provider}")
async def enterprise_callback(provider: str, request: Request, session: AsyncSession = Depends(get_db_session)):
    settings = get_settings()
    if not settings.enterprise_sso_enabled:
        raise HTTPException(status_code=501, detail="Enterprise SSO is disabled")

    code = request.query_params.get("code") or request.query_params.get("SAMLResponse")
    state = request.query_params.get("state") or request.query_params.get("RelayState")

    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code or SAML response")

    result = await session.execute(
        select(OAuthState).where(OAuthState.state == state, OAuthState.provider == provider)
    )
    db_state = result.scalar_one_or_none()
    if not db_state or db_state.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    if db_state.used:
        raise HTTPException(status_code=400, detail="State already used")

    db_state.used = True

    svc = EnterpriseSSOService()
    redirect_uri = str(request.base_url).rstrip("/") + f"/auth/enterprise/callback/{provider}"

    try:
        user_info = await svc.exchange_code(provider, code, redirect_uri)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auth exchange failed: {e}")

    email = user_info.get("email", "")
    if not email:
        raise HTTPException(status_code=400, detail="Could not retrieve email from provider")

    token = "sess_" + secrets.token_hex(32)
    role = "admin"

    existing = await session.execute(
        select(UserSession).where(
            UserSession.provider_user_id == user_info.get("provider_user_id", email),
            UserSession.email == email,
        )
    )
    existing_user = existing.scalar_one_or_none()
    if existing_user:
        existing_user.session_token = token
        existing_user.expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    else:
        db_session = UserSession(
            provider_user_id=user_info.get("provider_user_id", email),
            email=email,
            name=user_info.get("name"),
            session_token=token,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        session.add(db_session)

    await session.commit()

    frontend_url = settings.frontend_url or "http://localhost:5173"
    return RedirectResponse(
        url=f"{frontend_url}/#/login?sso_token={token}&email={email}",
        status_code=302,
    )
