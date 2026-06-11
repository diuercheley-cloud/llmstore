import pytest
from app.domains.config.contracts import ConfigRepository, ConfigEntryData
from app.domains.config.repositories import InMemoryConfigRepository

@pytest.mark.asyncio
async def test_config_repository_contract():
    repo = InMemoryConfigRepository()
    assert isinstance(repo, ConfigRepository)

@pytest.mark.asyncio
async def test_in_memory_config_flow():
    repo = InMemoryConfigRepository()
    entry = ConfigEntryData(key="test_key", value="test_value")
    await repo.set_config(entry)
    
    fetched = await repo.get_config("test_key")
    assert fetched.value == "test_value"
    
    configs = await repo.list_configs()
    assert len(configs) == 1
    assert configs[0].key == "test_key"
