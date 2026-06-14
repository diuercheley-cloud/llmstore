import os
import sys
import json
import yaml
from pathlib import Path
from collections import defaultdict
from typing import Any

# Add control_plane to sys.path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "control_plane"))

# Mocking some imports that might fail due to missing env or dependencies
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["JWT_SECRET"] = "static-secret-for-doc-generation-only"
os.environ["ADMIN_TOKEN"] = "static-token-for-doc-generation-only"
os.environ["DATA_PLANE_BASE_URL"] = "http://localhost:8001"

from app.services.config_service import BaseAppConfig
from app.services.feature_flag_registry import FeatureFlagRegistryService

GEN_HEADER = "<!-- AUTO-GENERATED: do not edit manually -->\n\n"

def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)

def md(value: Any) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).replace("|", "\\|").replace("\n", " ").strip()

def classify_secret(name: str) -> bool:
    upper = name.upper()
    markers = ("TOKEN", "SECRET", "PASSWORD", "KEY", "DSN")
    return any(marker in upper for marker in markers)

def generate_config_reference():
    grouped = defaultdict(list)
    
    for field_name, field_info in sorted(BaseAppConfig.model_fields.items()):
        # Try to get env name from alias or validation_alias
        env_name = field_name.upper()
        validation_alias = getattr(field_info, "validation_alias", None)
        if validation_alias:
             import re
             match = re.search(r"'([A-Z0-9_]+)'", str(validation_alias))
             if match:
                 env_name = match.group(1)
        
        is_secret = classify_secret(env_name) or classify_secret(field_name)
        group = env_name.split("_", 1)[0].lower()
        
        default = field_info.default
        if default is Ellipsis: # Pydantic way of saying Required
             default_str = "*Required*"
        elif is_secret and default not in (None, ""):
             default_str = "<redacted>"
        else:
             default_str = f"`{md(default)}`"
             
        p_type = str(field_info.annotation).replace("<class '", "").replace("'>", "").replace("typing.", "")
        
        grouped[group].append([env_name, p_type, default_str, "Yes" if is_secret else "No"])

    lines = [GEN_HEADER, "# Configuration Reference\n", "This document lists all environment variables used to configure the platform.\n"]
    
    for group in sorted(grouped.keys()):
        lines.append(f"## `{group}`\n")
        lines.append("| Env Var | Type | Default | Secret |")
        lines.append("| --- | --- | --- | --- |")
        for row in grouped[group]:
            lines.append(f"| `{row[0]}` | {row[1]} | {row[2]} | {row[3]} |")
        lines.append("")
        
    output_path = root_dir / "docs/generated/CONFIGURATION_REFERENCE.md"
    ensure_dir(output_path.parent)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Generated {output_path}")

