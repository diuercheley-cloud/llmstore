#!/usr/bin/env python3
import os
import sys
import json
import re
import subprocess
from typing import Iterable, Set


def git_status_paths(prefix: str) -> Set[str]:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--", prefix],
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception:
        return set()

    changed = set()
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if path.startswith(prefix):
            changed.add(path)
    return changed


def find_test_for_service(service_rel_path: str) -> str | None:
    service_name = os.path.basename(service_rel_path).replace(".py", "")
    module_hint = service_rel_path.replace("/", ".").replace(".py", "")
    test_roots = ("tests", "control_plane/tests")

    for test_root in test_roots:
        if not os.path.isdir(test_root):
            continue
        for root, _, files in os.walk(test_root):
            for file in files:
                if not file.endswith(".py"):
                    continue
                test_path = os.path.join(root, file)
                file_lower = file.lower()
                if f"test_{service_name.lower()}" in file_lower:
                    return test_path
                try:
                    with open(test_path, "r", encoding="utf-8") as handle:
                        content = handle.read()
                except OSError:
                    continue
                if module_hint in content or service_name in content:
                    return test_path
    return None

def load_rules():
    config_path = "config/platform-freeze-rules.json"
    if not os.path.exists(config_path):
        print(f"Error: Configuration file {config_path} not found.")
        sys.exit(1)
    with open(config_path, "r") as f:
        return json.load(f)

def check_top_level_dirs(rules):
    if not rules.get("forbid_new_top_level_dirs"):
        return True

    allowed = set(rules.get("allowed_top_level_dirs", []))
    allowed.update(rules.get("approved_exceptions", []))

    changed_dirs = {
        path.split("/", 1)[0]
        for path in git_status_paths(".")
        if "/" in path and os.path.isdir(path.split("/", 1)[0])
    }
    current_dirs = sorted(changed_dirs)
    violations = []

    # Ignore common development and cache directories that might exist locally but are not part of repository state
    ignored_local_dirs = {".vscode", ".idea", "__pycache__", "node_modules", ".venv", "venv", ".pytest_cache", ".ruff_cache"}

    for d in current_dirs:
        if d in ignored_local_dirs:
            continue
        if d not in allowed:
            violations.append(d)

    if violations:
        print(f"FAIL: New top-level directories detected: {violations}")
        return False
    return True

def check_bounded_contexts(rules):
    if not rules.get("forbid_new_bounded_contexts"):
        return True

    allowed = set(rules.get("allowed_bounded_contexts", []))
    allowed.update(rules.get("approved_exceptions", []))

    services_dir = "control_plane/app/services"
    if not os.path.exists(services_dir):
        return True

    current_dirs = [d for d in os.listdir(services_dir) if os.path.isdir(os.path.join(services_dir, d)) and d != "__pycache__"]
    violations = []

    for d in current_dirs:
        if d not in allowed:
            violations.append(d)

    if violations:
        print(f"FAIL: New bounded contexts detected under {services_dir}: {violations}")
        return False
    return True

def check_api_routers(rules):
    api_dir = "control_plane/app/api"
    if not os.path.exists(api_dir):
        return True

    violations = []
    allowed_routers = set(rules.get("allowed_api_routers", []))
    exceptions = set(rules.get("approved_exceptions", []))

    changed_router_paths = {
        os.path.basename(path)
        for path in git_status_paths(api_dir)
        if path.endswith(".py")
    }
    current_routers = [
        f for f in os.listdir(api_dir)
        if f.endswith(".py")
        and f not in ["__init__.py", "dependencies.py", "deps.py"]
        and f in changed_router_paths
    ]
    
    for r in current_routers:
        is_new = r not in allowed_routers
        is_approved = r in exceptions
        
        path = os.path.join(api_dir, r)
        with open(path, "r") as f:
            content = f.read()

        if is_new and not is_approved:
            violations.append(f"New api router file '{r}' is blocked under freeze rules. Add to approved_exceptions if approved.")

        # Determine if it's an admin router (by filename or content prefix)
        is_admin = r.startswith("admin_") or r.endswith("_admin.py") or "admin" in r or re.search(r"prefix\s*=\s*\"/admin", content)

        if is_new and is_admin:
            if not re.search(r"(#\s*Owner:)|(__owner__\s*=)", content, re.IGNORECASE):
                violations.append(f"New admin router {r} is missing an owner definition (# Owner: <role>)")

    if violations:
        for v in violations:
            print(f"FAIL: {v}")
        return False
    return True

