import fnmatch
import hashlib
import os
from typing import Any

from ..sanitizer import Sanitizer
from .ast_index import PythonASTParser
from .storage import IndexStorage
from .symbol_index import RegexFallbackParser

DEFAULT_IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".llm_harness_index",
    ".llm_harness_memory",
    ".llm_harness_cache",
    ".cache",
    "artifacts",
}


class RepositoryIndexer:
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = workspace_root
        self.storage = IndexStorage(workspace_root)
        self.py_parser = PythonASTParser()
        self.regex_parser = RegexFallbackParser()

    def build_index(self) -> dict[str, Any]:
        ignore_patterns = self._load_gitignore_patterns()
        indexed_files = {}

        for root, dirs, files in os.walk(self.workspace_root):
            dirs[:] = [d for d in dirs if d not in DEFAULT_IGNORED_DIRS and not d.startswith(".")]

            for file in files:
                if file.startswith("."):
                    continue
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, self.workspace_root)

                if self._is_ignored(rel_path, ignore_patterns):
                    continue

                try:
                    size = os.path.getsize(full_path)
                    if size > 2 * 1024 * 1024:
                        continue
                except OSError:
                    continue

                try:
                    with open(full_path, errors="ignore") as f:
                        content = f.read()
                except Exception:
                    continue

                sanitized_content = Sanitizer.sanitize_text(content)

                content_hash = hashlib.sha256(
                    sanitized_content.encode("utf-8", errors="ignore")
                ).hexdigest()
                mtime = os.path.getmtime(full_path)

                ext = os.path.splitext(file)[1].lower()
                language = "unknown"
                symbols_data: dict[str, Any] = {"classes": [], "functions": [], "imports": []}

                if ext == ".py":
                    language = "python"
                    symbols_data = self.py_parser.parse(sanitized_content)
                elif ext in (".js", ".jsx"):
                    language = "javascript"
                    symbols_data = self.regex_parser.parse(sanitized_content)
                elif ext in (".ts", ".tsx"):
                    language = "typescript"
                    symbols_data = self.regex_parser.parse(sanitized_content)
                elif ext == ".java":
                    language = "java"
                    symbols_data = self.regex_parser.parse(sanitized_content)
                elif ext == ".cs":
                    language = "csharp"
                    symbols_data = self.regex_parser.parse(sanitized_content)
                elif ext == ".html":
                    language = "html"
                elif ext == ".css":
                    language = "css"
                elif ext == ".md":
                    language = "markdown"

                sym_names = []
                for c in symbols_data.get("classes", []):
                    sym_names.append(c["name"])
                    for m in c.get("methods", []):
                        sym_names.append(m["name"])
                for f in symbols_data.get("functions", []):
                    sym_names.append(f["name"])

                indexed_files[rel_path] = {
                    "path": rel_path,
                    "language": language,
                    "size": size,
                    "hash": content_hash,
                    "modified_time": mtime,
                    "imports": symbols_data.get("imports", []),
                    "symbols": list(set(sym_names)),
                    "ast": symbols_data,
                }

        self.storage.save_json("repo_index.json", indexed_files)
        return indexed_files

    def _load_gitignore_patterns(self) -> list[str]:
        patterns = []
        path = os.path.join(self.workspace_root, ".gitignore")
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            patterns.append(line)
            except Exception:
                pass
        return patterns

    def _is_ignored(self, rel_path: str, patterns: list[str]) -> bool:
        for pattern in patterns:
            if pattern.endswith("/"):
                pat = pattern.rstrip("/")
                if (
                    fnmatch.fnmatch(rel_path, pat)
                    or fnmatch.fnmatch(rel_path, pat + "/*")
                    or f"/{pat}/" in f"/{rel_path}/"
                ):
                    return True
            else:
                if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(
                    os.path.basename(rel_path), pattern
                ):
                    return True
        return False
