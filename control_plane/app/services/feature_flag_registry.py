import os
import re
import yaml
from typing import List, Dict, Any, Tuple, Optional

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
            if status not in ("active", "deprecated", "experimental", "internal"):
                errors.append(f"Flag '{name}' has invalid status: {status}.")
                
            # 4. Deprecated validation (must have replacement or remove_after)
            if status == "deprecated":
                remove_after = f.get("remove_after")
                replacement = f.get("replacement")
                if not remove_after and not replacement:
                    errors.append(f"Deprecated flag '{name}' must have a 'remove_after' date or a 'replacement' flag.")
                    
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
        
        # Get all boolean settings fields from Settings class to filter out non-boolean settings
        from app.core.config import Settings
        bool_settings_keys = set()
        for field_name, field_info in Settings.model_fields.items():
            field_type = field_info.annotation
            type_str = str(field_type).lower()
            if "bool" in type_str:
                bool_settings_keys.add(field_name.upper())

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
                    # Filter: only keep if it is a boolean setting field
                    if key in bool_settings_keys:
                        env_keys.add(key)

        # 2. Scan codebase for setting usage (e.g. settings.SOME_FLAG)
        code_keys = set()
        settings_pattern = re.compile(r"(?:settings|get_settings\(\))\s*\.\s*([A-Za-z0-9_]+)")
        env_get_pattern = re.compile(r"os\s*\.\s*environ\s*\[\s*['\"]([A-Za-z0-9_]+)['\"]")
        env_get_opt_pattern = re.compile(r"os\s*\.\s*getenv\s*\(\s*['\"]([A-Za-z0-9_]+)['\"]")
        
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
                except Exception:
                    pass

        # 3. Load registered flags
        flags = self.load_registry()
        registered_keys = {f.get("name", "").upper() for f in flags if f.get("name")}

        # 4. Calculate orphans and missing
        # Registered but not in code or env
        orphans = []
        for r_key in sorted(registered_keys):
            if r_key not in code_keys and r_key not in env_keys:
                orphans.append(r_key)

        # In env/code but not registered
        missing_registration = []
        # Filter code_keys to only include boolean feature flags
        for c_key in sorted(code_keys):
            if c_key in bool_settings_keys:
                if c_key not in registered_keys:
                    missing_registration.append(c_key)
                    
        for e_key in sorted(env_keys):
            if e_key not in registered_keys:
                if e_key not in missing_registration:
                    missing_registration.append(e_key)

        return {
            "orphans": orphans,
            "missing_registration": missing_registration,
            "code_references_count": len(code_keys),
            "env_references_count": len(env_keys),
            "registered_count": len(registered_keys)
        }

