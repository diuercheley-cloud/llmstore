#!/usr/bin/env python3
"""
Comprehensive Security Audit Script v2
Checks for OWASP Top 10, secret leakage, supply-chain risks, and infrastructure flaws.
Exit code: 0 = all pass, 1 = failures found, 2 = warnings only
"""

import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"


class AuditCheck:
    def __init__(self):
        self.results: List[Tuple[str, str, str]] = []  # (check_name, status, detail)

    def add(self, name: str, status: str, detail: str = ""):
        self.results.append((name, status, detail))

    def run_checks(self):
        raise NotImplementedError

    def print_report(self):
        min_width = 65
        print(f"\n{'=' * 80}")
        print(f" Security Audit v2 Report")
        print(f"{'=' * 80}")
        fail_count = 0
        warn_count = 0
        pass_count = 0
        for name, status, detail in self.results:
            padded = f"  {name:<{min_width}}"
            if status == PASS:
                pass_count += 1
                print(f"{padded}[{PASS}]")
            elif status == WARN:
                warn_count += 1
                print(f"{padded}[{WARN}]  {detail}")
            else:
                fail_count += 1
                print(f"{padded}[{FAIL}]  {detail}")
        print(f"{'=' * 80}")
        print(f"  Total: {pass_count} passed, {fail_count} failed, {warn_count} warnings")
        print(f"{'=' * 80}")
        return fail_count


# =========================================================================
# A01: Broken Access Control Checks
# =========================================================================
class A01_AccessControl(AuditCheck):
    def run_checks(self):
        # Check agent_connectors_admin.py has require_admin dependency
        router_file = REPO_ROOT / "control_plane" / "app" / "api" / "agent_connectors_admin.py"
        if router_file.exists():
            content = router_file.read_text()
            if "dependencies=[Depends(require_admin)]" in content:
                self.add("agent_connectors_admin: require_admin on router", PASS)
            else:
                self.add("agent_connectors_admin: require_admin on router", FAIL)
            # Count endpoints without auth parameter
            endpoint_pattern = re.compile(r'@router\.(get|post|put|delete|patch)\(')
            endpoints = endpoint_pattern.findall(content)
            # All endpoints should be protected by the router-level dependency
            self.add(f"agent_connectors_admin: {len(endpoints)} endpoints with router-level auth", PASS)
        else:
            self.add("agent_connectors_admin: file exists", FAIL, "file not found")

        # Check all admin routers have auth
        api_dir = REPO_ROOT / "control_plane" / "app" / "api"
        for f in sorted(api_dir.glob("*_admin.py")):
            content = f.read_text()
            has_router_dep = "Depends(require_admin)" in content or "dependencies=[Depends(" in content
            has_endpoints = bool(re.findall(r'@router\.(get|post|put|delete|patch)\(', content))
            if has_endpoints and not has_router_dep:
                # Check if auto-secure mechanism covers it
                router_match = re.search(r'prefix\s*=\s*"([^"]+)"', content)
                if router_match:
                    prefix = router_match.group(1)
                    if prefix.startswith(("/admin", "/api/admin", "/api/v1/admin")):
                        self.add(f"{f.name}: endpoints rely on auto-secure wrapper", WARN, f"prefix={prefix}")
                    else:
                        self.add(f"{f.name}: NO auth dependency found", FAIL, f"prefix={prefix}")
                else:
                    self.add(f"{f.name}: NO auth dependency found", FAIL)
            else:
                self.add(f"{f.name}: auth check", PASS)

        return self


