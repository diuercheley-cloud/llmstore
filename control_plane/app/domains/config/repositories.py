from .contracts import ConfigEntryData


class InMemoryConfigRepository:
    def __init__(self):
        self.configs = {}

    async def get_config(self, key: str, scope: str = "global") -> ConfigEntryData | None:
        val = self.configs.get(f"{scope}:{key}")
        if val is None:
            return None
        return ConfigEntryData(key=key, value=val, scope=scope)

    async def set_config(self, entry: ConfigEntryData) -> None:
        self.configs[f"{entry.scope}:{entry.key}"] = entry.value

    async def list_configs(self, scope: str = "global") -> list[ConfigEntryData]:
        return [
            ConfigEntryData(key=k.split(":")[1], value=v, scope=scope)
            for k, v in self.configs.items()
            if k.startswith(f"{scope}:")
        ]
