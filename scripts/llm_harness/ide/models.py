from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ContextRefType(str, Enum):
    FILE = "file"
    FOLDER = "folder"
    SYMBOL = "symbol"
    SELECTION = "selection"

class ContextRef(BaseModel):
    ref_type: ContextRefType
    path: str
    symbol: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None

class ContextBundle(BaseModel):
    files: list[dict[str, Any]] = Field(default_factory=list)
    symbols: list[dict[str, Any]] = Field(default_factory=list)
    selections: list[dict[str, Any]] = Field(default_factory=list)
    token_count: int = 0

    def is_empty(self) -> bool:
        return not self.files and not self.symbols and not self.selections

    def to_text(self) -> str:
        parts = ["=== Context Reference Bundle ==="]
        for f in self.files:
            parts.append(f"--- File: {f['path']} ---")
            parts.append(f.get("content", ""))
            parts.append("")
        for s in self.selections:
            parts.append(
                f"--- Selection: {s['path']} "
                f"(lines {s['start_line']}-{s['end_line']}) ---"
            )
            parts.append(s.get("content", ""))
            parts.append("")
        for sym in self.symbols:
            parts.append(f"--- Symbol: {sym['name']} (in {sym['path']}) ---")
            parts.append(sym.get("content", ""))
            parts.append("")
        return "\n".join(parts)

class InlineEditRequest(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    instruction: str
    context_refs: list[ContextRef] = Field(default_factory=list)
