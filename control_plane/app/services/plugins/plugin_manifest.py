"""Plugin manifest contract for governed catalog/runtime flows."""

# Owner: platform-ops
"""Plugin manifest contract for governed catalog/runtime flows."""

# Owner: platform-ops
from typing import List

from pydantic import BaseModel, Field


class PluginManifest(BaseModel):
    name: str
    version: str
    owner: str
    permissions: List[str] = Field(default_factory=list)
    capabilities: List[str] = Field(default_factory=list)
    risk_level: str = "medium"
    side_effect_level: str = "none"
    runtime: str = "python"
    entrypoint: str
    checksum_sha256: str
