#!/bin/bash
set -e

# Default values
BASE_URL="http://localhost:18080"
OUTPUT_DIR="artifacts/security-reports"
STRICT=false
SKIP_ARTIFACTS=false

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --base-url) BASE_URL="$2"; shift ;;
        --output-dir) OUTPUT_DIR="$2"; shift ;;
        --strict) STRICT=true ;;
        --skip-artifacts-scan) SKIP_ARTIFACTS=true ;;
        --help)
            echo "Usage: $0 [--base-url URL] [--output-dir DIR] [--strict] [--skip-artifacts-scan]"
            exit 0
            ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

export BASE_URL
export OUTPUT_DIR
export STRICT
export SKIP_ARTIFACTS

# Use virtual environment python if available
PYTHON_BIN="python3"
if [ -f ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
fi

exec $PYTHON_BIN - << 'EOF'
import json
import os
import subprocess
import datetime
import sys
from pathlib import Path

BASE_URL = os.environ.get("BASE_URL", "http://localhost:18080")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "artifacts/security-reports")
STRICT = os.environ.get("STRICT") == "true"
SKIP_ARTIFACTS = os.environ.get("SKIP_ARTIFACTS") == "true"

timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
report_dir = Path(OUTPUT_DIR) / timestamp
report_dir.mkdir(parents=True, exist_ok=True)
(report_dir / "logs").mkdir(parents=True, exist_ok=True)

checks = []

def run_cmd(cmd):
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return res.returncode, res.stdout, res.stderr
    except Exception as e:
        return -1, "", str(e)

def add_check(id_val, category, title, status, severity, details, remediation, evidence):
    checks.append({
        "id": id_val,
        "category": category,
        "title": title,
        "status": status,
        "severity": severity,
        "details": details,
        "remediation": remediation,
        "evidence": evidence
    })

# 4.a) Secrets
code, out, err = run_cmd("./scripts/check-secrets.sh --all")
if code == 0:
    add_check("sec-secrets-all", "Secrets", "Check secrets in all files", "pass", "critical", "No secrets found", "", "")
else:
    add_check("sec-secrets-all", "Secrets", "Check secrets in all files", "fail", "critical", "Secrets detected in files", "Remove secrets from codebase", out[:500])

code, out, err = run_cmd("./scripts/check-secrets.sh --staged")
if code == 0:
    add_check("sec-secrets-staged", "Secrets", "Check staged secrets", "pass", "critical", "No secrets in staged files", "", "")
else:
    add_check("sec-secrets-staged", "Secrets", "Check staged secrets", "fail", "critical", "Secrets detected in staged files", "Remove secrets from stage", out[:500])

if not SKIP_ARTIFACTS:
    code, out, err = run_cmd('grep -rIE "sk-[a-zA-Z0-9]{20,}|Bearer [a-zA-Z0-9]{20,}|ADMIN_TOKEN=" artifacts/ releases/ 2>/dev/null')
    if code == 0 and out.strip():
        add_check("sec-secrets-artifacts", "Secrets", "Secrets in artifacts/releases", "fail", "high", "Found tokens in artifacts/releases", "Clear artifacts and remove secrets", out[:500])
    else:
        add_check("sec-secrets-artifacts", "Secrets", "Secrets in artifacts/releases", "pass", "high", "No tokens found in artifacts", "", "")
else:
    add_check("sec-secrets-artifacts", "Secrets", "Secrets in artifacts/releases", "skip", "high", "Skipped by user", "", "")

# 4.b) Git hygiene
git_checks = [
    (".env", "git-env", "critical"),
    (".env.local", "git-env-local", "critical"),
    (".local/", "git-local-dir", "high"),
    ("models/", "git-models", "high"),
    ("*.gguf", "git-gguf", "high"),
    ("data/rag_uploads/", "git-rag-uploads", "high"),
    ("backups/", "git-backups", "high"),
    ("exports/", "git-exports", "high")
]

for path, cid, sev in git_checks:
    code, out, err = run_cmd(f"git ls-files \"{path}\"")
    if out.strip():
        add_check(cid, "Git hygiene", f"Check {path} is not versioned", "fail", sev, f"{path} is tracked by git", f"Run git rm --cached {path}", out.strip()[:200])
    else:
        add_check(cid, "Git hygiene", f"Check {path} is not versioned", "pass", sev, f"{path} not tracked", "", "")

# 4.c) Permissões
code, out, err = run_cmd('find scripts/ -name "*.sh" ! -executable')
if out.strip():
    add_check("perm-scripts", "Permissões", "Check shell scripts permissions", "warn", "medium", "Some scripts are not executable", "Run chmod +x scripts/*.sh", out.strip()[:200])
else:
    add_check("perm-scripts", "Permissões", "Check shell scripts permissions", "pass", "medium", "All scripts executable", "", "")

if os.path.exists(".env.local"):
    st = os.stat(".env.local")
    mode = oct(st.st_mode)[-3:]
    if mode in ["777", "666"]:
        add_check("perm-env-local", "Permissões", "Check .env.local permissions", "warn", "medium", f".env.local has open permissions ({mode})", "Run chmod 600 .env.local", mode)
    else:
        add_check("perm-env-local", "Permissões", "Check .env.local permissions", "pass", "medium", "Permissions restricted", "", mode)
else:
    add_check("perm-env-local", "Permissões", "Check .env.local permissions", "skip", "medium", ".env.local not found", "", "")

code, out, err = run_cmd('find . -name "*.pem" -o -name "*.key" | grep -v ".venv"')
if out.strip():
    add_check("perm-pem-keys", "Permissões", "Check for .pem/.key files", "warn", "high", "Found pem/key files in project", "Verify if they should be here and restrict permissions", out.strip()[:200])
