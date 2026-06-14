from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


class SecurityConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
    )

    admin_token: str = Field(alias="ADMIN_TOKEN", validation_alias=AliasChoices("ADMIN_TOKEN", "ADMIN_TOKEN_FILE"))
    admin_read_token: str | None = Field(default=None, alias="ADMIN_READ_TOKEN", validation_alias=AliasChoices("ADMIN_READ_TOKEN", "ADMIN_READ_TOKEN_FILE"))
    admin_write_token: str | None = Field(default=None, alias="ADMIN_WRITE_TOKEN", validation_alias=AliasChoices("ADMIN_WRITE_TOKEN", "ADMIN_WRITE_TOKEN_FILE"))
    admin_super_token: str | None = Field(default=None, alias="ADMIN_SUPER_TOKEN", validation_alias=AliasChoices("ADMIN_SUPER_TOKEN", "ADMIN_SUPER_TOKEN_FILE"))
    jwt_secret: str = Field(..., alias="JWT_SECRET", validation_alias=AliasChoices("JWT_SECRET", "JWT_SECRET_FILE"))
    rbac_admin_enabled: bool = Field(default=True, alias="RBAC_ADMIN_ENABLED")
    admin_tests_rate_limit_enabled: bool = Field(default=True, alias="ADMIN_TESTS_RATE_LIMIT_ENABLED")

    oauth_google_client_id: str = Field(default="", alias="OAUTH_GOOGLE_CLIENT_ID")
    oauth_google_client_secret: str = Field(default="", alias="OAUTH_GOOGLE_CLIENT_SECRET")
    oauth_github_client_id: str = Field(default="", alias="OAUTH_GITHUB_CLIENT_ID")
    oauth_github_client_secret: str = Field(default="", alias="OAUTH_GITHUB_CLIENT_SECRET")
    oauth_enabled: bool = Field(default=False, alias="OAUTH_ENABLED")

    enterprise_sso_enabled: bool = Field(default=False, alias="ENTERPRISE_SSO_ENABLED")
    enterprise_sso_tenant_id: str = Field(default="", alias="ENTERPRISE_SSO_TENANT_ID")
    enterprise_sso_azure_client_id: str = Field(default="", alias="ENTERPRISE_SSO_AZURE_CLIENT_ID")
    enterprise_sso_azure_client_secret: str = Field(default="", alias="ENTERPRISE_SSO_AZURE_CLIENT_SECRET")
    enterprise_sso_okta_client_id: str = Field(default="", alias="ENTERPRISE_SSO_OKTA_CLIENT_ID")
    enterprise_sso_okta_client_secret: str = Field(default="", alias="ENTERPRISE_SSO_OKTA_CLIENT_SECRET")
    enterprise_sso_okta_domain: str = Field(default="", alias="ENTERPRISE_SSO_OKTA_DOMAIN")
    enterprise_sso_saml_sso_url: str = Field(default="", alias="ENTERPRISE_SSO_SAML_SSO_URL")
    enterprise_sso_saml_entity_id: str = Field(default="", alias="ENTERPRISE_SSO_SAML_ENTITY_ID")
    enterprise_sso_saml_certificate: str = Field(default="", alias="ENTERPRISE_SSO_SAML_CERTIFICATE")

    pki_enabled: bool = Field(default=False, alias="PKI_ENABLED")
    pki_storage_path: str = Field(default="./data/pki", alias="PKI_STORAGE_PATH")
    pki_ca_rotation_days: int = Field(default=365, alias="PKI_CA_ROTATION_DAYS")
    pki_cert_rotation_days: int = Field(default=90, alias="PKI_CERT_ROTATION_DAYS")
    hardware_trust_enabled: bool = Field(default=False, alias="HARDWARE_TRUST_ENABLED")
    hardware_trust_provider: str = Field(default="mock", alias="HARDWARE_TRUST_PROVIDER")
    attestation_mode: str = Field(default="advisory", alias="ATTESTATION_MODE")

    secrets_manager_provider: str = Field(default="vault", alias="SECRETS_MANAGER_PROVIDER")
    vault_addr: str = Field(default="http://localhost:8200", alias="VAULT_ADDR")
    vault_token: str = Field(default="", alias="VAULT_TOKEN")
    vault_kv_mount: str = Field(default="secret", alias="VAULT_KV_MOUNT")
