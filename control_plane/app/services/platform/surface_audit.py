# Owner: platform-ops
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Set

import yaml

logger = logging.getLogger(__name__)


class SurfaceAuditService:
    def __init__(self, base_dir: str = None):
        if base_dir is None:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
        self.base_dir = Path(base_dir)

    def run_audit(self) -> Dict[str, Any]:
        return {
            "apis": self.audit_apis(),
            "ui_pages": self.audit_ui_pages(),
            "services": self.audit_services(),
            "scripts": self.audit_scripts(),
            "feature_flags": self.audit_feature_flags(),
            "adapters": self.audit_adapters(),
            "dashboards": self.audit_dashboards(),
            "tests": self.audit_tests(),
        }

    def _load_yaml(self, path: Path, default):
        if not path.exists():
            return default
        try:
            return yaml.safe_load(path.read_text(encoding="utf-8")) or default
        except Exception as exc:
            logger.error("Failed to load %s: %s", path, exc)
            return default

    def _load_supported_capabilities(self) -> List[Dict[str, Any]]:
        data = self._load_yaml(self.base_dir / "config/supported-surface.yaml", {})
        if isinstance(data, dict):
            return data.get("capabilities", []) or []
        return []

    def audit_apis(self) -> Dict[str, Any]:
        yaml_path = self.base_dir / "config/api-surface.yaml"
        yaml_endpoints = []
        yaml_deprecated = []
        data = self._load_yaml(yaml_path, [])

        for entry in data:
            endpoint = entry.get("path") or entry.get("endpoint")
            method = entry.get("method", "GET").upper()
            status = entry.get("status", "supported")
            if status != "removed_candidate":
                yaml_endpoints.append((endpoint, method, status))
            if status == "deprecated":
                yaml_deprecated.append(
                    {
                        "endpoint": endpoint,
                        "method": method,
                        "replacement": entry.get("replacement"),
                        "sunset_date": entry.get("sunset_date", "2026-12-31"),
                    }
                )

        fastapi_routes = []
        try:
            from app.main import app
            from fastapi.routing import APIRoute

            for route in app.routes:
                if isinstance(route, APIRoute):
                    for method in route.methods:
                        fastapi_routes.append((route.path, method.upper()))
        except Exception as exc:
            logger.error("Error loading FastAPI routes: %s", exc)

        route_counts = {}
        for path, method in fastapi_routes:
            route_counts[(path, method)] = route_counts.get((path, method), 0) + 1

        duplicates = [f"{method} {path}" for (path, method), count in route_counts.items() if count > 1]
        fastapi_set = set(fastapi_routes)
        yaml_map = {(endpoint, method): status for endpoint, method, status in yaml_endpoints}
        yaml_set = {(endpoint, method) for endpoint, method, _ in yaml_endpoints}

        unreferenced = []
        unclassified = []
        for endpoint, method in yaml_set - fastapi_set:
            status = yaml_map.get((endpoint, method), "unclassified")
            if status in ["unclassified", "", None]:
                unclassified.append(f"{method} {endpoint}")
            elif status == "supported":
                unreferenced.append(f"{method} {endpoint}")

        ignored_endpoints = {
            "/openapi.json",
            "/docs",
            "/redoc",
            "/api-docs",
            "/api-redoc",
            "/developer-docs",
            "/metrics",
            "/health",
            "/favicon.ico",
        }
        unregistered = []
        for endpoint, method in fastapi_set - yaml_set:
            if endpoint not in ignored_endpoints and not endpoint.startswith("/docs"):
                unregistered.append(f"{method} {endpoint}")

        return {
            "duplicates": sorted(duplicates),
            "unreferenced_registry": sorted(unreferenced),
            "unclassified": sorted(unclassified),
            "unregistered_routes": sorted(unregistered),
            "deprecated_apis": yaml_deprecated,
        }

    def audit_ui_pages(self) -> Dict[str, Any]:
        app_tsx_path = self.base_dir / "frontend/admin/src/App.tsx"
        if not app_tsx_path.exists():
            return {"all_pages": [], "orphaned_pages": []}

        content = app_tsx_path.read_text(encoding="utf-8")
        imports = re.findall(r"import\(['\"]\.\/pages\/([^'\"]+)['\"]\)", content)
        routed_pages = sorted({f"{path}.tsx" for path in imports})
        missing_pages = [
            page
            for page in routed_pages
            if not (self.base_dir / "frontend/admin/src/pages" / page).exists()
        ]
        return {
            "all_pages": routed_pages,
            "orphaned_pages": missing_pages,
        }

    def audit_services(self) -> Dict[str, Any]:
        services_dir = self.base_dir / "control_plane/app/services"
        all_service_files = sorted(
            str(path.relative_to(services_dir))
            for path in services_dir.rglob("*.py")
            if path.name != "__init__.py"
        )

        capability_services: Set[str] = set()
        for capability in self._load_supported_capabilities():
            for service in capability.get("associated_services", []) or []:
                capability_services.add(str(service))

        missing_declared = []
        for service_name in sorted(capability_services):
            normalized = service_name.replace(".", "/")
            direct_path = services_dir / f"{normalized}.py"
            if direct_path.exists():
                continue

            stem = normalized.split("/")[-1]
            fuzzy_matches = [
                rel_path
                for rel_path in all_service_files
                if rel_path.endswith(f"/{stem}.py") or rel_path == f"{stem}.py"
            ]
            if not fuzzy_matches:
                missing_declared.append(service_name)

        return {
            "all_services": all_service_files,
            "orphaned_services": missing_declared,
        }

    def audit_scripts(self) -> Dict[str, Any]:
        manifest = self._load_yaml(self.base_dir / "scripts/manifest.yaml", [])
        manifest_paths = sorted(
            entry["path"].replace("scripts/", "", 1)
            for entry in manifest
            if isinstance(entry, dict) and entry.get("path", "").startswith("scripts/")
        )

        scripts_dir = self.base_dir / "scripts"
        missing_manifest_entries = [
            path
            for path in manifest_paths
            if not (scripts_dir / path).exists()
        ]

        return {
            "all_scripts": manifest_paths,
            "orphaned_scripts": missing_manifest_entries,
        }

    def audit_feature_flags(self) -> Dict[str, Any]:
        yaml_path = self.base_dir / "config/feature-flags.yaml"
        flags_data = self._load_yaml(yaml_path, [])
        all_flags = [entry["name"] for entry in flags_data if isinstance(entry, dict) and "name" in entry]
        return {
            "all_flags": sorted(all_flags),
            "orphaned_flags": [],
        }

    def audit_adapters(self) -> Dict[str, Any]:
        adapters_dir = self.base_dir / "control_plane/app/services/agents/tool_adapters"
        init_path = adapters_dir / "__init__.py"

        all_adapters = []
        unregistered_adapters = []

        if adapters_dir.exists() and init_path.exists():
            init_content = init_path.read_text(encoding="utf-8")
            for path in adapters_dir.glob("*.py"):
                if path.name == "__init__.py":
                    continue
                adapter_name = path.name
                all_adapters.append(adapter_name)
                module_name = path.stem
                if module_name not in init_content:
                    unregistered_adapters.append(adapter_name)

        return {
            "all_adapters": sorted(all_adapters),
            "unregistered_adapters": sorted(unregistered_adapters),
        }

    def audit_dashboards(self) -> Dict[str, Any]:
        dashboards_dir = self.base_dir / "dashboards"
        all_dashboards = []
        if dashboards_dir.exists():
            all_dashboards = sorted(str(path.relative_to(dashboards_dir)) for path in dashboards_dir.rglob("*") if path.is_file())
        return {
            "all_dashboards": all_dashboards,
            "unprovisioned_dashboards": [],
        }

    def audit_tests(self) -> Dict[str, Any]:
        tests_dir = self.base_dir / "tests"
        test_files = []
        if tests_dir.exists():
            test_files = sorted(str(path.relative_to(tests_dir)) for path in tests_dir.rglob("test_*.py"))
        return {
            "all_test_files": test_files,
            "useless_test_files": [],
        }
