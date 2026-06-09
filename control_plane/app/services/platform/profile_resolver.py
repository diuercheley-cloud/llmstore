"""Resolve supported platform profiles into effective flags."""

# Owner: platform-ops
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

import yaml

logger = logging.getLogger(__name__)

class ProfileResolver:
    def __init__(self, profiles_dir: str = "config/platform-profiles"):
        self.profiles_dir = Path(profiles_dir)
        self.default_profile = "appliance"
        self.schema_path = self.profiles_dir / "schema.yaml"
        self._load_schema()

    def _load_schema(self):
        if self.schema_path.exists():
            with open(self.schema_path, "r", encoding="utf-8") as f:
                self.schema = yaml.safe_load(f) or {}
        else:
            self.schema = {}
        self.valid_flags = self.schema.get("valid_flags", {})

    def resolve(self, profile_name: str = None) -> Dict[str, Any]:
        if not profile_name:
            profile_name = os.getenv("PLATFORM_PROFILE", self.default_profile)

        profile_path = self.profiles_dir / f"{profile_name}.yaml"
        if not profile_path.exists():
             raise ValueError(f"Profile '{profile_name}' not found at {profile_path}")

        with open(profile_path, "r", encoding="utf-8") as f:
            profile_data = yaml.safe_load(f) or {}

        # 1. Handle inheritance
        resolved_flags = {}
        parent_name = profile_data.get("inherits")
        if parent_name:
            parent_resolved = self.resolve(parent_name)
            resolved_flags.update(parent_resolved.get("flags", {}))

        resolved_flags.update(profile_data.get("flags", {}))

        # Validate base profile flags against schema
        for flag_name, flag_val in resolved_flags.items():
            if self.valid_flags and flag_name not in self.valid_flags:
                raise ValueError(f"Unknown flag '{flag_name}' in profile '{profile_name}' not defined in schema.")

        # 2. Apply and validate environment overrides
        overrides = self.get_overrides()
        for k, v in overrides.items():
            resolved_flags[k] = v

        # 3. Validation and strict production checks
        conflicts = self.detect_conflicts(resolved_flags)
        if conflicts:
            raise ValueError(f"Profile '{profile_name}' resolution has conflicts: {conflicts}")

        # Enforce dependencies
        self.validate_dependencies(resolved_flags)

        # Enforce production strictness
        if profile_name == "agentic-production":
            required = ["AGENT_WORKER_ENABLED", "AGENT_EVALS_ENABLED", "CRYPTO_RECEIPTS_ENABLED", "AGENT_READINESS_CHECKS_ENABLED"]
            for req in required:
                if not resolved_flags.get(req):
                    raise ValueError(f"Production profile requires '{req}' to be true.")

        # Metadata & Audit
        metadata = {}
        for flag in resolved_flags:
            metadata[flag] = {
                "source": "env" if flag in overrides else "profile",
                "internal": flag.startswith("_") or "INTERNAL" in flag,
            }

        return {
            "profile": profile_name,
            "flags": resolved_flags,
            "metadata": metadata,
            "overrides": list(overrides.keys()),
            "conflicts": conflicts
        }

    def get_overrides(self) -> Dict[str, Any]:
        overrides = {}
        allow_high_risk = os.getenv("ALLOW_HIGH_RISK_PROFILE_OVERRIDE", "false").lower() == "true"

        for key, value in os.environ.items():
            # In a real/hardened impl, we only allow overrides defined in valid_flags in schema.yaml
            if self.valid_flags and key in self.valid_flags:
                flag_def = self.valid_flags[key]
                if not flag_def.get("override_allowed", False):
                    raise ValueError(f"Environment override for flag '{key}' is forbidden by schema.")

                # Check high-risk requirement
                if flag_def.get("high_risk", False) and not allow_high_risk:
                    raise ValueError(f"High risk override for flag '{key}' is blocked. Set ALLOW_HIGH_RISK_PROFILE_OVERRIDE=true to allow.")

                # Parse types
                expected_type = flag_def.get("type", "string")
                if expected_type == "boolean":
                    if value.lower() in ("true", "1"):
                        overrides[key] = True
                    elif value.lower() in ("false", "0"):
                        overrides[key] = False
                    else:
                        raise ValueError(f"Invalid boolean value '{value}' for override '{key}'.")
                elif expected_type == "integer":
                    try:
                        overrides[key] = int(value)
                    except ValueError:
                        raise ValueError(f"Invalid integer value '{value}' for override '{key}'.")
                else:
                    overrides[key] = value
            elif key.isupper() and key.startswith(("AGENT_", "PLUGIN_", "CRYPTO_", "ABUSE_", "DISTRIBUTED_", "MULTI_", "MANAGED_")):
                # Unknown override attempt
                raise ValueError(f"Unknown environment override '{key}' is blocked by schema validation.")

        if overrides:
            logger.info(f"Audited Profile Overrides applied: {overrides}")

        return overrides

    def detect_conflicts(self, flags: Dict[str, Any]) -> List[str]:
        conflicts = []
        if flags.get("AGENT_CODE_SANDBOX_MICROVM_REQUIRED") and flags.get("AGENT_CODE_SANDBOX_PROVIDER") == "docker":
            conflicts.append("MICROVM_REQUIRED but provider is set to docker")
        schema_conflicts = self.schema.get("conflicts", [])
        for c in schema_conflicts:
            f1, f2 = c.get("flag1"), c.get("flag2")
            v1, v2 = c.get("value1"), c.get("value2")
            if flags.get(f1) == v1 and flags.get(f2) == v2:
                conflicts.append(c.get("message", f"Conflict detected between {f1} and {f2}"))
        return conflicts

    def validate_dependencies(self, flags: Dict[str, Any]):
        schema_deps = self.schema.get("dependencies", [])
        for dep in schema_deps:
            flag = dep.get("flag")
            if flags.get(flag):
                requires = dep.get("requires", {})
                for req_flag, allowed_values in requires.items():
                    current_val = flags.get(req_flag)
                    if current_val not in allowed_values:
                        raise ValueError(f"Dependency violation: '{flag}' requires '{req_flag}' to be one of {allowed_values}. Got: '{current_val}'.")

    def validate_profile(self, profile_name: str):
        result = self.resolve(profile_name)
        if result["conflicts"]:
            raise ValueError(f"Profile '{profile_name}' has conflicts: {result['conflicts']}")
        return result