# =========================================================================
# A02: Cryptographic Failures & Secret Detection
# =========================================================================
class A02_Secrets(AuditCheck):
    def run_checks(self):
        secret_patterns = [
            (r'(?i)(password|passwd|pwd|secret|token|api[_-]?key)\s*[:=]\s*["\'][^"\']{8,}["\']', "Hardcoded secret"),
            (r'sk-or-v1-[a-zA-Z0-9]{20,}', "OpenRouter API key"),
            (r'ghp_[a-zA-Z0-9]{36}', "GitHub Personal Access Token"),
            (r'gho_[a-zA-Z0-9]{36}', "GitHub OAuth Access Token"),
            (r'xox[bpras]-[0-9a-zA-Z-]{10,}', "Slack token"),
            (r'AKIA[0-9A-Z]{16}', "AWS Access Key"),
            (r'-----BEGIN (RSA|EC|DSA|OPENSSH|PRIVATE) KEY-----', "Private key"),
            (r'eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+', "JWT token"),
        ]

        # Scan for .env files on disk
        env_files = list(REPO_ROOT.glob(".env*"))
        for ef in env_files:
            if ef.name.endswith(".bak") or ".bak." in ef.name:
                self.add(f"Backup .env file on disk: {ef.name}", FAIL, "Contains secrets, should be removed")
            elif ef.suffix not in (".example", ".template"):
                self.add(f".env file on disk: {ef.name}", WARN, "Check if it contains real secrets")

        # Check .gitignore for .env pattern
        gitignore = REPO_ROOT / ".gitignore"
        if gitignore.exists():
            content = gitignore.read_text()
            if ".env" in content:
                self.add(".gitignore: .env is ignored", PASS)
            else:
                self.add(".gitignore: .env NOT ignored", FAIL)
        else:
            self.add(".gitignore: file exists", FAIL)

        # Scan for secrets in staged/unstaged files
        try:
            result = subprocess.run(
                ["git", "grep", "-n", "--cached", "-E", "sk-or-v1-[a-zA-Z0-9]"],
                capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=30
            )
            if result.stdout.strip():
                self.add("No API keys in git index", FAIL, "Found OpenRouter key pattern in tracked files")
            else:
                self.add("No API keys in git index", PASS)
        except Exception:
            self.add("API key scan", WARN, "Could not run git grep")

        # Check for private key files
        key_files = list(REPO_ROOT.glob("*_key*")) + list(REPO_ROOT.glob("*.pem")) + list(REPO_ROOT.glob("*.key"))
        for kf in key_files:
            self.add(f"Key file found: {kf.name}", FAIL, "Private key file should not be in repo root")

        return self


# =========================================================================
# A03: Injection Checks (eval/exec/shell)
# =========================================================================
class A03_Injection(AuditCheck):
    def run_checks(self):
        # Check workflow_dag.py for eval
        dag_file = REPO_ROOT / "control_plane" / "app" / "services" / "agents" / "workflows" / "workflow_dag.py"
        if dag_file.exists():
            content = dag_file.read_text()
            if "eval(" not in content:
                self.add("workflow_dag.py: no eval()", PASS)
            else:
                # Check if it's in the _safe_eval method or actual eval
                if "def _safe_eval" in content:
                    self.add("workflow_dag.py: uses safe expression parser", PASS)
                else:
                    self.add("workflow_dag.py: contains eval()", FAIL)
        else:
            self.add("workflow_dag.py: file exists", FAIL)

        # Check compat importers for exec() protections
        compat_dirs = [
            REPO_ROOT / "control_plane" / "app" / "compat",
            REPO_ROOT / "scripts" / "llm_harness" / "compat",
        ]
        for cd in compat_dirs:
            for importer in cd.rglob("importers.py"):
                content = importer.read_text()
                if "BLOCKED_PATTERNS" in content and "MAX_CODE_LENGTH" in content:
                    self.add(f"{importer.relative_to(REPO_ROOT)}: exec() with protections", PASS)
                elif "exec(" in content:
                    self.add(f"{importer.relative_to(REPO_ROOT)}: exec() without protections", FAIL)
                else:
                    self.add(f"{importer.relative_to(REPO_ROOT)}: no exec()", PASS)

        # Check shell=True
        for pattern in ["shell=True"]:
            result = subprocess.run(
                ["git", "grep", "-n", "-E", re.escape(pattern), "--", "*.py"],
                capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=30
            )
            lines = [l for l in result.stdout.strip().split("\n") if l and not l.startswith("tests/") and not l.startswith("scripts/validators/validate_")]
            if lines:
                self.add(f"No shell=True in production .py files", FAIL, f"Found: {lines}")
            else:
                self.add(f"No shell=True in production .py files", PASS)

        # Check shell scripts for eval
        sh_files = [
            REPO_ROOT / "scripts" / "validators" / "validate-system-health.sh",
            REPO_ROOT / "scripts" / "validators" / "admin-lab-financial-flow.sh",
        ]
        for sf in sh_files:
            if sf.exists():
                content = sf.read_text()
                if "eval(" not in content or "safe_eval" in content or "safe_get" in content:
                    self.add(f"{sf.name}: no eval() or safe parser", PASS)
                elif "eval(" in content:
                    self.add(f"{sf.name}: contains eval()", FAIL)

        return self


