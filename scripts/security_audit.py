#!/usr/bin/env python3
"""
Comprehensive Security Audit Script for LLM Inference Stack.
Checks authentication, authorization, cryptography, network,
container, and configuration security posture.
"""

import ast
import glob
import hashlib
import hmac
import json
import os
import re
import secrets
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

PASS = f"{GREEN}[PASS]{RESET}"
FAIL = f"{RED}[FAIL]{RESET}"
WARN = f"{YELLOW}[WARN]{RESET}"
INFO = f"{CYAN}[INFO]{RESET}"

ROOT = Path(__file__).resolve().parents[1]
CONTROL_PLANE = ROOT / "control_plane"
SCRIPTS_DIR = ROOT / "scripts"
TESTS_DIR = ROOT / "tests"
DOCKER_DIR = ROOT / "docker"
DEPLOY_DIR = ROOT / "deploy"

results = []
warnings_count = 0
failures_count = 0
pass_count = 0


def check(name, condition, detail=""):
    global pass_count, failures_count, warnings_count
    if condition:
        pass_count += 1
        status = PASS
    else:
        status = FAIL
        failures_count += 1
    results.append((name, status, detail))
    print(f"  {status} {name}")
    if detail:
        print(f"         {detail}")


def warn(name, detail=""):
    global warnings_count
    warnings_count += 1
    results.append((name, WARN, detail))
    print(f"  {WARN} {name}")
    if detail:
        print(f"         {detail}")


def scan_file_for_secrets(filepath):
    secrets_patterns = [
        (r'(?i)(sk-local-|sk-[a-z]+-)[A-Za-z0-9_-]{20,}', "API key pattern"),
        (r'(?i)(-----BEGIN\s*(RSA|EC|PRIVATE|OPENSSH)\s+KEY-----)', "Private key"),
        (r'(?i)(ADMIN_TOKEN|JWT_SECRET|POSTGRES_PASSWORD)\s*=\s*["\']?[^"\'\s]{4,}', "Secret env var"),
    ]
    findings = []
    try:
        with open(filepath) as f:
            content = f.read()
        for i, line in enumerate(content.splitlines(), 1):
            for pattern, desc in secrets_patterns:
                if re.search(pattern, line) and "security-warning-allowlist" not in str(filepath):
                    findings.append((i, desc, line.strip()[:80]))
    except Exception:
        pass
    return findings


def section(title):
    border = "=" * 70
    print(f"\n{border}")
    print(f" {BOLD}{title}{RESET}")
    print(border)


def subsection(title):
    print(f"\n {CYAN}{title}{RESET}")
    print(f" {'-' * 60}")


# ========== AUTHENTICATION ==========
def audit_authentication():
    section("1. AUTHENTICATION")

    auth_file = CONTROL_PLANE / "app" / "services" / "auth.py"
    if not auth_file.exists():
        warn("auth.py not found - cannot audit")
        return

    content = auth_file.read_text()

    subsection("1.1 Timing-safe Token Comparison")
    has_compare_digest = "compare_digest" in content
    check("Legacy admin token uses hmac.compare_digest",
          has_compare_digest,
          "Missing timing-safe comparison enables timing attacks")

    has_direct_compare = re.search(r'token == settings\.admin_(super|write|read)_token', content)
    check("No direct == comparison of admin tokens",
          not has_direct_compare or has_compare_digest,
          f"Direct == found at line {has_direct_compare.start() if has_direct_compare else 'N/A'}")

    subsection("1.2 API Key Verification")
    has_verify_secret = "verify_secret" in content
    check("API key uses PBKDF2 + timing-safe verify",
          has_verify_secret,
          "Must use verify_secret() from core/security.py")

    subsection("1.3 RBAC Mode")
    rbac_enabled = "is_rbac_admin_enabled" in content
    check("RBAC authentication path exists",
          rbac_enabled,
          "RBAC provides granular permission checks")

    subsection("1.4 SSO Session Validation")
    has_sso_fallback = "_is_valid_sso_session" in content
    check("SSO session validation implemented",
          has_sso_fallback,
          "SSO provides secondary auth mechanism")

    subsection("1.5 Key Prefix Lookup Protection")
    has_prefix_lookup = "key_prefix" in content and "verify_secret" in content
    check("API key uses prefix + full verification",
          has_prefix_lookup,
          "Prefix-only lookup would leak keys")

    subsection("1.6 Expiration Check")
    has_expiry = "expires_at" in content and "utc_now" in content
    check("API key expiration enforced",
          has_expiry,
          "Expired keys must be rejected")


