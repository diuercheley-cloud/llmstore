#!/usr/bin/env python3
import os
import re
import yaml
import sys
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_DIR = PROJECT_ROOT / "control_plane/app/api"
FRONTEND_ADMIN_DIR = PROJECT_ROOT / "frontend/admin/src"
FRONTEND_CLIENT_DIR = PROJECT_ROOT / "frontend/client/src"
EXCEPTIONS_FILE = PROJECT_ROOT / "governance/frontend_surface_exceptions.yml"
REPORT_FILE = PROJECT_ROOT / "docs/generated/frontend_backend_surface.md"

def normalize_path(path):
    """Normalize path params: {id} or :id to <ID>"""
    p = re.sub(r'\{.*?\}', '<ID>', path)
    p = re.sub(r':\w+', '<ID>', p)
    # Remove trailing slashes and ensure it starts with /
    p = p.strip("/")
    return "/" + p

def get_backend_endpoints():
    endpoints = []
    for py_file in BACKEND_DIR.glob("*.py"):
        content = py_file.read_text()
        
        # Find router prefix
        prefix_match = re.search(r'APIRouter\s*\(\s*prefix=["\'](.*?)["\']', content)
        prefix = prefix_match.group(1) if prefix_match else ""
        
        # Find routes
        # Matches @router.get("/path"), @router.post(f"/path/{id}"), etc.
        route_matches = re.finditer(r'@router\.(get|post|put|patch|delete)\s*\(\s*[f]?["\'](.*?)["\']', content)
        for m in route_matches:
            full_path = prefix + m.group(2)
            endpoints.append({
                "path": full_path,
                "normalized": normalize_path(full_path),
                "method": m.group(1).upper(),
                "file": str(py_file.relative_to(PROJECT_ROOT))
            })
    return endpoints

def get_frontend_routes():
    routes = set()
    
    # Scan admin routes
    admin_routes_file = FRONTEND_ADMIN_DIR / "routes/adminRoutes.tsx"
    if admin_routes_file.exists():
        content = admin_routes_file.read_text()
        # Matches '/path': lazy(...)
        matches = re.finditer(r'["\'](/.*?)["\']\s*:\s*lazy', content)
        for m in matches:
            routes.add(normalize_path(m.group(1)))
            
    # Scan client App.tsx or similar
    client_app = FRONTEND_CLIENT_DIR / "App.tsx"
    if client_app.exists():
        content = client_app.read_text()
        # Look for tab keys or navigation paths
        # Matches path: '/path' or activeTab === 'path'
        matches = re.finditer(r'path\s*:\s*["\'](.*?)["\']', content)
        for m in matches:
            routes.add(normalize_path(m.group(1)))

    # Scan navConfig for admin
    nav_config = FRONTEND_ADMIN_DIR / "navigation/navConfig.ts"
    if nav_config.exists():
        content = nav_config.read_text()
        matches = re.finditer(r'path\s*:\s*["\'](.*?)["\']', content)
        for m in matches:
            routes.add(normalize_path(m.group(1)))
            
    return routes

def get_api_client_coverage():
    covered = set()
    covered_prefixes = set()
    
    # Scan TS api files
    for api_file in [FRONTEND_ADMIN_DIR / "lib/api.ts", FRONTEND_CLIENT_DIR / "lib/api.ts"]:
        if api_file.exists():
            content = api_file.read_text()
            
            # 1. Direct path matches (literals)
            # request('GET', '/path')
            matches = re.finditer(r'["\'](GET|POST|PUT|PATCH|DELETE)["\']\s*,\s*["\'](.*?)(?:\?.*?)?["\']', content)
            for m in matches:
                covered.add(normalize_path(m.group(2)))
            
            # 2. Template literals (paths with params)
            # request('GET', `/path/${id}`)
            template_matches = re.finditer(r'["\'](GET|POST|PUT|PATCH|DELETE)["\']\s*,\s*[`](.*?)[`]', content)
            for m in template_matches:
                # Replace ${variable} with <ID>
                path = re.sub(r'\$\{.*?\}', '<ID>', m.group(2))
                path = path.split('?')[0]
                covered.add(normalize_path(path))

            # 3. Simple client helpers
            # this.client.get('/path')
            helper_matches = re.finditer(r'this\.client\.(get|post|put|patch|delete)<.*?>\([`"\'](.*?)[`"\']', content)
            for m in helper_matches:
                path = re.sub(r'\$\{.*?\}', '<ID>', m.group(2))
                path = path.split('?')[0]
                covered.add(normalize_path(path))

            # 4. Partial matches for action sub-paths
            # If we cover /admin/agents, we often cover sub-actions dynamically
            # For strictness we only count explicit ones, but let's look for common prefixes
            for line in content.splitlines():
                p_match = re.search(r'["\'](/admin/.*?)["\']', line)
                if p_match:
                    p = p_match.group(1).split('?')[0]
                    covered_prefixes.add(normalize_path(p))
                
    return covered, covered_prefixes