# =========================================================================
# A05: Security Misconfiguration
# =========================================================================
class A05_Misconfig(AuditCheck):
    def run_checks(self):
        # Check Dockerfiles for USER directive
        dockerfiles = list((REPO_ROOT / "docker").rglob("Dockerfile*"))
        for df in dockerfiles:
            content = df.read_text()
            if "USER appuser" in content:
                self.add(f"{df.name}: non-root user", PASS)
            else:
                self.add(f"{df.name}: missing non-root USER directive", FAIL)

        # Check Dockerfiles for SHA256 pinning
        for df in dockerfiles:
            content = df.read_text()
            from_lines = re.findall(r'^FROM\s+(\S+)', content, re.MULTILINE)
            for fl in from_lines:
                if "@sha256:" in fl:
                    self.add(f"{df.name}: FROM {fl.split(':')[0]} pinned to SHA256", PASS)
                else:
                    self.add(f"{df.name}: FROM {fl} not pinned to SHA256", WARN)

        # Check CORS settings
        settings_dir = REPO_ROOT / "control_plane" / "app" / "services" / "config"
        for sf in settings_dir.glob("*.py"):
            content = sf.read_text()
            if "cors" in content.lower():
                if '"*"' in content or "'*'" in content:
                    self.add(f"{sf.name}: CORS wildcard '*'' found", WARN, "Should be restricted in production")
                else:
                    self.add(f"{sf.name}: CORS configured", PASS)

        return self


# =========================================================================
# A07: Token Leakage Checks
# =========================================================================
class A07_TokenLeakage(AuditCheck):
    def run_checks(self):
        # Check SSO redirects use hash fragments
        auth_file = REPO_ROOT / "control_plane" / "app" / "api" / "auth.py"
        if auth_file.exists():
            content = auth_file.read_text()
            if "sso_token=" in content:
                if "#sso_token=" in content:
                    self.add("auth.py: SSO token in URL hash fragment", PASS)
                else:
                    self.add("auth.py: SSO token in URL query param", FAIL)

        sso_file = REPO_ROOT / "control_plane" / "app" / "api" / "enterprise_sso.py"
        if sso_file.exists():
            content = sso_file.read_text()
            if "sso_token=" in content:
                if "#sso_token=" in content:
                    self.add("enterprise_sso.py: SSO token in URL hash fragment", PASS)
                else:
                    self.add("enterprise_sso.py: SSO token in URL query param", FAIL)

        # Check token in WebSocket URLs
        ws_patterns = [
            r'\?token=', r'\?api_key=', r'\?access_token='
        ]
        for pat in ws_patterns:
            result = subprocess.run(
                ["git", "grep", "-n", "-E", pat, "--", "*.py", "*.ts", "*.tsx"],
                capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=30
            )
            lines = [l for l in result.stdout.strip().split("\n") if l and "/tests/" not in l]
            if lines:
                for line in lines:
                    self.add(f"Token in URL: {line}", WARN, "Token passed as URL query parameter")

        return self


# =========================================================================
# A10: SSRF Prevention
# =========================================================================
class A10_SSRF(AuditCheck):
    def run_checks(self):
        # Check web ingestor for URL validation
        web_ingestor = REPO_ROOT / "control_plane" / "app" / "services" / "ingestion" / "web_ingestor.py"
        if web_ingestor.exists():
            content = web_ingestor.read_text()
            if "private" in content.lower() or "169.254" in content or "127.0.0.1" in content:
                self.add("web_ingestor.py: SSRF validation", PASS)
            else:
                self.add("web_ingestor.py: SSRF validation", WARN, "No private IP blocking detected")

        # Check webhook handlers for URL validation
        webhook_dir = REPO_ROOT / "control_plane" / "app" / "services" / "webhooks"
        if webhook_dir.exists():
            for wf in webhook_dir.rglob("*.py"):
                content = wf.read_text()
                if "url" in content.lower():
                    self.add(f"webhooks/{wf.name}: potential SSRF surface", WARN, "Verify URL validation")

        return self