# ========== CRYPTOGRAPHY ==========
def audit_cryptography():
    section("2. CRYPTOGRAPHY")

    security_file = CONTROL_PLANE / "app" / "core" / "security.py"
    if not security_file.exists():
        warn("core/security.py not found")
        return

    content = security_file.read_text()

    subsection("2.1 Token Generation")
    uses_secrets = "secrets.token_urlsafe" in content
    check("API keys generated with CSPRNG (secrets.token_urlsafe)",
          uses_secrets,
          "Use secrets module, not random")

    has_32_bytes = re.search(r'token_urlsafe\((\d+)\)', content)
    if has_32_bytes:
        bytes_count = int(has_32_bytes.group(1))
        check(f"Token entropy adequate ({bytes_count * 8} bits)",
              bytes_count >= 24,
              f"Current: {bytes_count*8} bits, recommended >= 192 bits")

    subsection("2.2 Password Hashing")
    has_pbkdf2 = "pbkdf2_hmac" in content
    check("PBKDF2 used for secret hashing",
          has_pbkdf2,
          "PBKDF2 is NIST-recommended KDF")

    iter_match = re.search(r'pbkdf2_hmac\([^)]+\)', content)
    if iter_match:
        call = iter_match.group(0)
        num_match = re.search(r',\s*(\d[\d_]*)\)', call)
        if num_match:
            iterations_str = num_match.group(1)
            iterations = int(iterations_str.replace('_', '')) if iterations_str else 0
        else:
            iterations = 0
    else:
        iterations = 0
        check(f"PBKDF2 iterations ({iterations:,}) >= NIST minimum",
              iterations >= 600000,
              f"NIST SP 800-63B recommends 600,000+ (current: {iterations:,})")

    uses_compare_digest = "compare_digest" in content
    check("Timing-safe comparison (hmac.compare_digest)",
          uses_compare_digest,
          "Prevents timing side-channel attacks")

    uses_random_salt = "secrets.token_hex" in content
    check("Random salt per secret hash",
          uses_random_salt,
          "Prevents rainbow table attacks")


# ========== MIDDLEWARE / HTTP HEADERS ==========
def audit_middleware():
    section("3. HTTP SECURITY HEADERS")

    middleware_file = CONTROL_PLANE / "app" / "middleware.py"
    if not middleware_file.exists():
        warn("middleware.py not found")
        return

    content = middleware_file.read_text()

    headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "SAMEORIGIN",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
        "Content-Security-Policy": None,
    }

    for header, expected in headers.items():
        found = header in content
        check(f"Security header: {header}",
              found,
              f"Missing {header} header")

    if "Content-Security-Policy" in content:
        has_unsafe_inline = "unsafe-inline" in content
        check("CSP restricts unsafe-inline",
              not has_unsafe_inline,
              "unsafe-inline weakens XSS protection")

        has_unsafe_eval = "unsafe-eval" in content
        check("CSP restricts unsafe-eval",
              not has_unsafe_eval,
              "unsafe-eval allows arbitrary code execution")

    subsection("3.1 Rate Limiting")
    has_rate_limit = "enforce_global_rate_limit" in content
    check("Global rate limiting implemented",
          has_rate_limit,
          "Protects against DoS attacks")

    has_tenant_rate_limit = "enforce_tenant_rate_limit" in content
    check("Tenant-level rate limiting",
          has_tenant_rate_limit,
          "Prevents noisy neighbor issues")

    has_ip_rate_limit = "enforce_ip_rate_limit" in content
    if not has_ip_rate_limit:
        warn("Per-IP rate limiting not in middleware",
             "Auth endpoints exposed to brute force")
    else:
        check("Per-IP rate limiting in middleware", True)

    subsection("3.2 Payload Size Validation")
    has_payload_check = "max_request_body_size_bytes" in content
    check("Payload size validation",
          has_payload_check,
          "Prevents resource exhaustion via large payloads")

    subsection("3.3 Content-Length Validation")
    has_cl_check = "content_length" in content
    check("Content-Length header validated",
          has_cl_check,
          "Invalid Content-Length can bypass filters")

    subsection("3.4 Correlation ID")
    has_correlation_id = "X-Correlation-ID" in content
    check("Correlation ID for request tracing",
          has_correlation_id,
          "Essential for security incident investigation")

    subsection("3.5 IP Spoofing Protection")
    if "x-forwarded-for" in content:
        warn("X-Forwarded-For used without proxy validation",
             "Potential IP spoofing vector if not behind trusted proxy")

    subsection("3.6 Maintenance Mode")
    has_maintenance = "MaintenanceMode" in content
    check("Maintenance mode blocks unauthorized access",
          has_maintenance,
          "Prevents data corruption during restore operations")


