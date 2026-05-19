from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from pydantic import BaseModel, Field
from app.contracts.base import BaseContract, ContractCapability

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