def main():
    try:
        with open(EXCEPTIONS_FILE, 'r') as f:
            exceptions_data = yaml.safe_load(f) or {}
            exceptions_list = exceptions_data.get('exceptions', [])
    except FileNotFoundError:
        exceptions_list = []

    backend = get_backend_endpoints()
    frontend_routes = get_frontend_routes()
    api_coverage, api_prefixes = get_api_client_coverage()
    
    report = []
    report.append("# Frontend/Backend Surface Alignment Report")
    report.append(f"Generated on: {datetime.now().isoformat()}\n")
    report.append("| Method | Backend Path | Status | Frontend Coverage | File |")
    report.append("|--------|--------------|--------|-------------------|------|")
    
    failures = []
    
    # Dedup backend by path + method
    seen = set()
    
    for ep in sorted(backend, key=lambda x: x['path']):
        key = (ep['method'], ep['normalized'])
        if key in seen: continue
        seen.add(key)
        
        status = "no_frontend"
        coverage = "None"
        
        # Check exact exceptions
        exception = next((ex for ex in exceptions_list if normalize_path(ex['path']) == ep['normalized']), None)
        
        # Check prefix exceptions (e.g. /admin-v2/{rest:path})
        if not exception:
            for ex in exceptions_list:
                if '{' in ex['path']:
                    prefix_part = ex['path'].split('{')[0]
                    if prefix_part and prefix_part != "/":
                        normalized_prefix = normalize_path(prefix_part)
                        if ep['normalized'].startswith(normalized_prefix):
                            exception = ex
                            break

        if exception:
            status = exception['status']
            coverage = f"Exempted: {exception.get('reason', 'No reason')}"
        else:
            is_in_routes = ep['normalized'] in frontend_routes
            is_in_api = ep['normalized'] in api_coverage or ep['normalized'] in api_prefixes
            
            # Inheritance Check: Check all parent paths for exemptions/coverage
            parts = ep['normalized'].split('/')
            for i in range(2, len(parts)):
                parent_path = "/".join(parts[:i])
                
                # Check parent in routes
                if parent_path in frontend_routes:
                    is_in_routes = True
                
                # Check parent in API
                if parent_path in api_coverage or parent_path in api_prefixes:
                    is_in_api = True
                
                # Check parent in exceptions
                parent_ex = next((ex for ex in exceptions_list if normalize_path(ex['path']) == parent_path), None)
                if parent_ex:
                    status = parent_ex['status']
                    coverage = f"Inherited from {parent_path}: {parent_ex.get('reason')}"
                    break

            if status == "no_frontend":
                if is_in_routes:
                    status = "has_frontend"
                    coverage = "Route + API" if is_in_api else "Route Only"
                elif is_in_api:
                    status = "api_client_only"
                    coverage = "API Client Only"
        
        report.append(f"| {ep['method']} | `{ep['path']}` | {status} | {coverage} | {ep['file']} |")
        
        # Enforce P0: core/supported endpoints must have frontend coverage
        if status == "no_frontend":
             failures.append(f"MISSING FRONTEND: {ep['method']} {ep['path']} ({ep['file']})")

    os.makedirs(REPORT_FILE.parent, exist_ok=True)
    REPORT_FILE.write_text("\n".join(report))
    
    print(f"Report generated: {REPORT_FILE}")
    
    if failures:
        print("\n[!] Validation Failed: Unsupported backend surface detected without frontend coverage.")
        for f in failures:
            print(f"  - {f}")
        print("\nAction required: Implement frontend surface or add to governance/frontend_surface_exceptions.yml")
        sys.exit(1)
    else:
        print("\n[+] Validation Success: All backend endpoints are mapped to a frontend surface or exempted.")
        sys.exit(0)

if __name__ == "__main__":
    from datetime import datetime
    main()