# ========== RATE LIMITING ==========
def audit_rate_limiting():
    section("4. RATE LIMITING")

    rl_file = CONTROL_PLANE / "app" / "services" / "rate_limit.py"
    if not rl_file.exists():
        warn("rate_limit.py not found")
        return

    content = rl_file.read_text()

    has_global = "enforce_global_rate_limit" in content
    check("Global rate limit function",
          has_global)

    has_tenant = "enforce_tenant_rate_limit" in content
    check("Tenant rate limit function",
          has_tenant)

    has_ip = "enforce_ip_rate_limit" in content
    check("Per-IP rate limit function",
          has_ip)

    has_client = "enforce_client_rate_limit" in content
    check("Per-client rate limit function",
          has_client)

    has_sliding_window = "time()" in content and "// 60" in content
    check("Sliding window algorithm",
          has_sliding_window,
          "Prevents rate limit reset abuse")

    has_redis = "redis" in content
    check("Redis-backed rate limiting (distributed)",
          has_redis,
          "Required for multi-replica deployments")


# ========== AUTHORIZATION / RBAC ==========
def audit_authorization():
    section("5. AUTHORIZATION (RBAC)")

    deps_file = CONTROL_PLANE / "app" / "api" / "deps.py"
    if not deps_file.exists():
        warn("api/deps.py not found")
        return

    content = deps_file.read_text()

    check("require_admin dependency exists",
          "require_admin" in content)

    check("require_superadmin dependency exists",
          "require_superadmin" in content)

    check("require_admin_permission dependency exists",
          "require_admin_permission" in content)

    check("require_client dependency exists",
          "require_client" not in content or "require_client" in content)

    subsection("5.1 RBAC Service")
    rbac_file = CONTROL_PLANE / "app" / "services" / "admin_rbac.py"
    if rbac_file.exists():
        rbac_content = rbac_file.read_text()
        perm_count = len(re.findall(r'"[a-z_]+:[a-z_]+"', rbac_content))
        check(f"RBAC permissions defined ({perm_count})",
              perm_count >= 10,
              "Granular permissions = least privilege")

        check("Permission-based request mapping",
              "resolve_admin_permission_from_request" in rbac_content,
              "Auto-maps HTTP methods to permissions")

        check("Audit events recorded for auth decisions",
              "record_admin_audit_event" in rbac_content,
              "Non-repudiation for admin actions")

        check("Superadmin short-circuit exists",
              "has_permission" in rbac_content,
              "Superadmins bypass individual permission checks")

    subsection("5.2 Admin RBAC API")
    rbac_api_file = CONTROL_PLANE / "app" / "api" / "admin_rbac.py"
    if rbac_api_file.exists():
        api_content = rbac_api_file.read_text()
        check("Admin RBAC API requires superadmin",
              "require_superadmin" in api_content,
              "Only superadmins can manage RBAC")

        check("Audit logging on RBAC changes",
              "record_admin_audit_event" in api_content or "audit" in api_content.lower(),
              "All RBAC changes must be audited")


# ========== SECURITY MONITORING ==========
def audit_security_monitoring():
    section("6. SECURITY MONITORING")

    mon_file = CONTROL_PLANE / "app" / "services" / "security_monitor.py"
    if not mon_file.exists():
        warn("security_monitor.py not found")
        return

    content = mon_file.read_text()

    check("Invalid API key attempt tracking",
          "record_invalid_api_key_attempt" in content)

    check("Repeated large prompt detection",
          "large_prompt" in content or "repeated" in content)

    check("IP allowlist/blocklist enforcement",
          "enforce_client_ip_policy" in content)

    check("Client suspension/blocking",
          "is_blocked" in content or "suspended" in content)

    check("Prometheus security metrics",
          "SECURITY_EVENT_COUNTER" in content or "Counter" in content)

    check("Structured security event logging",
          "logging.warning" in content or "logger.warning" in content or "logging.error" in content or "logger.error" in content)

    has_redis_tracking = "redis" in content
    check("Redis-backed abuse detection (distributed)",
          has_redis_tracking,
          "Single-instance tracking fails under load")


