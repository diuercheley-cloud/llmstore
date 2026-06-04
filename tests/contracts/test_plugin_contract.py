import pytest
from app.contracts.plugin import PluginCapabilities, PluginContract, PluginManifest


class MockPluginLoader(PluginContract):
    async def load_plugin(self, manifest: PluginManifest, plugin_binary: bytes):
        return {"name": manifest.name, "status": "loaded"}

    async def validate_manifest(self, manifest: PluginManifest) -> bool:
        return True

    def capabilities(self) -> PluginCapabilities:
        return PluginCapabilities(sandbox_execution=True)

    def validate_contract(self) -> bool:
        return True

@pytest.mark.asyncio
async def test_plugin_contract_implementation():
    loader = MockPluginLoader()
    assert loader.validate_contract() is True
    
    manifest = PluginManifest(
        name="test-plugin",
        version="1.0.0",
        entrypoint="main.py",
        permissions=["read"],
        sha256="abc"
    )
    result = await loader.load_plugin(manifest, b"binary")
    assert result["name"] == "test-plugin"
    
    caps = loader.capabilities()
    assert caps.sandbox_execution is True