def check_new_services(rules):
    services_dir = "control_plane/app/services"
    if not os.path.exists(services_dir):
        return True

    allowed_services = set(rules.get("allowed_services", []))
    exceptions = set(rules.get("approved_exceptions", []))

    violations = []
    changed_service_paths = git_status_paths(services_dir)
    for root, _, files in os.walk(services_dir):
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                rel_path = os.path.relpath(os.path.join(root, file), services_dir)
                repo_rel_path = os.path.join(services_dir, rel_path)
                if repo_rel_path not in changed_service_paths:
                    continue
                is_new = rel_path not in allowed_services
                is_approved = rel_path in exceptions

                if is_new:
                    if not is_approved:
                        violations.append(f"New service file '{rel_path}' is blocked under freeze rules. Add to approved_exceptions.")
                    
                    # Check for test coverage
                    service_name = file.replace(".py", "")
                    if not find_test_for_service(rel_path):
                        violations.append(f"New service file '{rel_path}' has no corresponding test in tests/. All new services must have tests.")

                    path = os.path.join(root, file)
                    with open(path, "r") as f:
                        content = f.read()
                    
                    # Check for docstring or owner comment
                    has_doc = '"""' in content or "'''" in content
                    has_owner = re.search(r"(#\s*Owner:)|(__owner__\s*=)", content, re.IGNORECASE)
                    if not (has_doc or has_owner):
                        violations.append(f"New service file '{rel_path}' is missing documentation/owner info.")

    if violations:
        for v in violations:
            print(f"FAIL: {v}")
        return False
    return True

def check_feature_flags(rules):
    config_file = "control_plane/app/core/config.py"
    if not os.path.exists(config_file):
        return True

    allowed_flags = set(rules.get("allowed_feature_flags", []))
    exceptions = set(rules.get("approved_exceptions", []))

    if config_file not in git_status_paths(config_file):
        return True

    with open(config_file, "r") as f:
        lines = f.readlines()

    violations = []
    for idx, line in enumerate(lines):
        if ("_enabled" in line or "feature_flag" in line) and ":" in line and "=" in line:
            match = re.match(r"\s*(\w+)\s*:", line)
            if match:
                flag_name = match.group(1)
                is_new = flag_name not in allowed_flags
                is_approved = flag_name in exceptions

                if is_new:
                    if not is_approved:
                        violations.append(f"New feature flag '{flag_name}' is blocked. Add to approved_exceptions.")
                    
                    has_owner = False
                    has_status = False
                    # Check preceding 5 lines for comments
                    start_check = max(0, idx - 5)
                    for check_idx in range(start_check, idx + 1):
                        if re.search(r"Owner:", lines[check_idx], re.IGNORECASE):
                            has_owner = True
                        if re.search(r"Status:", lines[check_idx], re.IGNORECASE):
                            has_status = True
                    if not (has_owner and has_status):
                        violations.append(f"New feature flag '{flag_name}' at line {idx+1} must have 'Owner:' and 'Status:' comments.")

    if violations:
        for v in violations:
            print(f"FAIL: {v}")
        return False
    return True

def check_models_and_migrations(rules):
    models_dir = "control_plane/app/models"
    if not os.path.exists(models_dir):
        return True

    allowed_models = set(rules.get("allowed_models", []))
    exceptions = set(rules.get("approved_exceptions", []))

    violations = []
    
    # Get migration contents
    migrations_dir = "control_plane/alembic/versions"
    migration_contents = ""
    if os.path.exists(migrations_dir):
        for f in os.listdir(migrations_dir):
            if f.endswith(".py"):
                with open(os.path.join(migrations_dir, f), "r") as m_file:
                    migration_contents += m_file.read() + "\n"

    changed_model_paths = git_status_paths(models_dir)
    for root, _, files in os.walk(models_dir):
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                path = os.path.join(root, file)
                if path not in changed_model_paths:
                    continue
                with open(path, "r") as f:
                    content = f.read()

                classes = re.findall(r"class\s+(\w+)\s*\(\s*(?:[^)]*,\s*)*Base(?:\s*,\s*[^)]*)*\s*\)\s*:", content)
                for cls in classes:
                    is_new = cls not in allowed_models
                    is_approved = cls in exceptions

                    if is_new:
                        if not is_approved:
                            violations.append(f"New model class {cls} in {file} is blocked under freeze rules. Add to approved_exceptions.")
                        
                        # Require Owner
                        if not re.search(rf"#\s*Owner:|__owner__\s*=", content, re.IGNORECASE):
                            violations.append(f"New model class {cls} in {file} is missing an owner tag")
                        # Require Alembic Migration
                        if cls not in migration_contents and cls.lower() not in migration_contents.lower():
                            violations.append(f"New model class {cls} has no associated Alembic migration version file")

    if violations:
        for v in violations:
            print(f"FAIL: {v}")
        return False
    return True