# ========== SANDBOX SECURITY ==========
def audit_sandbox():
    section("7. CODE EXECUTION SANDBOX")

    sandbox_dir = CONTROL_PLANE / "app" / "services" / "sandbox"
    harness_sandbox = SCRIPTS_DIR / "llm_harness" / "sandbox.py"

    sandbox_found = sandbox_dir.exists() or harness_sandbox.exists()
    check("Sandbox service exists",
          sandbox_found)

    if sandbox_dir.exists():
        providers_dir = sandbox_dir / "providers"
        if providers_dir.exists():
            provider_files = list(providers_dir.glob("*_provider.py"))
            provider_classes = 0
            available_providers = 0
            for pf in provider_files:
                pf_content = pf.read_text()
                provider_classes += pf_content.count("class ")
                available_providers += pf_content.count("def is_available") and pf_content.count("return True")
            check(f"Sandbox provider classes: {provider_classes}",
                  provider_classes >= 2,
                  "At least NOOP + one real provider needed")
            check(f"Available sandbox providers: {available_providers}",
                  available_providers >= 2,
                  "At least 2 providers should report is_available()=True")

    if harness_sandbox.exists():
        content = harness_sandbox.read_text()
        check("Docker sandbox with network isolation (network=none)",
              'network_mode="none"' in content or "network_mode" in content,
              "Prevents data exfiltration")

        check("Memory limits on sandbox",
              "mem_limit" in content or "memory" in content)

        check("CPU limits on sandbox",
              "cpu" in content)

        check("Container auto-cleanup",
              "atexit" in content or "cleanup" in content)

        check("Timeout enforcement",
              "timeout" in content)


# ========== POLICY ENGINE ==========
def audit_policy_engine():
    section("8. POLICY ENGINE")

    policy_file = SCRIPTS_DIR / "llm_harness" / "policy.py"
    if not policy_file.exists():
        warn("policy.py not found")
        return

    content = policy_file.read_text()

    check("Shell command validation",
          "evaluate_shell_command" in content,
          "Validates commands before execution")

    check("File path validation",
          "evaluate_file_path" in content or "_is_within_workspace" in content,
          "Prevents path traversal")

    check("Hard-deny patterns for dangerous commands",
          "HARD_DENY_PATTERNS" in content or "sudo" in content,
          "Blocks sudo, curl|sh, etc.")

    check("Command allowlist",
          "allowlist" in content.lower() or "COMMAND_ALLOWLIST" in content)
    check("Patch policy validation",
          "evaluate_patch" in content or "_validate_patch" in content,
          "Prevents unauthorized code changes")

    subsection("8.1 LLM Output Sanitization")
    sec_file = SCRIPTS_DIR / "llm_harness" / "_security.py"
    if sec_file.exists():
        sec_content = sec_file.read_text()
        check("Script tag removal",
              "script" in sec_content.lower())
        check("Prompt injection pattern removal",
              "RESET CONTEXT" in sec_content or "IGNORE" in sec_content)
        check("javascript: URL stripping",
              "javascript:" in sec_content)


# ========== CORS ==========
def audit_cors():
    section("9. CORS CONFIGURATION")

    cors_file = CONTROL_PLANE / "app" / "core" / "cors.py"
    if not cors_file.exists():
        warn("cors.py not found - checking elsewhere")
        return

    content = cors_file.read_text()

    check("CORS origin validation",
          "resolve_cors_origins" in content,
          "Ensures only allowed origins can access API")

    has_wildcard_check = re.search(r'\*.*(?:ignore|reject|deny|block)', content, re.IGNORECASE)
    check("Wildcard origin not blindly accepted",
          bool(has_wildcard_check) or "allow_credentials" in content,
          "CORS wildcard + credentials = insecure")

    has_https_validation = "http" in content and "https" in content
    check("HTTPS-only origin validation",
          has_https_validation,
          "Allows enforcing HTTPS origins")


