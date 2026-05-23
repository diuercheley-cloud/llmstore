# Owner: platform-ops
import os
import re
import yaml
import logging
from typing import Dict, Any, List, Set, Tuple

logger = logging.getLogger(__name__)

class SurfaceAuditService:
    def __init__(self, base_dir: str = None):
        if base_dir is None:
            # Resolved relative to this file: control_plane/app/services/platform/surface_audit.py
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
        self.base_dir = base_dir

    def run_audit(self) -> Dict[str, Any]:
        """Runs the entire platform surface area audit and returns structured findings."""
        results = {
            "apis": self.audit_apis(),
            "ui_pages": self.audit_ui_pages(),
            "services": self.audit_services(),
            "scripts": self.audit_scripts(),
            "feature_flags": self.audit_feature_flags(),
            "adapters": self.audit_adapters(),
            "dashboards": self.audit_dashboards(),
            "tests": self.audit_tests()
        }
        return results

    def audit_apis(self) -> Dict[str, Any]:
        """Audits APIs by comparing api-surface.yaml with FastAPI routes."""
        yaml_path = os.path.join(self.base_dir, "config/api-surface.yaml")
        yaml_endpoints = []
        yaml_deprecated = []
        
        if os.path.exists(yaml_path):
            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or []
                    for entry in data:
                        endpoint = entry.get("endpoint")
                        method = entry.get("method", "GET").upper()
                        status = entry.get("status", "supported")
                        yaml_endpoints.append((endpoint, method, status))
                        if status == "deprecated":
                            yaml_deprecated.append({
                                "endpoint": endpoint,
                                "method": method,
                                "replacement": entry.get("replacement"),
                                "sunset_date": entry.get("sunset_date", "2026-12-31")
                            })
            except Exception as e:
                logger.error(f"Error loading api-surface.yaml: {e}")

        # Get FastAPI routes
        fastapi_routes = []
        try:
            from app.main import app
            from fastapi.routing import APIRoute
            for route in app.routes:
                if isinstance(route, APIRoute):
                    for method in route.methods:
                        fastapi_routes.append((route.path, method.upper()))
        except Exception as e:
            logger.error(f"Error loading FastAPI routes: {e}")

        # Detect duplicates
        route_counts = {}
        for path, method in fastapi_routes:
            route_counts[(path, method)] = route_counts.get((path, method), 0) + 1
        
        duplicates = [f"{method} {path}" for (path, method), count in route_counts.items() if count > 1]

        # Convert to sets for comparison
        fastapi_set = set(fastapi_routes)
        yaml_map = {(endpoint, method): status for endpoint, method, status in yaml_endpoints}
        yaml_set = set((endpoint, method) for endpoint, method, _ in yaml_endpoints)

        # Unreferenced registry: present in YAML but not in FastAPI
        unreferenced = []
        for endpoint, method in yaml_set - fastapi_set:
            unreferenced.append(f"{method} {endpoint}")

        # Unregistered: present in FastAPI but not in YAML
        unregistered = []
        ignored_endpoints = {
            "/openapi.json", "/docs", "/redoc", "/api-docs", "/api-redoc", 
            "/developer-docs", "/metrics", "/health", "/favicon.ico"
        }
        for endpoint, method in fastapi_set - yaml_set:
            if endpoint not in ignored_endpoints and not endpoint.startswith("/docs"):
                unregistered.append(f"{method} {endpoint}")

        return {
            "duplicates": sorted(duplicates),
            "unreferenced_registry": sorted(unreferenced),
            "unregistered_routes": sorted(unregistered),
            "deprecated_apis": yaml_deprecated
        }

    def audit_ui_pages(self) -> Dict[str, Any]:
        """Audits frontend UI pages by checking if they are routed in App.tsx."""
        pages_dir = os.path.join(self.base_dir, "frontend/admin/src/pages")
        app_tsx_path = os.path.join(self.base_dir, "frontend/admin/src/App.tsx")
        
        all_pages = []
        orphaned_pages = []
        
        if os.path.exists(pages_dir) and os.path.exists(app_tsx_path):
            try:
                with open(app_tsx_path, "r", encoding="utf-8") as f:
                    app_content = f.read()

                for root, _, files in os.walk(pages_dir):
                    for file in files:
                        if file.endswith((".tsx", ".ts", ".jsx", ".js")):
                            full_path = os.path.join(root, file)
                            rel_path = os.path.relpath(full_path, pages_dir)
                            base_name = os.path.splitext(file)[0]
                            all_pages.append(rel_path)
                            
                            # Check if referenced in App.tsx
                            # Check for import base_name or './pages/...' or similar
                            is_referenced = (
                                base_name in app_content or
                                rel_path in app_content or
                                os.path.splitext(rel_path)[0] in app_content
                            )
                            if not is_referenced:
                                orphaned_pages.append(rel_path)
            except Exception as e:
                logger.error(f"Error auditing UI pages: {e}")

        return {
            "all_pages": sorted(all_pages),
            "orphaned_pages": sorted(orphaned_pages)
        }

    def audit_services(self) -> Dict[str, Any]:
        """Audits python services under control_plane/app/services."""
        services_dir = os.path.join(self.base_dir, "control_plane/app/services")
        app_dir = os.path.join(self.base_dir, "control_plane/app")
        
        all_services = []
        orphaned_services = []

        if os.path.exists(services_dir):
            try:
                # Find all .py files in services
                service_files = []
                for root, _, files in os.walk(services_dir):
                    for file in files:
                        if file.endswith(".py") and file != "__init__.py":
                            full_path = os.path.join(root, file)
                            rel_path = os.path.relpath(full_path, services_dir)
                            service_files.append((full_path, rel_path))

                # For each service, check if it's imported in any python files in control_plane/app/
                # excluding the service file itself.
                for full_path, rel_path in service_files:
                    # Construct module import patterns
                    # e.g., app.services.platform.surface_audit
                    # rel_path: platform/surface_audit.py -> platform.surface_audit
                    module_parts = os.path.splitext(rel_path)[0].replace(os.path.sep, ".")
                    import_pattern1 = f"services.{module_parts}"
                    import_pattern2 = os.path.splitext(os.path.basename(full_path))[0]
                    
                    all_services.append(rel_path)
                    
                    is_imported = False
                    # Scan control_plane/app/ py files
                    for root_app, _, files_app in os.walk(app_dir):
                        if is_imported:
                            break
                        for file_app in files_app:
                            if file_app.endswith(".py"):
                                full_app_path = os.path.join(root_app, file_app)
                                if full_app_path == full_path:
                                    continue # skip self
                                
                                try:
                                    with open(full_app_path, "r", encoding="utf-8") as f_app:
                                        content = f_app.read()
                                        if import_pattern1 in content or f"import {import_pattern2}" in content or f"from app.services.{module_parts}" in content:
                                            is_imported = True
                                            break
                                except Exception:
                                    pass
                    
                    if not is_imported:
                        orphaned_services.append(rel_path)
            except Exception as e:
                logger.error(f"Error auditing services: {e}")

        return {
            "all_services": sorted(all_services),
            "orphaned_services": sorted(orphaned_services)
        }

    def audit_scripts(self) -> Dict[str, Any]:
        """Audits scripts under scripts/ to see if they are used in Makefile, workflows, or code."""
        scripts_dir = os.path.join(self.base_dir, "scripts")
        makefile_path = os.path.join(self.base_dir, "Makefile")
        workflows_dir = os.path.join(self.base_dir, ".github/workflows")
        app_dir = os.path.join(self.base_dir, "control_plane/app")
        
        all_scripts = []
        orphaned_scripts = []

        if os.path.exists(scripts_dir):
            try:
                scripts = [f for f in os.listdir(scripts_dir) if os.path.isfile(os.path.join(scripts_dir, f))]
                
                # Load Makefile content
                makefile_content = ""
                if os.path.exists(makefile_path):
                    with open(makefile_path, "r", encoding="utf-8") as f:
                        makefile_content = f.read()

                # Load workflow contents
                workflow_contents = ""
                if os.path.exists(workflows_dir):
                    for root, _, files in os.walk(workflows_dir):
                        for file in files:
                            try:
                                with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                                    workflow_contents += f.read() + "\n"
                            except Exception:
                                pass

                # Check references
                for script in scripts:
                    all_scripts.append(script)
                    # Search inside Makefile, workflows, and python app files
                    is_used = script in makefile_content or script in workflow_contents
                    
                    if not is_used:
                        # Scan python app files
                        for root, _, files in os.walk(app_dir):
                            if is_used:
                                break
                            for file in files:
                                if file.endswith(".py"):
                                    try:
                                        with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                                            if script in f.read():
                                                is_used = True
                                                break
                                    except Exception:
                                        pass
                                        
                    if not is_used:
                        orphaned_scripts.append(script)
            except Exception as e:
                logger.error(f"Error auditing scripts: {e}")

        return {
            "all_scripts": sorted(all_scripts),
            "orphaned_scripts": sorted(orphaned_scripts)
        }

    def audit_feature_flags(self) -> Dict[str, Any]:
        """Audits feature flags from config/feature-flags.yaml."""
        yaml_path = os.path.join(self.base_dir, "config/feature-flags.yaml")
        app_dir = os.path.join(self.base_dir, "control_plane/app")
        
        all_flags = []
        orphaned_flags = []

        if os.path.exists(yaml_path):
            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    flags_data = yaml.safe_load(f) or []
                    all_flags = [entry["name"] for entry in flags_data if isinstance(entry, dict) and "name" in entry]

                # Check if flag name is used in python code
                for flag in all_flags:
                    is_used = False
                    for root, _, files in os.walk(app_dir):
                        if is_used:
                            break
                        for file in files:
                            if file.endswith(".py"):
                                try:
                                    with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                                        if flag in f.read():
                                            is_used = True
                                            break
                                except Exception:
                                    pass
                    if not is_used:
                        orphaned_flags.append(flag)
            except Exception as e:
                logger.error(f"Error auditing feature flags: {e}")

        return {
            "all_flags": sorted(all_flags),
            "orphaned_flags": sorted(orphaned_flags)
        }

    def audit_adapters(self) -> Dict[str, Any]:
        """Audits tool adapters to make sure they are registered in __init__.py."""
        adapters_dir = os.path.join(self.base_dir, "control_plane/app/services/agents/tool_adapters")
        init_path = os.path.join(adapters_dir, "__init__.py")
        
        all_adapters = []
        unregistered_adapters = []

        if os.path.exists(adapters_dir) and os.path.exists(init_path):
            try:
                with open(init_path, "r", encoding="utf-8") as f:
                    init_content = f.read()

                # Find classes in adapter files
                for file in os.listdir(adapters_dir):
                    if file.endswith(".py") and file != "__init__.py":
                        file_path = os.path.join(adapters_dir, file)
                        all_adapters.append(file)
                        
                        # Find adapter class names
                        classes = []
                        try:
                            with open(file_path, "r", encoding="utf-8") as f_class:
                                class_content = f_class.read()
                                for match in re.finditer(r"class\s+(\w+)\(ToolAdapterContract\):", class_content):
                                    classes.append(match.group(1))
                        except Exception:
                            pass
                        
                        # Verify if classes are registered
                        for cls in classes:
                            if cls not in init_content or f"register({cls}(" not in init_content.replace(" ", ""):
                                unregistered_adapters.append(f"{file} ({cls})")
            except Exception as e:
                logger.error(f"Error auditing tool adapters: {e}")

        return {
            "all_adapters": sorted(all_adapters),
            "unregistered_adapters": sorted(unregistered_adapters)
        }

    def audit_dashboards(self) -> Dict[str, Any]:
        """Audits Grafana dashboards in monitoring/dashboards/ to see if provisioned in provisioning/dashboards/."""
        dashboards_dir = os.path.join(self.base_dir, "monitoring/dashboards")
        provision_dir = os.path.join(self.base_dir, "monitoring/grafana/provisioning/dashboards")
        
        all_dashboards = []
        unprovisioned_dashboards = []

        if os.path.exists(dashboards_dir):
            try:
                # Find all JSON dashboard files
                dashboards = [f for f in os.listdir(dashboards_dir) if f.endswith(".json")]
                for db in dashboards:
                    all_dashboards.append(db)
                    # Check if provisioned
                    prov_path = os.path.join(provision_dir, db)
                    if not os.path.exists(prov_path):
                        unprovisioned_dashboards.append(db)
            except Exception as e:
                logger.error(f"Error auditing Grafana dashboards: {e}")

        return {
            "all_dashboards": sorted(all_dashboards),
            "unprovisioned_dashboards": sorted(unprovisioned_dashboards)
        }

    def audit_tests(self) -> Dict[str, Any]:
        """Audits python tests for coverage utility (assert statements)."""
        tests_dir = os.path.join(self.base_dir, "tests")
        
        all_test_files = []
        useless_test_files = []

        if os.path.exists(tests_dir):
            try:
                for root, _, files in os.walk(tests_dir):
                    for file in files:
                        if file.startswith("test_") and file.endswith(".py"):
                            full_path = os.path.join(root, file)
                            rel_path = os.path.relpath(full_path, tests_dir)
                            all_test_files.append(rel_path)
                            
                            # Check size or presence of "assert"
                            try:
                                size = os.path.getsize(full_path)
                                if size == 0:
                                    useless_test_files.append(rel_path)
                                    continue
                                    
                                with open(full_path, "r", encoding="utf-8") as f:
                                    content = f.read()
                                    if "assert" not in content:
                                        useless_test_files.append(rel_path)
                            except Exception:
                                pass
            except Exception as e:
                logger.error(f"Error auditing test files: {e}")

        return {
            "all_test_files": len(all_test_files),
            "useless_test_files": sorted(useless_test_files)
        }