def check_new_endpoints(rules):
    if not rules.get("require_supported_surface_classification"):
        return True

    violations = []
    
    # Check if the tag v1.9.7-compliance-readiness exists in git history
    try:
        subprocess.run(["git", "rev-parse", "--verify", "v1.9.7-compliance-readiness"], capture_output=True, check=True)
        base_ref = "v1.9.7-compliance-readiness"
    except Exception:
        # Fallback: if tag is missing, try fetching it or warn
        print("Warning: git tag v1.9.7-compliance-readiness not found. Skipping endpoint classification check.")
        return True

    try:
        # Get diff of control_plane/app/api/ relative to the tag
        cmd = ["git", "diff", base_ref, "--", "control_plane/app/api/"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        diff_output = res.stdout
    except Exception as e:
        print(f"Warning: git diff failed: {e}. Skipping endpoint classification check.")
        return True

    current_file = None
    file_classifications = {}

    for line in diff_output.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            # Match FastAPI route decorator like @router.get(, @router.post(, etc.
            if re.search(r"^\+\s*@\w+\.(get|post|put|delete|patch|options|head|trace|api_route)\s*\(", line):
                if not current_file or not os.path.exists(current_file):
                    continue

                if current_file not in file_classifications:
                    with open(current_file, "r") as f:
                        content = f.read()
                    
                    # A file has surface classification if it defines APIRouter prefix matching admin/client/portal/public
                    # or contains # Surface: <value> or # Classification: <value>
                    has_surface = re.search(
                        r"(?:#\s*(?:Surface|Classification):\s*(admin|client|portal|public))|"
                        r"(?:APIRouter\([^)]*prefix\s*=\s*\"/(admin|client|portal|public))|"
                        r"(?:surface\s*=\s*\"(admin|client|portal|public)\")",
                        content,
                        re.IGNORECASE
                    )
                    file_classifications[current_file] = bool(has_surface)

                if not file_classifications[current_file]:
                    violations.append(f"New endpoint in {current_file} (line: '{line.strip()}') has no surface classification. Routers must specify classification prefix or tag (admin, client, portal, public).")

    if violations:
        for v in violations:
            print(f"FAIL: {v}")
        return False
    return True

def check_capability_classification(rules):
    yaml_path = "config/supported-surface.yaml"
    if not os.path.exists(yaml_path):
        print(f"FAIL: Configuration file {yaml_path} not found.")
        return False

    try:
        import yaml
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"FAIL: Failed to parse {yaml_path}: {e}")
        return False

    capabilities = data.get("capabilities", [])
    
    # Extract all classified identifiers
    classified_flags = set()
    for c in capabilities:
        ff = c.get("feature_flag")
        if ff:
            classified_flags.add(ff.lower())
        for add_ff in c.get("additional_flags", []) or []:
            if add_ff:
                classified_flags.add(add_ff.lower())
                
    classified_prefixes = {c.get("api_prefix") for c in capabilities if c.get("api_prefix")}
    
    violations = []

    # 1. Check feature flags
    config_file = "control_plane/app/core/config.py"
    if os.path.exists(config_file):
        allowed_flags = set(rules.get("allowed_feature_flags", []))
        with open(config_file, "r", encoding="utf-8") as f:
            content = f.read()
        # Find all fields that end with _enabled or look like feature flags
        for line in content.splitlines():
            if ":" in line and "=" in line and ("_enabled" in line or "feature_flag" in line):
                match = re.match(r"\s*(\w+)\s*:", line)
                if match:
                    flag_name = match.group(1)
                    if flag_name not in allowed_flags:
                        # This is a new feature flag. Is it classified?
                        if flag_name.lower() not in classified_flags:
                            violations.append(f"New feature flag '{flag_name}' must be classified under a capability in {yaml_path} (using the 'feature_flag' or 'additional_flags' fields).")

    # 2. Check API routers
    api_dir = "control_plane/app/api"
    if os.path.exists(api_dir):
        allowed_routers = set(rules.get("allowed_api_routers", []))
        changed_router_paths = {
            os.path.basename(path)
            for path in git_status_paths(api_dir)
            if path.endswith(".py")
        }
        for r in os.listdir(api_dir):
            if r.endswith(".py") and r not in ["__init__.py", "dependencies.py", "deps.py"]:
                if r not in changed_router_paths:
                    continue
                if r not in allowed_routers:
                    # New router. Check if its filename, prefix, or id matches any capability
                    path = os.path.join(api_dir, r)
                    with open(path, "r", encoding="utf-8") as f:
                        router_content = f.read()
                    
                    prefix_match = re.search(r"prefix\s*=\s*\"([^\"]+)\"", router_content)
                    prefix = prefix_match.group(1) if prefix_match else None
                    
                    classified = False
                    # Check prefix match
                    if prefix:
                        for p in classified_prefixes:
                            if p and prefix.startswith(p):
                                classified = True
                                break
                    
                    # Check ID or name match
                    router_base = r.replace(".py", "").replace("_admin", "").replace("_portal", "").replace("_", "-")
                    router_name_no_ext = r.replace(".py", "")
                    for c in capabilities:
                        cap_id = c.get("id", "")
                        assoc_services = c.get("associated_services", []) or []
                        if (cap_id == router_base or router_base in cap_id or cap_id in router_base or
                                router_name_no_ext in assoc_services or router_base in assoc_services):
                            classified = True
                            break
                    
                    if not classified:
                        violations.append(f"New API router '{r}' (prefix: '{prefix}') must be classified under a capability in {yaml_path} (by matching prefix, capability ID, or feature name).")

    # 3. Check Services
    services_dir = "control_plane/app/services"
    if os.path.exists(services_dir):
        allowed_services = set(rules.get("allowed_services", []))
        changed_service_paths = git_status_paths(services_dir)
        for root, _, files in os.walk(services_dir):
            for file in files:
                if file.endswith(".py") and file != "__init__.py":
                    rel_path = os.path.relpath(os.path.join(root, file), services_dir)
                    repo_rel_path = os.path.join(services_dir, rel_path)
                    if repo_rel_path not in changed_service_paths:
                        continue
                    if rel_path not in allowed_services:
                        # New service. Check if it's classified
                        service_base = file.replace(".py", "").replace("_", "-")
                        service_name_no_ext = file.replace(".py", "")
                        classified = False
                        for c in capabilities:
                            cap_id = c.get("id", "")
                            assoc_services = c.get("associated_services", []) or []
                            if (cap_id == service_base or service_base in cap_id or cap_id in service_base or
                                    service_name_no_ext in assoc_services or service_base in assoc_services or
                                    file in assoc_services or rel_path in assoc_services):
                                classified = True
                                break
                        if not classified:
                            violations.append(f"New service file '{rel_path}' must be classified under a capability in {yaml_path} (matching service name to capability ID).")

    if violations:
        for v in violations:
            print(f"FAIL: {v}")
        return False
    return True

def main():
    print("--- Starting Architectural Freeze Compliance Audit ---")
    rules = load_rules()
    
    success = True
    if not check_top_level_dirs(rules):
        success = False

    if not check_bounded_contexts(rules):
        success = False

    if not check_api_routers(rules):
        success = False

    if not check_new_services(rules):
        success = False

    if not check_feature_flags(rules):
        success = False

    if not check_models_and_migrations(rules):
        success = False

    if not check_new_endpoints(rules):
        success = False

    if not check_capability_classification(rules):
        success = False

    if success:
        print("PASS: Platform architectural freeze compliance verified successfully.")
        sys.exit(0)
    else:
        print("FAIL: Architectural freeze violations detected.")
        sys.exit(1)

if __name__ == "__main__":
    main()
