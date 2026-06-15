from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


class ConfigEntryData(BaseModel):
    key: str
    value: Any
    scope: str = "global"


@runtime_checkable
class ConfigRepository(Protocol):
    async def get_config(self, key: str, scope: str = "global") -> ConfigEntryData | None: ...
    async def set_config(self, entry: ConfigEntryData) -> None: ...
    async def list_configs(self, scope: str = "global") -> list[ConfigEntryData]: ...