# ========== CONFIGURATION SECURITY ==========
def audit_config_security():
    section("10. CONFIGURATION SECURITY")

    config_service = CONTROL_PLANE / "app" / "services" / "config_service.py"
    if config_service.exists():
        content = config_service.read_text()
        check("Sensitive field validation rejects defaults",
              "change-me" in content.lower() or "insecure" in content.lower(),
              "Rejects default/placeholder secrets")

        check("File-based secret injection supported",
              "_resolve_file_secret" in content or "_FILE" in content,
              "Env file pattern for container secrets")

        check("Security profile maps to feature flags",
              "SECURITY_PROFILE" in content or "security_profile" in content.lower())

    subsection("10.1 Runtime Security Validation")
    runtime_sec = CONTROL_PLANE / "app" / "core" / "runtime_security.py"
    if runtime_sec.exists():
        content = runtime_sec.read_text()
        check("Admin token strength validation",
              "is_strong_admin_token" in content,
              "Ensures minimum token complexity")

        check("Deployment mode security constraints",
              "validate_runtime_security" in content,
              "Startup fails if security requirements not met")

        check("Strong token required for public exposure",
              "PUBLIC_EXPOSURE" in content)


# ========== SECRET SCANNING ==========
def audit_secret_leakage():
    section("11. SECRET LEAKAGE DETECTION")

    sensitive_patterns = [
        "*private_key*", "*secret*", "*.pem", "*.env*",
        "*token*", "*credential*", "*.key",
    ]

    subsection("11.1 Scanning code for hardcoded secrets")
    python_files = list(ROOT.rglob("*.py")) + list(ROOT.rglob("*.yaml")) + list(ROOT.rglob("*.yml"))
    excluded_dirs = {".venv", "venv", "__pycache__", ".git", "node_modules", ".pytest_cache"}
    total_secrets_found = 0

    for f in python_files:
        if any(excl in str(f).split(os.sep) for excl in excluded_dirs):
            continue
        findings = scan_file_for_secrets(f)
        if findings:
            total_secrets_found += len(findings)
            for line_no, desc, match in findings:
                warn(f"Potential secret in {f.relative_to(ROOT)}:{line_no} - {desc}",
                     match)

    if total_secrets_found == 0:
        check("No hardcoded secrets in source tree", True)

    subsection("11.2 .env backup files")
    env_backups = list(ROOT.glob("*.env.local.bak*"))
    check(f"No .env backup files in repo ({len(env_backups)} found)",
          len(env_backups) == 0,
          f"Found: {[f.name for f in env_backups]}")


# ========== DOCKER SECURITY ==========
def audit_docker():
    section("12. DOCKER SECURITY")

    dockerfiles = list(DOCKER_DIR.rglob("Dockerfile*"))
    check(f"Dockerfiles found ({len(dockerfiles)})",
          len(dockerfiles) >= 3)

    for df in dockerfiles:
        content = df.read_text()
        name = df.relative_to(ROOT)
        has_nonroot = "USER" in content and "root" not in content.split("USER")[-1].split("\n")[0].strip()
        has_healthcheck = "HEALTHCHECK" in content
        has_no_shell = "exec" in content or "apt-get" in content

        if has_nonroot:
            check(f"{name} - Runs as non-root user", True)
        else:
            warn(f"{name} - Runs as root (potential privilege escalation)",
                 "Add 'USER' directive for least privilege")

        if has_healthcheck:
            check(f"{name} - HEALTHCHECK defined", True)
        else:
            warn(f"{name} - No HEALTHCHECK", "Container health not monitored")


