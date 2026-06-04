import os
from pathlib import Path
from typing import Any, Dict, List

from fastapi import HTTPException


class FileService:
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path

    def _safe_path(self, relative_path: str) -> Path:
        # Sanitize path to prevent directory traversal
        target = (self.workspace_path / relative_path).resolve()
        if not str(target).startswith(str(self.workspace_path.resolve())):
            raise HTTPException(status_code=400, detail="Invalid path")
        return target

    async def list_files(self, relative_path: str = "") -> List[Dict[str, Any]]:
        path = self._safe_path(relative_path)
        if not path.is_dir():
            return []
            
        items = []
        for entry in os.scandir(path):
            items.append({
                "name": entry.name,
                "path": os.path.relpath(entry.path, self.workspace_path),
                "is_dir": entry.is_dir(),
                "size": entry.stat().st_size if entry.is_file() else None
            })
        return sorted(items, key=lambda x: (not x["is_dir"], x["name"]))

    async def read_file(self, relative_path: str) -> str:
        path = self._safe_path(relative_path)
        if not path.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    async def write_file(self, relative_path: str, content: str):
        path = self._safe_path(relative_path)
        os.makedirs(path.parent, exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    async def delete_file(self, relative_path: str):
        path = self._safe_path(relative_path)
        if path.is_file():
            os.remove(path)
        elif path.is_dir():
            import shutil
            shutil.rmtree(path)
