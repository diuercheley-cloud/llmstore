from datetime import datetime, UTC
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
import uuid

class BackupComponent(BaseModel):
    name: str
    description: str
    item_count: int
    data_hash: str

class BackupManifest(BaseModel):
    backup_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    schema_version: str = "1.0.0"
    components: List[BackupComponent] = Field(default_factory=list)
    encryption_status: str = "redacted" # redacted | encrypted | clear (not allowed)
    signature_status: str = "placeholder"
    pitr_supported: bool = False
    metadata: Dict[str, str] = Field(default_factory=dict)

class BackupSummary(BaseModel):
    id: str
    created_at: datetime
    component_count: int
    status: str
