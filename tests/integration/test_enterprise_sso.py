"""Tests for Enterprise SSO — SAML, Azure AD, and Okta login/callback flows."""

import base64
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.api.enterprise_sso import EnterpriseSSOService
from app.api.enterprise_sso import router as enterprise_sso_router
from app.core.config import get_settings
from app.db.session import get_db_session
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def setup_env():
    os.environ["ENTERPRISE_SSO_ENABLED"] = "true"
    os.environ["ENTERPRISE_SSO_TENANT_ID"] = "test-tenant-id"
    os.environ["ENTERPRISE_SSO_AZURE_CLIENT_ID"] = "azure-test-client"
    os.environ["ENTERPRISE_SSO_AZURE_CLIENT_SECRET"] = "azure-test-secret"
    os.environ["ENTERPRISE_SSO_OKTA_CLIENT_ID"] = "okta-test-client"
    os.environ["ENTERPRISE_SSO_OKTA_CLIENT_SECRET"] = "okta-test-secret"
    os.environ["ENTERPRISE_SSO_SAML_SSO_URL"] = "https://saml.example.com/sso"
    os.environ["ENTERPRISE_SSO_SAML_ENTITY_ID"] = "https://app.example.com"
    os.environ["ENTERPRISE_SSO_SAML_CERTIFICATE"] = "test-cert"
    os.environ["ENTERPRISE_SSO_OKTA_DOMAIN"] = "test.okta.com"
    os.environ["FRONTEND_URL"] = "http://localhost:5173"
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestEnterpriseSSOService:
    def test_get_provider_config_azure_ad(self):
        svc = EnterpriseSSOService()
        config = svc.get_provider_config("azure-ad")
        assert config["base_url"] == "https://login.microsoftonline.com/test-tenant-id"
        assert config["auth_endpoint"] == "/oauth2/v2.0/authorize"

    def test_get_provider_config_okta(self):
        svc = EnterpriseSSOService()
        config = svc.get_provider_config("okta")
        assert config["base_url"] == "https://test.okta.com"
        assert config["auth_endpoint"] == "/oauth2/v1/authorize"

    def test_get_provider_config_saml(self):
        svc = EnterpriseSSOService()
        config = svc.get_provider_config("saml")
        assert config["sso_url"] == "https://saml.example.com/sso"
        assert config["entity_id"] == "https://app.example.com"

    def test_get_provider_config_unknown(self):
        svc = EnterpriseSSOService()
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            svc.get_provider_config("unknown-provider")
        assert exc.value.status_code == 400

    def test_build_login_url_azure_ad(self):
        svc = EnterpriseSSOService()
        url = svc.build_login_url("azure-ad", "http://localhost/callback", "test-state")
        assert "login.microsoftonline.com" in url
        assert "client_id=azure-test-client" in url
        assert "response_type=code" in url
        assert "state=test-state" in url

    def test_build_login_url_okta(self):
        svc = EnterpriseSSOService()
        url = svc.build_login_url("okta", "http://localhost/callback", "test-state")
        assert "test.okta.com" in url
        assert "client_id=okta-test-client" in url
        assert "state=test-state" in url

    def test_build_login_url_saml(self):
        svc = EnterpriseSSOService()
        url = svc.build_login_url("saml", "http://localhost/callback", "test-state")
        assert "SAMLRequest=" in url
        assert "RelayState=test-state" in url
        assert url.startswith("https://saml.example.com/sso")

    def test_build_saml_request_xml_structure(self):
        svc = EnterpriseSSOService()
        saml_xml = svc._build_saml_request(
            "https://app.example.com", "https://saml.example.com/sso"
        )
        assert '<?xml version="1.0" encoding="UTF-8"?>' in saml_xml
        assert "<saml2p:AuthnRequest" in saml_xml
        assert 'Version="2.0"' in saml_xml

    def test_client_id_and_secret_azure(self):
        svc = EnterpriseSSOService()
        assert svc._get_client_id("azure-ad") == "azure-test-client"
        assert svc._get_client_secret("azure-ad") == "azure-test-secret"

    def test_client_id_and_secret_okta(self):
        svc = EnterpriseSSOService()
        assert svc._get_client_id("okta") == "okta-test-client"
        assert svc._get_client_secret("okta") == "okta-test-secret"

    def test_client_id_unknown_provider(self):
        svc = EnterpriseSSOService()
        assert svc._get_client_id("unknown") == ""


