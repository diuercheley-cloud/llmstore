"""Resolve supported platform profiles into effective flags."""

# Owner: platform-ops
"""Resolve supported platform profiles into effective flags."""

# Owner: platform-ops
import os
import yaml
from pathlib import Path
from typing import Dict, Any, List

class ProfileResolver:
    def __init__(self, profiles_dir: str = "config/platform-profiles"):
        self.profiles_dir = Path(profiles_dir)
        self.default_profile = "appliance"

    def resolve(self, profile_name: str = None) -> Dict[str, Any]:
        if not profile_name:
            profile_name = os.getenv("PLATFORM_PROFILE", self.default_profile)

        profile_path = self.profiles_dir / f"{profile_name}.yaml"
        if not profile_path.exists():
             raise ValueError(f"Profile '{profile_name}' not found at {profile_path}")

        with open(profile_path, "r") as f:
            profile_data = yaml.safe_load(f)

        resolved_flags = profile_data.get("flags", {}).copy()
        
        # Apply environment overrides
        overrides = self.get_overrides()
        resolved_flags.update(overrides)
        
        # Mark internal/derived flags (metadata)
        metadata = {}
        for flag in resolved_flags:
            metadata[flag] = {
                "source": "env" if flag in overrides else "profile",
                "internal": flag.startswith("_") or "INTERNAL" in flag,
                "deprecated": flag in ["OLD_S3_PATH", "LEGACY_AUTH"] # Example
            }
            if metadata[flag]["deprecated"]:
                print(f"WARNING: Feature flag '{flag}' is deprecated and will be removed soon.")

        return {
            "profile": profile_name,
            "flags": resolved_flags,
            "metadata": metadata,
            "overrides": list(overrides.keys()),
            "conflicts": self.detect_conflicts(resolved_flags)
        }

    def get_overrides(self) -> Dict[str, Any]:
        overrides = {}
        for key, value in os.environ.items():
            # In a real impl, we would check if it's a known flag
            if key.isupper() and (value.lower() in ["true", "false"] or key.endswith("_ENABLED")):
                if value.lower() == "true":
                    overrides[key] = True
                elif value.lower() == "false":
                    overrides[key] = False
                else:
                    overrides[key] = value
        return overrides

    def detect_conflicts(self, flags: Dict[str, Any]) -> List[str]:
        conflicts = []
        if flags.get("AGENT_SANDBOX_ALLOW_SIMULATED_PROVIDER") and flags.get("AGENT_CODE_SANDBOX_PROVIDER") in ["gvisor", "firecracker"]:
             # This is not necessarily a hard conflict but maybe a warning
             pass
        
        if flags.get("AGENT_CODE_SANDBOX_MICROVM_REQUIRED") and flags.get("AGENT_CODE_SANDBOX_PROVIDER") == "docker":
            conflicts.append("MICROVM_REQUIRED but provider is set to docker")
            
        return conflicts

    def validate_profile(self, profile_name: str):
        result = self.resolve(profile_name)
        if result["conflicts"]:
            raise ValueError(f"Profile '{profile_name}' has conflicts: {result['conflicts']}")
        return result