def generate_feature_flags():
    registry = FeatureFlagRegistryService()
    flags = registry.get_all_flags()
    
    lines = [GEN_HEADER, "# Feature Flags Inventory\n", "Inventory of all feature flags and their current lifecycle status.\n"]
    lines.append("| Flag | Area | Status | Risk | Owner | Description |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    
    for f in sorted(flags, key=lambda x: x.get("name", "")):
        name = f.get("name", "UNNAMED")
        area = f.get("area", "general")
        status = f.get("status", "active")
        risk = f.get("risk_level", "low")
        owner = f.get("owner", "unknown")
        desc = f.get("description", "")
        lines.append(f"| `{name}` | {area} | {status} | {risk} | {owner} | {desc} |")
        
    output_path = root_dir / "docs/generated/FLAGS_INVENTORY.md"
    ensure_dir(output_path.parent)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Generated {output_path}")

def generate_profiles():
    profiles_dir = root_dir / "config/profiles"
    lines = [GEN_HEADER, "# Platform Profiles\n", "Available operational profiles and their characteristic feature sets.\n"]
    
    for p_file in sorted(profiles_dir.glob("*.yaml")):
        with open(p_file, "r") as f:
            data = yaml.safe_load(f)
        
        name = p_file.stem
        desc = data.get("description", "No description")
        lines.append(f"## Profile: `{name}`\n")
        lines.append(f"{desc}\n")
        
        features = data.get("features", {})
        if features:
            lines.append("### Feature Set\n")
            lines.append("| Feature | Enabled |")
            lines.append("| --- | --- |")
            for feat, enabled in sorted(features.items()):
                lines.append(f"| `{feat}` | {'✅' if enabled else '❌'} |")
            lines.append("")

    output_path = root_dir / "docs/generated/PROFILES_REFERENCE.md"
    ensure_dir(output_path.parent)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Generated {output_path}")

def generate_api_surface():
    manifest_path = root_dir / "generated/route_surface_manifest.json"
    if not manifest_path.exists():
        print("Warning: route_surface_manifest.json not found. Skipping API documentation.")
        return

    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        
    lines = [GEN_HEADER, "# API Surface Reference\n", "Automatically discovered API endpoints and their classification.\n"]
    lines.append("| Method | Path | Status | Domain | Owner |")
    lines.append("| --- | --- | --- | --- | --- |")
    
    for r in sorted(manifest, key=lambda x: (x.get("path", ""), x.get("method", ""))):
        method = r.get("method")
        path = r.get("path")
        status = r.get("status")
        domain = r.get("domain")
        owner = r.get("owner")
        lines.append(f"| **{method}** | `{path}` | {status} | {domain} | {owner} |")
        
    output_path = root_dir / "docs/generated/API_SURFACE.md"
    ensure_dir(output_path.parent)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Generated {output_path}")

def generate_storage_backends():
    try:
        from app.storage.backends import describe_storage_backend
        families = [
            "postgresql+asyncpg://user:pass@localhost/db",
            "sqlite+aiosqlite:////tmp/test.db",
            "duckdb:///tmp/test.duckdb",
            "clickhouse://localhost:8123/default",
            "opensearch://localhost:9200"
        ]
        
        lines = [GEN_HEADER, "# Storage Backends\n", "Supported storage families and their capabilities.\n"]
        lines.append("| Family | Driver | Async | Persistent | Search |")
        lines.append("| --- | --- | --- | --- | --- |")
        
        for url in families:
            desc = describe_storage_backend(url)
            family = desc.get("family")
            driver = desc.get("driver")
            is_async = "✅" if desc.get("is_async") else "❌"
            persistent = "✅" if desc.get("persistent") else "❌"
            search = "✅" if desc.get("vector_search") else "❌"
            lines.append(f"| {family} | {driver} | {is_async} | {persistent} | {search} |")
            
        output_path = root_dir / "docs/generated/STORAGE_BACKENDS.md"
        ensure_dir(output_path.parent)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"Generated {output_path}")
    except Exception as e:
        print(f"Failed to generate storage backends doc: {e}")

def generate_backup_capabilities():
    try:
        from app.schemas.backup import BackupManifest
        manifest_default = BackupManifest(archive_checksum="dummy", payload_file="dummy", payload_signature="dummy")
        
        lines = [GEN_HEADER, "# Backup & Restore Capabilities\n", "Overview of platform backup coverage and technical constraints.\n"]
        
        lines.append("## Coverage Matrix\n")
        lines.append("| Scope | Included Components | Excluded Components | Encryption |")
        lines.append("| --- | --- | --- | --- |")
        lines.append(f"| {manifest_default.scope} | {', '.join(manifest_default.included)} | {', '.join(manifest_default.excluded)} | {manifest_default.encryption_algorithm} ({manifest_default.encryption_status}) |")
        
        lines.append("\n## Technical Constraints\n")
        lines.append(f"- **Schema Version:** {manifest_default.schema_version}")
        lines.append(f"- **PITR Supported:** {'✅' if manifest_default.pitr_supported else '❌'}")
        lines.append(f"- **Signature Algorithm:** {manifest_default.signature_algorithm}")
        
        output_path = root_dir / "docs/generated/BACKUP_CAPABILITIES.md"
        ensure_dir(output_path.parent)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"Generated {output_path}")
    except Exception as e:
        print(f"Failed to generate backup capabilities doc: {e}")

def generate_product_surface():
    try:
        payload_path = root_dir / "config/supported-surface.yaml"
        if not payload_path.exists():
            return
            
        with open(payload_path, "r") as f:
            payload = yaml.safe_load(f)
            
        capabilities = payload.get("capabilities", [])
        
        lines = [GEN_HEADER, "# Product Surface\n", "Documentation source of truth for capability status claims.\n"]
        lines.append("| Capability | ID | Status | Support | Owner |")
        lines.append("| --- | --- | --- | --- | --- |")
        
        for cap in sorted(capabilities, key=lambda x: x.get("name", "")):
            lines.append(f"| {cap.get('name')} | `{cap.get('id')}` | {cap.get('status')} | {cap.get('support_level', '-')} | {cap.get('owner', '-')} |")
            
        output_path = root_dir / "docs/generated/PRODUCT_SURFACE.md"
        ensure_dir(output_path.parent)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"Generated {output_path}")
    except Exception as e:
        print(f"Failed to generate product surface doc: {e}")

def main():
    generate_config_reference()
    generate_feature_flags()
    generate_profiles()
    generate_api_surface()
    generate_storage_backends()
    generate_backup_capabilities()
    generate_product_surface()

if __name__ == "__main__":
    main()