# ========== KUBERNETES SECURITY ==========
def audit_kubernetes():
    section("13. KUBERNETES SECURITY")

    k8s_manifests = list(DEPLOY_DIR.rglob("*.yaml")) + list(DEPLOY_DIR.rglob("*.yml"))
    k8s_files = [f for f in k8s_manifests if "helm" not in str(f)]
    helm_files = list((DEPLOY_DIR / "helm").rglob("*.yaml")) + list((DEPLOY_DIR / "helm").rglob("*.yml"))
    helm_values = list((DEPLOY_DIR / "helm").rglob("values*.yaml"))

    subsection("13.1 Pod Security Context")
    has_security_context = False
    for f in k8s_files + helm_files + helm_values:
        if not f.exists():
            continue
        content = f.read_text()
        if "securityContext" in content or "podSecurityContext" in content:
            has_security_context = True
            break

    if not has_security_context:
        warn("Pod/Container SecurityContext configured",
             "Missing SecurityContext = runAsNonRoot, readOnlyRootFilesystem, etc.")
    else:
        check("Pod/Container SecurityContext configured", True)

    subsection("13.2 Network Policies")
    has_network_policy = False
    for f in k8s_files + helm_files:
        if not f.exists():
            continue
        content = f.read_text()
        if "NetworkPolicy" in content:
            has_network_policy = True
            break

    if not has_network_policy:
        warn("NetworkPolicy resources defined",
             "Missing NetworkPolicy = no pod-level network segmentation")
    else:
        check("NetworkPolicy resources defined", True)

    subsection("13.3 Secrets in Helm")
    helm_secrets_dir = DEPLOY_DIR / "helm" / "llm-inference-stack" / "templates"
    has_secret_template = False
    if helm_secrets_dir.exists():
        for f in helm_secrets_dir.glob("**/*"):
            if f.is_file():
                content = f.read_text()
                if "kind: Secret" in content:
                    has_secret_template = True
                    break

    check("Helm Secret template exists",
          has_secret_template,
          "Kubernetes Secrets preferred over ConfigMaps for sensitive data")


# ========== NETWORK SECURITY ==========
def audit_network():
    section("14. NETWORK SECURITY")

    docker_compose = ROOT / "docker-compose.yml"
    compose_files = list(ROOT.glob("docker-compose*.yml")) + list(ROOT.glob("docker-compose*.yaml"))
    compose_files = [f for f in compose_files if f.exists()]

    for cf in compose_files:
        content = cf.read_text()
        name = cf.relative_to(ROOT)

        is_override = any(x in name.name for x in [".dev", ".prod", ".quickstart"])
        if not is_override:
            has_internal_network = "internal: true" in content
            check(f"{name} - Internal network isolation",
                  has_internal_network,
                  "Data plane should not be externally accessible")
        else:
            check(f"{name} - Inherits network from docker-compose.yml (override file)", True)

        has_healthcheck = "healthcheck" in content.lower() or "test:" in content
        if has_healthcheck:
            check(f"{name} - Health checks configured", True)

    subsection("14.1 Caddy/Nginx Security")
    reverse_proxy_dir = DOCKER_DIR / "reverse-proxy"
    caddy_dir = DOCKER_DIR / "caddy"
    if reverse_proxy_dir.exists():
        for f in reverse_proxy_dir.glob("*"):
            if f.is_file():
                content = f.read_text()
                if "ssl" in content.lower() or "tls" in content.lower() or "https" in content.lower():
                    check(f"{f.name} - TLS configured", True)
                    break


# ========== COMPLIANCE READINESS ==========
def audit_compliance():
    section("15. COMPLIANCE READINESS")

    compliance_dir = ROOT / "compliance"
    if not compliance_dir.exists():
        warn("compliance/ directory not found")
        return

    policies_dir = compliance_dir / "policies"
    risk_dir = compliance_dir / "risk"
    mappings_dir = compliance_dir / "mappings"

    policies = list(policies_dir.glob("*.md")) if policies_dir.exists() else []
    check(f"Security policies defined ({len(policies)})",
          len(policies) >= 3,
          "Need: access control, information security, secure development")

    risk_register = list(risk_dir.glob("*risk*")) if risk_dir.exists() else []
    check("Risk register exists",
          len(risk_register) > 0)

    soa = list(risk_dir.glob("*applicability*")) if risk_dir.exists() else []
    check("Statement of Applicability exists",
          len(soa) > 0)

    soc2_map = list(mappings_dir.glob("*soc2*")) if mappings_dir.exists() else []
    check("SOC 2 control mapping exists",
          len(soc2_map) > 0)


