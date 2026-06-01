import os
import shutil
from pathlib import Path
from typing import List, Optional
from app.core.config import get_settings

settings = get_settings()

class WorkspaceService:
    def __init__(self, tenant_id: str):
        self.tenant_id = str(tenant_id)
        self.base_path = Path(settings.web_ide_workspaces_dir) / self.tenant_id

    async def ensure_workspace(self):
        """
        Ensures the tenant workspace directory exists and has basic structure.
        """
        os.makedirs(self.base_path, exist_ok=True)
        # Create basic folders
        os.makedirs(self.base_path / "agents", exist_ok=True)
        os.makedirs(self.base_path / "tools", exist_ok=True)
        os.makedirs(self.base_path / "plugins", exist_ok=True)
        os.makedirs(self.base_path / "tests", exist_ok=True)
        
        # Create a sample agent manifest if it doesn't exist
        sample_file = self.base_path / "agents" / "sample_agent.yaml"
        if not sample_file.exists():
            with open(sample_file, "w") as f:
                f.write("name: Sample Agent\nversion: 0.1.0\ninstructions: |\n  You are a helpful assistant.\n")
        
        return str(self.base_path)

    async def delete_workspace(self):
        if self.base_path.exists():
            shutil.rmtree(self.base_path)

    def get_path(self) -> Path:
        return self.base_path
