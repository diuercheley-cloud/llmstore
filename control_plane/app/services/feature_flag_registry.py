import os
import re
from typing import Any, Dict, List, Optional, Tuple

import yaml
from app.core.config import get_settings


class FeatureFlagRegistryService:
    def __init__(self, registry_path: Optional[str] = None):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        if registry_path is None:
            registry_path = os.path.join(base_dir, "config/feature-flags.yaml")
        self.registry_path = registry_path

    def load_registry(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.registry_path):
            return []
        with open(self.registry_path, "r", encoding="utf-8") as f:
            try:
                data = yaml.safe_load(f)
                return data if isinstance(data, list) else []
            except Exception:
                return []

    def get_all_flags(self) -> List[Dict[str, Any]]:
        return self.load_registry()

    def get_flag_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        flags = self.load_registry()
        name_upper = name.upper()
        for f in flags:
            if f.get("name", "").upper() == name_upper:
                return f
        return None

    def get_deprecated_flags(self) -> List[Dict[str, Any]]:
        flags = self.load_registry()
        return [f for f in flags if f.get("status") == "deprecated"]

    def validate_registry(self) -> Tuple[bool, List[str]]:
        errors = []
        flags = self.load_registry()
        
        # Build mapping for lookup
        flag_names = {f.get("name", "").upper() for f in flags if f.get("name")}
        
        for f in flags:
            name = f.get("name", "UNNAMED")
            
            # 1. Owner presence validation
            owner = f.get("owner")
            if not owner or str(owner).strip() == "":
                errors.append(f"Flag '{name}' has no owner defined.")
                
            # 2. Area validation
            if not f.get("area"):
                errors.append(f"Flag '{name}' has no area defined.")
                
            # 3. Status validation
            status = f.get("status")
            if status not in ("active", "deprecated", "experimental", "internal", "beta"):
                errors.append(f"Flag '{name}' has invalid status: {status}.")
                
            # 4. Deprecated validation (must have replacement AND remove_after)
            if status == "deprecated":
                remove_after = f.get("remove_after")
                replacement = f.get("replacement")
                if not remove_after or str(remove_after).strip() == "":
                    errors.append(f"Deprecated flag '{name}' must have a 'remove_after' date.")
                if not replacement or str(replacement).strip() == "":
                    errors.append(f"Deprecated flag '{name}' must have a 'replacement' flag or 'none'.")
                    
            # 5. Experimental validation (must be opt-in, default false)
            if status == "experimental":
                default_val = f.get("default")
                if default_val is not False:
                    errors.append(f"Experimental flag '{name}' must be opt-in (default must be false).")
                    
            # 6. Risk Level validation
            risk = f.get("risk_level")
            if risk not in ("low", "medium", "high"):
                errors.append(f"Flag '{name}' has invalid risk_level: {risk}.")
                
            # 7. High-risk validation (must be default false)
            if risk == "high":
                default_val = f.get("default")
                if default_val is not False:
                    errors.append(f"High-risk flag '{name}' must be disabled by default (default must be false).")
                    
            # 8. Dependency check (must exist in registry)
            dependencies = f.get("dependencies", [])
            for dep in dependencies:
                if dep.upper() not in flag_names:
                    errors.append(f"Flag '{name}' depends on unregistered flag '{dep}'.")
                    
            # 9. Conflict check (must exist in registry)
            conflicts = f.get("conflicts", [])
            for conf in conflicts:
                if conf.upper() not in flag_names:
                    errors.append(f"Flag '{name}' conflicts with unregistered flag '{conf}'.")
                    
        return len(errors) == 0, errors

    def detect_active_conflicts(self) -> List[Dict[str, Any]]:
        """
        Detects active conflicts where two conflicting flags are both enabled in settings.
        """
        settings = get_settings()
        flags = self.load_registry()
        
        # Build mapping of lowercase name -> value from settings
        settings_vals = {}
        for k, v in settings.__dict__.items():
            settings_vals[k.upper()] = v
            
        active_conflicts = []
        for f in flags:
            name = f.get("name", "").upper()
            conflicts = f.get("conflicts", [])
            
            # Check if this flag is active/enabled in environment
            if settings_vals.get(name) is True:
                for conf in conflicts:
                    conf_upper = conf.upper()
                    # Check if the conflicting flag is also enabled
                    if settings_vals.get(conf_upper) is True:
                        active_conflicts.append({
                            "flag_a": name,
                            "flag_b": conf_upper,
                            "message": f"Conflict detected: both '{name}' and '{conf_upper}' are enabled in the environment."
                        })
                        
        return active_conflicts

    def scan_orphans(self) -> Dict[str, Any]:
        """
        Scans the codebase and configuration to find orphaned flags.
        """
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))

        settings_model = type(get_settings())
        model_fields = getattr(settings_model, "model_fields", None) or getattr(settings_model, "__fields__", {})
        settings_keys = set()
        bool_settings_keys = set()
        alias_to_field = {}
        for field_name, field_info in model_fields.items():
            settings_keys.add(field_name.upper())
            field_type = getattr(field_info, "annotation", None) or getattr(field_info, "type_", None)
            if "bool" in str(field_type).lower():
                bool_settings_keys.add(field_name.upper())
            alias = getattr(field_info, "alias", None)
            if alias:
                alias_upper = str(alias).upper()
                alias_to_field[alias_upper] = field_name.upper()
                settings_keys.add(alias_upper)
                if "bool" in str(field_type).lower():
                    bool_settings_keys.add(alias_upper)
            validation_alias = getattr(field_info, "validation_alias", None)
            if validation_alias is not None:
                alias_repr = str(validation_alias)
                for alias in re.findall(r"'([A-Z0-9_]+)'", alias_repr):
                    alias_to_field[alias.upper()] = field_name.upper()
                    settings_keys.add(alias.upper())
                    if "bool" in str(field_type).lower():
                        bool_settings_keys.add(alias.upper())

        # 1. Parse .env.example
        env_example_path = os.path.join(base_dir, ".env.example")
        env_keys = set()
        if os.path.exists(env_example_path):
            with open(env_example_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key = line.split("=", 1)[0].strip().upper()
                    canonical = alias_to_field.get(key, key)
                    if key in settings_keys or canonical in settings_keys:
                        env_keys.add(key)
                        env_keys.add(canonical)

        # 2. Scan codebase for setting usage (e.g. settings.SOME_FLAG)
        code_keys = set()
        settings_pattern = re.compile(r"(?:settings|get_settings\(\))\s*\.\s*([A-Za-z0-9_]+)")
        env_get_pattern = re.compile(r"os\s*\.\s*environ\s*\[\s*['\"]([A-Za-z0-9_]+)['\"]")
        env_get_opt_pattern = re.compile(r"os\s*\.\s*getenv\s*\(\s*['\"]([A-Za-z0-9_]+)['\"]")
        getattr_pattern = re.compile(r"getattr\s*\([^,]+,\s*['\"]([A-Za-z0-9_]+)['\"]")
        
        # Avoid scanning virtual environments, build artifacts, git
        exclude_dirs = {".git", "venv", ".venv", "__pycache__", "node_modules", "artifacts", "brain"}
        
        for root, dirs, files in os.walk(base_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for file in files:
                if not file.endswith(".py"):
                    continue
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        # Find all matches
                        for m in settings_pattern.finditer(content):
                            code_keys.add(m.group(1).upper())
                        for m in env_get_pattern.finditer(content):
                            code_keys.add(m.group(1).upper())
                        for m in env_get_opt_pattern.finditer(content):
                            code_keys.add(m.group(1).upper())
                        for m in getattr_pattern.finditer(content):
                            code_keys.add(m.group(1).upper())
                except Exception:
                    pass

        normalized_code_keys = set()
        for key in code_keys:
            normalized_code_keys.add(key)
            normalized_code_keys.add(alias_to_field.get(key, key))
        code_keys = normalized_code_keys

        # 2.5 Scan docs for mentions
        doc_keys = set()
        docs_dir = os.path.join(base_dir, "docs")
        if os.path.exists(docs_dir):
            for root, dirs, files in os.walk(docs_dir):
                for file in files:
                    if not file.endswith(".md"): continue
                    path = os.path.join(root, file)
                    try:
                        with open(path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            # Find uppercase flags like AGENT_... or COMMERCIAL_...
                            for m in re.finditer(r"\b([A-Z][A-Z0-9_]{10,})\b", content):
                                flag = m.group(1)
                                if "ENABLED" in flag or "MODE" in flag or "PROVIDER" in flag:
                                    doc_keys.add(flag.upper())
                    except Exception: pass

        # 3. Load registered flags
        flags = self.load_registry()
        registered_keys = {f.get("name", "").upper() for f in flags if f.get("name")}

        # 4. Calculate orphans and missing
        # Registered but not in code, env or docs
        orphans = []
        for r_key in sorted(registered_keys):
            if r_key not in code_keys and r_key not in env_keys and r_key not in doc_keys:
                orphans.append(r_key)

        # In env/code but not registered
        missing_registration = []
        for c_key in sorted(code_keys):
            if c_key in bool_settings_keys:
                if c_key not in registered_keys:
                    missing_registration.append(c_key)
                    
        for e_key in sorted(env_keys):
            if e_key in bool_settings_keys and e_key not in registered_keys:
                if e_key not in missing_registration:
                    missing_registration.append(e_key)

        for d_key in sorted(doc_keys):
            if d_key not in registered_keys and d_key not in missing_registration:
                # Basic check if it's likely a flag
                if d_key in settings_keys or d_key.startswith("AGENT_") or d_key.startswith("COMMERCIAL_"):
                    missing_registration.append(d_key)

        return {
            "orphans": orphans,
            "missing_registration": missing_registration,
            "code_references_count": len(code_keys),
            "env_references_count": len(env_keys),
            "doc_references_count": len(doc_keys),
            "registered_count": len(registered_keys)
        }
