from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from pydantic import BaseModel

class ConfigEntryData(BaseModel):
    key: str
    value: Any
    scope: str = "global"

@runtime_checkable
class ConfigRepository(Protocol):
    async def get_config(self, key: str, scope: str = "global") -> Optional[ConfigEntryData]: ...
    async def set_config(self, entry: ConfigEntryData) -> None: ...
    async def list_configs(self, scope: str = "global") -> List[ConfigEntryData]: ...
