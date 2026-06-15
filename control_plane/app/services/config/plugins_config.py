from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PluginsConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
    )

    plugin_marketplace_enabled: bool = Field(default=False, alias="PLUGIN_MARKETPLACE_ENABLED")

    marketplace_governance_enabled: bool = Field(
        default=True, alias="MARKETPLACE_GOVERNANCE_ENABLED"
    )
    marketplace_require_security_scan: bool = Field(
        default=True, alias="MARKETPLACE_REQUIRE_SECURITY_SCAN"
    )
    marketplace_require_approval: bool = Field(default=True, alias="MARKETPLACE_REQUIRE_APPROVAL")

    plugin_sbom_policy_decision: str = Field(default="block", alias="PLUGIN_SBOM_POLICY_DECISION")
