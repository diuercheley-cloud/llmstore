from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from pydantic import BaseModel, Field, field_validator
from app.contracts.base import BaseContract, ContractCapability
from app.contracts.plugin_types import PLUGIN_TYPES, ALLOWED_PERMISSIONS

class ManifestV1(BaseModel):
    manifest_version: str = "1"
    name: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-zA-Z0-9_-]+$")
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    description: str = ""
    author: str = ""
    license: str = "Proprietary"
    entrypoint: str = Field(..., min_length=1)
    plugin_type: str = Field(...)
    permissions: List[str] = []
    checksums: Dict[str, str] = Field(default_factory=dict)
    signature: Optional[str] = None
    certificate_chain: Optional[str] = None
    minimum_platform_version: str = "1.0.0"
    compatibility: Dict[str, List[str]] = Field(default_factory=dict)

    @field_validator("plugin_type")
    @classmethod
    def validate_plugin_type(cls, v: str) -> str:
        if v not in PLUGIN_TYPES:
            raise ValueError(f"Invalid plugin_type '{v}'. Must be one of: {', '.join(sorted(PLUGIN_TYPES))}")
        return v

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, v: List[str]) -> List[str]:
        invalid = set(v) - ALLOWED_PERMISSIONS
        if invalid:
            raise ValueError(f"Invalid permissions: {invalid}. Allowed: {', '.join(sorted(ALLOWED_PERMISSIONS))}")
        return v

class PluginManifest(BaseModel):
    name: str
    version: str
    entrypoint: str
    permissions: List[str]
    sha256: str
    signature: Optional[str] = None
    certificate_chain: Optional[str] = None

class PluginCapabilities(ContractCapability):
    sandbox_execution: bool = False
    network_access: bool = False
    data_access: bool = False

@runtime_checkable
class PluginContract(BaseContract, Protocol):
    """
    Contract for Platform Plugins.
    """
    
    async def load_plugin(self, manifest: PluginManifest, plugin_binary: bytes) -> Any:
        """Validates and registers a new plugin."""
        ...

    async def validate_manifest(self, manifest: PluginManifest) -> bool:
        """Performs deep validation of the plugin manifest."""
        ...

    def capabilities(self) -> PluginCapabilities:
        """Returns capabilities required/offered by the plugin system."""
        ...

    def validate_contract(self) -> bool:
        required_methods = ["load_plugin", "validate_manifest", "capabilities"]
        for method in required_methods:
            if not hasattr(self, method) or not callable(getattr(self, method)):
                return False
        return True