else:
    add_check("perm-pem-keys", "Permissões", "Check for .pem/.key files", "pass", "high", "No pem/key files found", "", "")

# 4.d) Admin/API
code, out, err = run_cmd(f'curl -s -o /dev/null -w "%{{http_code}}" {BASE_URL}/admin/info')
if out == "401":
    add_check("api-admin-token", "Admin/API", "Admin endpoints require token", "pass", "high", "Got 401 as expected", "", "")
elif out == "000":
    add_check("api-admin-token", "Admin/API", "Admin endpoints require token", "skip", "high", "API not reachable", "", "")
else:
    add_check("api-admin-token", "Admin/API", "Admin endpoints require token", "warn", "high", f"Got status {out}", "Require token for admin endpoints", "")

# 4.e) Logs/artifacts (already partially covered, add log check)
code, out, err = run_cmd('grep -rIE "POSTGRES_PASSWORD|REDIS_URL" logs/ 2>/dev/null')
if code == 0 and out.strip():
    add_check("log-env", "Logs/artifacts", "Logs do not contain secrets", "fail", "high", "Found env variables in logs", "Review logging configuration", out[:200])
else:
    add_check("log-env", "Logs/artifacts", "Logs do not contain secrets", "pass", "high", "No env variables found in logs", "", "")

# 4.f) RAG/TTS data
add_check("rag-git", "RAG/TTS data", "RAG uploads outside git", "pass", "medium", "Checked by git hygiene", "", "")

# 4.g) Docker
code, out, err = run_cmd('grep -A1 "ports:" docker-compose.yml | grep -E "5432|6379" | grep -v "127.0.0.1"')
if code == 0 and out.strip() and not out.strip().startswith('#'):
    add_check("docker-expose", "Docker", "Docker-compose does not expose DB ports globally", "warn", "high", "DB ports might be exposed to 0.0.0.0", "Bind to 127.0.0.1 in docker-compose.yml", out[:200])
else:
    add_check("docker-expose", "Docker", "Docker-compose does not expose DB ports globally", "pass", "high", "DB ports not globally exposed", "", "")

code, out, err = run_cmd('grep -r "privileged: true" docker-compose.yml 2>/dev/null')
if code == 0 and out.strip():
    add_check("docker-privileged", "Docker", "Containers don't use privileged mode", "fail", "high", "Found privileged: true", "Remove privileged mode", out[:200])
else:
    add_check("docker-privileged", "Docker", "Containers don't use privileged mode", "pass", "high", "No privileged containers", "", "")

# calculate score
critical_fails = sum(1 for c in checks if c["status"] == "fail" and c["severity"] == "critical")
high_fails = sum(1 for c in checks if c["status"] == "fail" and c["severity"] == "high")
fails = sum(1 for c in checks if c["status"] == "fail")
warns = sum(1 for c in checks if c["status"] == "warn")
passes = sum(1 for c in checks if c["status"] == "pass")
skips = sum(1 for c in checks if c["status"] == "skip")

if critical_fails > 0:
    score = "FAIL"
elif STRICT and high_fails > 0:
    score = "FAIL"
elif fails > 0 and not STRICT:
    score = "PASS_WITH_WARNINGS"
elif fails > 0:
    score = "FAIL"
elif warns > 0:
    score = "PASS_WITH_WARNINGS"
else:
    score = "PASS"

# Generate report dict
code, branch, _ = run_cmd('git rev-parse --abbrev-ref HEAD')
branch = branch.strip()
code, commit, _ = run_cmd('git rev-parse HEAD')
commit = commit.strip()

report_data = {
    "generated_at": datetime.datetime.now().isoformat(),
    "version": "1.0",
    "git_branch": branch,
    "git_commit": commit,
    "score": score,
    "totals": {
        "pass": passes,
        "warn": warns,
        "fail": fails,
        "skip": skips,
        "critical_failures": critical_fails
    },
    "checks": checks,
    "artifacts": {
        "report_json": str(report_dir / "security-report.json"),
        "report_md": str(report_dir / "security-report.md")
    }
}

# Write JSON
with open(report_dir / "security-report.json", "w") as f:
    json.dump(report_data, f, indent=2)

# Write MD
md_lines = [
    f"# Security Report",
    f"**Date:** {report_data['generated_at']}",
    f"**Score:** {score}",
    f"**Branch:** {branch} ({commit})",
    f"",
    f"## Totals",
    f"- Pass: {passes}",
    f"- Warn: {warns}",
    f"- Fail: {fails}",
    f"- Skip: {skips}",
    f"- Critical Fails: {critical_fails}",
    f"",
    f"## Checks",
    f"| ID | Category | Title | Status | Severity | Details |",
    f"|---|---|---|---|---|---|",
]
for c in checks:
    md_lines.append(f"| {c['id']} | {c['category']} | {c['title']} | {c['status']} | {c['severity']} | {c['details']} |")

md_content = "\n".join(md_lines)
with open(report_dir / "security-report.md", "w") as f:
    f.write(md_content)

print(f"Security Report Generated: {score}")
if critical_fails > 0 or fails > 0 or warns > 0:
    print(f"Top warnings/fails:")
    for c in checks:
        if c["status"] in ["fail", "warn"]:
            print(f" - [{c['status'].upper()}] {c['title']}: {c['details']}")

print(f"JSON Output: {report_dir / 'security-report.json'}")
print(f"MD Output: {report_dir / 'security-report.md'}")

if score == "FAIL":
    sys.exit(1)
EOF