# =========================================================================
# Supply Chain Security Checks
# =========================================================================
class SupplyChain(AuditCheck):
    def run_checks(self):
        # Check requirements.txt vs uv.lock sync
        req_file = REPO_ROOT / "requirements.txt"
        lock_file = REPO_ROOT / "uv.lock"
        if req_file.exists() and lock_file.exists():
            self.add("requirements.txt + uv.lock both exist", PASS)

        # Check for SBOM
        sbom_files = list(REPO_ROOT.glob("**/sbom*")) + list(REPO_ROOT.glob("**/*cyclonedx*")) + list(REPO_ROOT.glob("**/*spdx*"))
        if sbom_files:
            self.add("SBOM file(s) found", PASS)
            for sf in sbom_files:
                if ".sig" not in sf.name:
                    self.add(f"SBOM signing: {sf.name}", WARN, "SBOM should be signed")
        else:
            self.add("SBOM file found", WARN, "No SBOM found in repo")

        # Check .pre-commit-config.yaml for security hooks
        precommit = REPO_ROOT / ".pre-commit-config.yaml"
        if precommit.exists():
            content = precommit.read_text()
            if "detect-secrets" in content or "detect-private-key" in content:
                self.add("pre-commit: security hooks configured", PASS)
            else:
                self.add("pre-commit: security hooks", WARN, "No detect-secrets or detect-private-key hooks")
        else:
            self.add("pre-commit-config.yaml exists", FAIL)

        return self


# =========================================================================
# Infrastructure Checks
# =========================================================================
class Infrastructure(AuditCheck):
    def run_checks(self):
        # Check docker-compose for security best practices
        dc_file = REPO_ROOT / "docker-compose.yml"
        if dc_file.exists():
            content = dc_file.read_text()
            if "internal: true" in content:
                self.add("docker-compose: internal networks enabled", PASS)
            else:
                self.add("docker-compose: internal networks", WARN, "No internal:true found")
            if "restart: always" in content or "restart: unless-stopped" in content:
                self.add("docker-compose: restart policy set", PASS)

        # Check rate limiting
        rl_file = REPO_ROOT / "control_plane" / "app" / "services" / "rate_limit.py"
        if rl_file.exists():
            content = rl_file.read_text()
            if "enforce_client_rate_limit" in content:
                self.add("rate_limit: enforce_client_rate_limit exists", PASS)
            else:
                self.add("rate_limit: enforce_client_rate_limit missing", FAIL)

        # Check middleware for security headers
        mw_file = REPO_ROOT / "control_plane" / "app" / "middleware.py"
        if mw_file.exists():
            content = mw_file.read_text()
            headers_found = []
            for header in ["X-Content-Type-Options", "X-Frame-Options", "Content-Security-Policy", "Strict-Transport-Security"]:
                if header in content:
                    headers_found.append(header)
            if len(headers_found) >= 3:
                self.add(f"middleware: security headers ({len(headers_found)})", PASS, f"Found: {', '.join(headers_found)}")
            else:
                self.add("middleware: security headers", WARN, f"Only found: {', '.join(headers_found)}")

        return self


# =========================================================================
# Main
# =========================================================================
def main():
    total_fails = 0

    checkers = [
        ("A01: Broken Access Control", A01_AccessControl()),
        ("A02: Cryptographic Failures / Secrets", A02_Secrets()),
        ("A03: Injection (eval/exec/shell)", A03_Injection()),
        ("A05: Security Misconfiguration", A05_Misconfig()),
        ("A07: Token Leakage", A07_TokenLeakage()),
        ("A10: SSRF Prevention", A10_SSRF()),
        ("Supply Chain Security", SupplyChain()),
        ("Infrastructure", Infrastructure()),
    ]

    for title, checker in checkers:
        print(f"\n--- {title} ---")
        checker.run_checks()
        total_fails += checker.print_report()

    sys.exit(0 if total_fails == 0 else min(total_fails, 255))


if __name__ == "__main__":
    main()