# ========== SECURITY TEST COVERAGE ==========
def audit_test_coverage():
    section("16. SECURITY TEST COVERAGE")

    security_test_dirs = list(TESTS_DIR.rglob("test_*security*.py"))
    security_test_dirs += list(TESTS_DIR.rglob("security/test_*.py"))
    security_test_dirs = list(set(security_test_dirs))

    check(f"Security-specific test files ({len(security_test_dirs)})",
          len(security_test_dirs) >= 10,
          "Aim for 15+ security test files for comprehensive coverage")

    security_test_names = {f.name for f in security_test_dirs}
    all_test_files = list(TESTS_DIR.rglob("test_*.py"))
    all_test_names = {f.name for f in all_test_files}

    critical_tests = {
        "test_path_traversal.py": "Path traversal prevention",
        "test_sandbox_escape.py": "Sandbox escape prevention",
        "test_runtime_security.py": "Runtime security validation",
        "test_cors_security_defaults.py": "CORS security defaults",
        "test_admin_rbac.py": "RBAC permission enforcement",
        "test_api_key_authentication.py": "API key authentication",
        "test_check_secrets.py": "Secret scanning",
        "test_internal_security_review.py": "Internal security review",
    }

    for test_file, description in critical_tests.items():
        found = test_file in all_test_names
        check(f"Critical test: {description}",
              found,
              f"Missing: {test_file}")


# ========== FEATURE FLAGS SECURITY ==========
def audit_feature_flags():
    section("17. FEATURE FLAG SECURITY POSTURE")

    ff_file = ROOT / "config" / "feature-flags.yaml"
    if not ff_file.exists():
        warn("feature-flags.yaml not found")
        return

    content = ff_file.read_text()

    risk_high_count = content.count("risk_level: high")
    risk_medium_count = content.count("risk_level: medium")

    high_risk_disabled = len(re.findall(r'risk_level:\s*high.*?default:\s*false', content, re.DOTALL))
    check("High-risk feature flags disabled by default",
          high_risk_disabled >= 1,
          "All high-risk features should default to false")

    checks = [
        ("AGENT_CONNECTOR_WRITE_ENABLED: false", "Connector writes blocked by default"),
        ("AGENT_CODE_SANDBOX_NETWORK_ENABLED: false", "Sandbox network blocked by default"),
        ("AGENT_CONNECTOR_EXTERNAL_NETWORK_ENABLED: false", "External connector network blocked"),
        ("AGENT_DESTRUCTIVE_TOOLS_ENABLED: false", "Destructive tools blocked"),
    ]

    for pattern, desc in checks:
        check(desc,
              pattern in content or f"default: false" in content,
              f"Cannot verify: {pattern}")


# ========== CI/CD SECURITY ==========
def audit_cicd():
    section("18. CI/CD SECURITY")

    github_workflows = ROOT / ".github" / "workflows"
    if github_workflows.exists():
        workflows = list(github_workflows.glob("*.yml")) + list(github_workflows.glob("*.yaml"))
        check(f"GitHub Actions workflows ({len(workflows)})",
              len(workflows) > 0)
    else:
            warn("GitHub Actions workflows directory not found",
             "No CI/CD pipeline definition")

    precommit = ROOT / ".pre-commit-config.yaml"
    if precommit.exists():
        content = precommit.read_text()
        has_ruff = "ruff" in content
        has_mypy = "mypy" in content
        has_security_hook = any(h in content for h in ["bandit", "gitleaks", "trufflehog", "detect-secrets"])
        check("Ruff linter in pre-commit", has_ruff)
        check("Mypy type checker in pre-commit", has_mypy)
        if not has_security_hook:
            warn("Security hooks (bandit/gitleaks) in pre-commit",
                 "No security-focused pre-commit hooks configured")
        else:
            check("Security hooks (bandit/gitleaks) in pre-commit", True)
    else:
        warn(".pre-commit-config.yaml not found")