@pytest.mark.asyncio
async def test_exchange_code_azure_ad():
    svc = EnterpriseSSOService()

    class FakeResponse:
        def __init__(self, data, status=200):
            self._data = data
            self.status_code = status
            self.text = str(data)

        def json(self):
            return self._data

    token_resp = FakeResponse({"access_token": "test-token"})
    userinfo_resp = FakeResponse(
        {"email": "user@example.com", "name": "Test User", "sub": "user-123"}
    )

    async def mock_context_manager(self):
        return self

    with patch("httpx.AsyncClient") as mock_client_cls:
        instance = MagicMock()
        instance.__aenter__.return_value = instance
        instance.post = AsyncMock(side_effect=[token_resp])
        instance.get = AsyncMock(side_effect=[userinfo_resp])
        mock_client_cls.return_value = instance

        result = await svc.exchange_code("azure-ad", "test-code", "http://localhost/callback")
        assert result["email"] == "user@example.com"
        assert result["name"] == "Test User"
        assert result["provider_user_id"] == "user-123"


class TestSAMLHandling:
    @pytest.mark.asyncio
    async def test_exchange_code_saml_success(self):
        svc = EnterpriseSSOService()
        saml_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<saml2p:Response xmlns:saml2p="urn:oasis:names:tc:SAML:2.0:protocol"'
            ' xmlns:saml2="urn:oasis:names:tc:SAML:2.0:assertion">'
            "<saml2:Assertion>"
            "<saml2:Subject><saml2:NameID>user@example.com</saml2:NameID></saml2:Subject>"
            "<saml2:AttributeStatement>"
            '<saml2:Attribute Name="email"><saml2:AttributeValue>user@example.com</saml2:AttributeValue></saml2:Attribute>'
            '<saml2:Attribute Name="name"><saml2:AttributeValue>Test User</saml2:AttributeValue></saml2:Attribute>'
            "</saml2:AttributeStatement>"
            "</saml2:Assertion>"
            "</saml2p:Response>"
        )
        encoded = base64.b64encode(saml_xml.encode()).decode()
        result = await svc.exchange_code("saml", encoded, "http://localhost/callback")
        assert result["email"] == "user@example.com"
        assert result["name"] == "Test User"

    @pytest.mark.asyncio
    async def test_exchange_code_saml_invalid(self):
        svc = EnterpriseSSOService()
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await svc.exchange_code("saml", "invalid-base64!!!", "http://localhost/callback")
        assert exc.value.status_code == 400


class TestEnterpriseSSOEndpoints:
    @pytest.fixture(autouse=True)
    def _setup(self):
        os.environ["ENTERPRISE_SSO_ENABLED"] = "true"
        get_settings.cache_clear()
        yield
        get_settings.cache_clear()

    @pytest.fixture
    def app_with_db(self):
        import app.models.core.auth
        from app.db.base import Base
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

        async def init():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            return engine

        import anyio

        anyio.run(init)

        async def get_test_session():
            async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with async_session() as s:
                yield s

        app = FastAPI()
        app.include_router(enterprise_sso_router)
        app.dependency_overrides[get_db_session] = get_test_session
        return app

    @pytest.mark.asyncio
    async def test_login_endpoint_success(self, app_with_db):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            resp = await client.get("/auth/enterprise/login/azure-ad")
            assert resp.status_code == 200
            data = resp.json()
            assert "url" in data
            assert "state" in data

    @pytest.mark.asyncio
    async def test_login_endpoint_disabled(self):
        os.environ["ENTERPRISE_SSO_ENABLED"] = "false"
        get_settings.cache_clear()
        app = FastAPI()
        app.include_router(enterprise_sso_router)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/auth/enterprise/login/azure-ad")
            assert resp.status_code == 501
        get_settings.cache_clear()

    @pytest.mark.asyncio
    async def test_login_unknown_provider(self, app_with_db):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            resp = await client.get("/auth/enterprise/login/unknown-provider")
            assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_callback_missing_code(self, app_with_db):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            resp = await client.get("/auth/enterprise/callback/azure-ad")
            assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_callback_invalid_state(self, app_with_db):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_db), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/auth/enterprise/callback/azure-ad?code=test-code&state=invalid-state"
            )
            assert resp.status_code == 400
