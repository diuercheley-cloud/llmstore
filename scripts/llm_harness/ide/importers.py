import json
import os
import re
from glob import glob
from typing import Any, Dict, Optional

from ..sanitizer import Sanitizer


def load_json_file(file_path: str) -> Optional[Any]:
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        # strip comments (both single line and multi-line comments)
        content = re.sub(r"//.*$", "", content, flags=re.MULTILINE)
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
        content = re.sub(r",(\s*[}\]])", r"\1", content)
        return json.loads(content)
    except Exception:
        return None

def import_vscode_config(path: str, workspace_root: str = ".") -> Dict[str, Any]:
    settings = None
    keybindings = None
    extensions = None
    cursor_rules_parts = []

    search_dirs = [path]
    if os.path.isdir(path):
        search_dirs.append(os.path.join(path, ".vscode"))
    else:
        parent = os.path.dirname(path)
        if parent:
            search_dirs.append(parent)
            search_dirs.append(os.path.join(parent, ".vscode"))

    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        
        # settings.json
        s_path = os.path.join(d, "settings.json")
        if os.path.isfile(s_path) and settings is None:
            settings = load_json_file(s_path)
            
        # keybindings.json
        k_path = os.path.join(d, "keybindings.json")
        if os.path.isfile(k_path) and keybindings is None:
            keybindings = load_json_file(k_path)
            
        # extensions.json
        e_path = os.path.join(d, "extensions.json")
        if os.path.isfile(e_path) and extensions is None:
            ext_data = load_json_file(e_path)
            if isinstance(ext_data, dict):
                extensions = ext_data.get("recommendations", [])
            elif isinstance(ext_data, list):
                extensions = ext_data

    # Check for .cursorrules
    if os.path.isdir(path):
        cursorrules_path = os.path.join(path, ".cursorrules")
    else:
        cursorrules_path = os.path.join(os.path.dirname(path), ".cursorrules")

    if os.path.isfile(cursorrules_path):
        try:
            with open(cursorrules_path, "r", encoding="utf-8", errors="ignore") as f:
                cursor_rules_parts.append(f.read())
        except Exception:
            pass

    cursor_rules_base = path if os.path.isdir(path) else os.path.dirname(path)
    cursor_rules_dir = os.path.join(cursor_rules_base, ".cursor", "rules")
    if os.path.isdir(cursor_rules_dir):
        for rule_path in sorted(glob(os.path.join(cursor_rules_dir, "*.md"))):
            try:
                with open(rule_path, "r", encoding="utf-8", errors="ignore") as f:
                    cursor_rules_parts.append(f.read())
            except Exception:
                pass

    # Sanitize/redact secrets
    sanitized_settings = Sanitizer.sanitize_data(settings) if settings else {}
    sanitized_keybindings = Sanitizer.sanitize_data(keybindings) if keybindings else []
    sanitized_extensions = Sanitizer.sanitize_data(extensions) if extensions else []
    cursor_rules = "\n\n".join(part.strip() for part in cursor_rules_parts if part.strip())
    sanitized_cursor_rules = Sanitizer.sanitize_text(cursor_rules) if cursor_rules else None

    config_data = {
        "settings": sanitized_settings,
        "keybindings": sanitized_keybindings,
        "extensions": sanitized_extensions,
        "cursor_rules": sanitized_cursor_rules,
    }

    # Save to local file
    out_path = os.path.join(workspace_root, ".llm_harness_ide_config.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)

    return config_data

def get_ide_config(workspace_root: str = ".") -> Dict[str, Any]:
    cfg_path = os.path.join(workspace_root, ".llm_harness_ide_config.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}