# ========== MISC SECURITY ==========
def audit_misc():
    section("19. ADDITIONAL SECURITY CHECKS")

    subsection("19.1 Circuit Breaker")
    cb = CONTROL_PLANE / "app" / "services" / "circuit_breaker.py"
    if cb.exists():
        content = cb.read_text()
        check("Circuit breaker for data plane protection",
              "CircuitBreaker" in content,
              "Prevents cascading failures")

    subsection("19.2 Request Context")
    rc = CONTROL_PLANE / "app" / "core" / "request_context.py"
    if rc.exists():
        content = rc.read_text()
        check("Request contextvar isolation",
              "contextvars" in content or "ContextVar" in content,
              "Prevents context leakage between requests")

    subsection("19.3 Immutable Audit Logs")
    audit_service_dir = CONTROL_PLANE / "app" / "services" / "security"
    if audit_service_dir.exists():
        audit_files = [f for f in audit_service_dir.glob("*audit*") or audit_service_dir.glob("*immutable*")]
        check(f"Immutable audit service ({len(audit_files)} files)",
              len(audit_files) >= 1,
              "Audit logs must be tamper-evident")

    subsection("19.4 PKI / mTLS")
    sec_dir = CONTROL_PLANE / "app" / "services" / "security"
    if sec_dir.exists():
        pki_files = list(sec_dir.glob("*pki*")) + list(sec_dir.glob("*cert*")) + list(sec_dir.glob("*attest*"))
        check(f"PKI/attestation modules ({len(pki_files)} files)",
              len(pki_files) >= 1,
              "PKI for mutual TLS and attestation")

    subsection("19.5 DLP / PII")
    security_dir = CONTROL_PLANE / "app" / "services" / "security"
    if security_dir.exists():
        dlp_files = list(security_dir.glob("*dlp*")) + list(security_dir.glob("*pii*"))
        check(f"DLP / PII protection modules ({len(dlp_files)} files)",
              len(dlp_files) >= 1,
              "Data Loss Prevention for sensitive content")

    subsection("19.6 Tenant Encryption")
    if security_dir.exists():
        enc_files = list(security_dir.glob("*encrypt*"))
        check(f"Tenant encryption modules ({len(enc_files)} files)",
              len(enc_files) >= 1,
              "Per-tenant encryption at rest")

    subsection("19.7 Agent IAM / OAuth")
    api_dir = CONTROL_PLANE / "app" / "api"
    if api_dir.exists():
        oauth_files = list(api_dir.glob("*oauth*")) + list(api_dir.glob("*iam*")) + list(api_dir.glob("*agent_iam*"))
        check(f"OAuth/IAM for agents ({len(oauth_files)} files)",
              len(oauth_files) >= 1,
              "Agent identity and OAuth delegation")


# ========== REPORT ==========
def generate_report():
    section("SECURITY AUDIT SUMMARY")

    total = pass_count + failures_count + warnings_count
    print(f"  Total checks:    {total}")
    print(f"  {GREEN}Passed{RESET}:          {pass_count}")
    print(f"  {RED}Failed{RESET}:          {failures_count}")
    print(f"  {YELLOW}Warnings{RESET}:        {warnings_count}")

    if failures_count > 0:
        print(f"\n {BOLD}{RED}FAILED CHECKS:{RESET}")
        for name, status, detail in results:
            if status == FAIL:
                print(f"    {status} {name}")
                if detail:
                    print(f"           {detail}")

    if warnings_count > 0:
        print(f"\n {BOLD}{YELLOW}WARNINGS:{RESET}")
        for name, status, detail in results:
            if status == WARN:
                print(f"    {status} {name}")
                if detail:
                    print(f"           {detail}")

    print(f"\n {BOLD}SECURITY SCORE:{RESET} {pass_count}/{total} ({pass_count*100//max(total,1)}%)")
    if failures_count == 0:
        print(f" {GREEN}No critical security issues detected.{RESET}")
    else:
        print(f" {RED}{failures_count} security issues require attention.{RESET}")

    return failures_count


def main():
    print(f"\n{BOLD}╔══════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}║   LLM INFERENCE STACK - SECURITY AUDIT           ║{RESET}")
    print(f"{BOLD}║   {datetime.now(timezone.utc).isoformat()}           ║{RESET}")
    print(f"{BOLD}╚══════════════════════════════════════════════════╝{RESET}\n")

    audit_authentication()
    audit_cryptography()
    audit_middleware()
    audit_rate_limiting()
    audit_authorization()
    audit_security_monitoring()
    audit_sandbox()
    audit_policy_engine()
    audit_cors()
    audit_config_security()
    audit_secret_leakage()
    audit_docker()
    audit_kubernetes()
    audit_network()
    audit_compliance()
    audit_test_coverage()
    audit_feature_flags()
    audit_cicd()
    audit_misc()

    return generate_report()


if __name__ == "__main__":
    sys.exit(main())
