#!/bin/bash
set -euo pipefail

BASE_URL="http://localhost:18080"
OUTPUT_DIR="artifacts/security-reports"
STRICT=false
SKIP_ARTIFACTS=false

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --base-url)
            BASE_URL="$2"
            shift
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift
            ;;
        --strict)
            STRICT=true
            ;;
        --skip-artifacts-scan)
            SKIP_ARTIFACTS=true
            ;;
        --help)
            echo "Usage: $0 [--base-url URL] [--output-dir DIR] [--strict] [--skip-artifacts-scan]"
            exit 0
            ;;
        *)
            echo "Unknown parameter: $1"
            exit 1
            ;;
    esac
    shift
done

export BASE_URL OUTPUT_DIR STRICT SKIP_ARTIFACTS

PYTHON_BIN="python3"
if [ -f ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
fi

exec "$PYTHON_BIN" - <<'EOF'
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

BASE_URL = os.environ.get("BASE_URL", "http://localhost:18080")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "artifacts/security-reports")
STRICT = os.environ.get("STRICT") == "true"
SKIP_ARTIFACTS = os.environ.get("SKIP_ARTIFACTS") == "true"

CLASSIFICATIONS = [
    "real_secret_suspected",
    "fixture_expected",
    "generated_artifact",
    "obsolete_release_file",
    "needs_review",
]

STATUS_BY_CLASSIFICATION = {
    "real_secret_suspected": ("fail", "critical"),
    "fixture_expected": ("skip", "low"),
    "generated_artifact": ("warn", "high"),
    "obsolete_release_file": ("warn", "high"),
    "needs_review": ("warn", "medium"),
}

timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
report_dir = Path(OUTPUT_DIR) / timestamp
report_dir.mkdir(parents=True, exist_ok=True)
(report_dir / "logs").mkdir(parents=True, exist_ok=True)

checks = []


def run_cmd(cmd: str):
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return res.returncode, res.stdout, res.stderr
    except Exception as exc:
        return -1, "", str(exc)


def add_check(check_id, category, title, status, severity, details, remediation="", evidence="", meta=None):
    checks.append(
        {
            "id": check_id,
            "category": category,
            "title": title,
            "status": status,
            "severity": severity,
            "details": details,
            "remediation": remediation,
            "evidence": evidence,
            "meta": meta or {},
        }
    )


def parse_classified_output(output: str):
    grouped = {name: [] for name in CLASSIFICATIONS}
    unclassified = []
    for line in output.splitlines():
        matched = False
        for classification in CLASSIFICATIONS:
            token = f"[{classification}]"
            if token in line:
                grouped[classification].append(line)
                matched = True
                break
        if not matched and "Potential" in line:
            unclassified.append(line)
    if unclassified:
        grouped["needs_review"].extend(unclassified)
    return grouped


def add_secret_scan_results(check_id_prefix: str, title_context: str, output: str, scope_hint: str):
    grouped = parse_classified_output(output)
    total_findings = sum(len(lines) for lines in grouped.values())

    worst_status = "pass"
    worst_severity = "low"
    if grouped["real_secret_suspected"]:
        worst_status, worst_severity = "fail", "critical"
    elif grouped["generated_artifact"] or grouped["obsolete_release_file"] or grouped["needs_review"]:
        worst_status, worst_severity = "warn", "high"
    elif grouped["fixture_expected"]:
        worst_status, worst_severity = "skip", "low"

    summary_details = (
        "No secret findings."
        if total_findings == 0
        else f"Classified {total_findings} finding(s) for {title_context}."
    )
    add_check(
        check_id_prefix,
        "Secrets",
        f"Secrets scan ({title_context})",
        worst_status,
        worst_severity,
        summary_details,
        "Review classified findings below.",
        json.dumps({name: len(lines) for name, lines in grouped.items()}),
        meta={"scope": scope_hint, "classifications": {name: len(lines) for name, lines in grouped.items()}},
    )

    for classification in CLASSIFICATIONS:
        lines = grouped[classification]
        if not lines:
            continue

        status, severity = STATUS_BY_CLASSIFICATION[classification]
        details = {
            "real_secret_suspected": f"Found suspected real secrets in {title_context}.",
            "fixture_expected": f"Found authorized fake fixtures in {title_context}.",
            "generated_artifact": f"Found secrets in generated artifacts for {title_context}.",
            "obsolete_release_file": f"Found secrets in release files for {title_context}.",
            "needs_review": f"Found items needing manual review in {title_context}.",
        }[classification]
        remediation = {
            "real_secret_suspected": "Remove the secret or replace it with runtime-generated test data.",
            "fixture_expected": "No action required if the fixture policy still applies.",
            "generated_artifact": "Purge or redact generated artifacts that contain secrets.",
            "obsolete_release_file": "Clean up or regenerate release files without embedded secrets.",
            "needs_review": "Review the finding manually and tighten the classifier if appropriate.",
        }[classification]
        add_check(
            f"{check_id_prefix}-{classification}",
            "Secrets",
            f"{classification} ({title_context})",
            status,
            severity,
            details,
            remediation,
            "\n".join(lines)[:1000],
            meta={"scope": scope_hint, "classification": classification, "count": len(lines)},
        )


code, out, err = run_cmd("./scripts/check-secrets.sh --all --verbose")
add_secret_scan_results("sec-secrets-all", "all files", out, "repository")

code, out, err = run_cmd("./scripts/check-secrets.sh --staged --verbose")
add_secret_scan_results("sec-secrets-staged", "staged files", out, "git_staged")

if not SKIP_ARTIFACTS:
    _, art_out, _ = run_cmd("./scripts/check-secrets.sh --path artifacts --verbose")
    _, rel_out, _ = run_cmd("./scripts/check-secrets.sh --path releases --verbose")
    add_secret_scan_results(
        "sec-secrets-artifacts",
        "artifacts/releases",
        "\n".join([art_out, rel_out]).strip(),
        "artifacts_and_releases",
    )
else:
    add_check(
        "sec-secrets-artifacts",
        "Secrets",
        "Secrets scan (artifacts/releases)",
        "skip",
        "high",
        "Artifacts/releases scan skipped by user.",
        "",
        "",
        meta={"scope": "artifacts_and_releases", "skipped": True},
    )

git_checks = [
    (".env", "git-env", "critical"),
    (".env.local", "git-env-local", "critical"),
    (".local/", "git-local-dir", "high"),
    ("models/", "git-models", "high"),
    ("*.gguf", "git-gguf", "high"),
    ("data/rag_uploads/", "git-rag-uploads", "high"),
    ("backups/", "git-backups", "high"),
    ("exports/", "git-exports", "high"),
]

for path, check_id, severity in git_checks:
    code, out, err = run_cmd(f'git ls-files "{path}"')
    if out.strip():
        add_check(
            check_id,
            "Git hygiene",
            f"Check {path} is not versioned",
            "fail",
            severity,
            f"{path} is tracked by git.",
            f"Run git rm --cached {path}",
            out.strip()[:500],
        )
    else:
        add_check(
            check_id,
            "Git hygiene",
            f"Check {path} is not versioned",
            "pass",
            severity,
            f"{path} not tracked.",
        )

code, out, err = run_cmd('find scripts/ -name "*.sh" ! -executable')
if out.strip():
    add_check(
        "perm-scripts",
        "Permissions",
        "Check shell scripts permissions",
        "warn",
        "medium",
        "Some scripts are not executable.",
        "Run chmod +x scripts/*.sh",
        out.strip()[:500],
    )
else:
    add_check(
        "perm-scripts",
        "Permissions",
        "Check shell scripts permissions",
        "pass",
        "medium",
        "All scripts executable.",
    )

if os.path.exists(".env.local"):
    mode = oct(os.stat(".env.local").st_mode)[-3:]
    if mode in {"777", "666"}:
        add_check(
            "perm-env-local",
            "Permissions",
            "Check .env.local permissions",
            "warn",
            "medium",
            f".env.local has open permissions ({mode}).",
            "Run chmod 600 .env.local",
            mode,
        )
    else:
        add_check(
            "perm-env-local",
            "Permissions",
            "Check .env.local permissions",
            "pass",
            "medium",
            "Permissions restricted.",
            evidence=mode,
        )
else:
    add_check(
        "perm-env-local",
        "Permissions",
        "Check .env.local permissions",
        "skip",
        "medium",
        ".env.local not found.",
    )

code, out, err = run_cmd(
    'find . -type f \\( -name "*.pem" -o -name "*.key" \\) '
    '-not -path "./.venv/*" -not -path "./.git/*" -not -path "./.cache/*" | sort'
)
if out.strip():
    found_files = [line.strip() for line in out.splitlines() if line.strip()]
    allowed = []
    unauthorized = []
    for file_path in found_files:
        normalized = file_path.removeprefix("./")
        name = Path(normalized).name
        content = Path(normalized).read_text(errors="ignore")
        marker_ok = (
            "FAKE TEST KEY - DO NOT USE" in content
            or "FAKE SECRET FOR TESTS ONLY" in content
        )
        in_allowed_path = normalized.startswith("tests/fixtures/")
        allowed_name = "fake_" in name or "fixture_" in name
        blocked_area = normalized.startswith(("releases/", "docs/", "scripts/", "control_plane/"))
        if in_allowed_path and allowed_name and marker_ok and not blocked_area:
            allowed.append(normalized)
        else:
            unauthorized.append(normalized)

    if unauthorized:
        add_check(
            "perm-pem-keys",
            "Permissions",
            "Check for .pem/.key files",
            "fail",
            "high",
            "Unauthorized pem/key files found.",
            "Remove real keys or move clearly fake fixtures to tests/fixtures/ with markers.",
            "\n".join(unauthorized)[:1000],
        )
    elif allowed:
        add_check(
            "perm-pem-keys",
            "Permissions",
            "Check for .pem/.key files",
            "skip",
            "low",
            f"Only authorized fake fixtures found ({len(allowed)}).",
            "",
            "\n".join(allowed)[:1000],
            meta={"classification": "fixture_expected", "count": len(allowed)},
        )
    else:
        add_check(
            "perm-pem-keys",
            "Permissions",
            "Check for .pem/.key files",
            "pass",
            "high",
            "No pem/key files found.",
        )
else:
    add_check(
        "perm-pem-keys",
        "Permissions",
        "Check for .pem/.key files",
        "pass",
        "high",
        "No pem/key files found.",
    )

code, out, err = run_cmd(f'curl -s -o /dev/null -w "%{{http_code}}" {BASE_URL}/admin/clients')
if out == "401":
    add_check(
        "api-admin-token",
        "Admin/API",
        "Admin endpoints require token",
        "pass",
        "high",
        "Got 401 as expected from /admin/clients.",
    )
elif out == "000":
    add_check(
        "api-admin-token",
        "Admin/API",
        "Admin endpoints require token",
        "skip",
        "high",
        "API not reachable.",
    )
else:
    add_check(
        "api-admin-token",
        "Admin/API",
        "Admin endpoints require token",
        "warn",
        "high",
        f"Got status {out} from /admin/clients.",
        "Investigate auth middleware or route protection for admin endpoints.",
        meta={"classification": "needs_review", "endpoint": "/admin/clients"},
    )

code, out, err = run_cmd('grep -rIE "POSTGRES_PASSWORD|REDIS_URL" logs/ 2>/dev/null')
if code == 0 and out.strip():
    add_check(
        "log-env",
        "Logs/artifacts",
        "Logs do not contain secrets",
        "fail",
        "high",
        "Found env variables in logs.",
        "Review logging configuration.",
        out[:1000],
    )
else:
    add_check(
        "log-env",
        "Logs/artifacts",
        "Logs do not contain secrets",
        "pass",
        "high",
        "No env variables found in logs.",
    )

add_check("rag-git", "RAG/TTS data", "RAG uploads outside git", "pass", "medium", "Checked by git hygiene.")

code, out, err = run_cmd('grep -A1 "ports:" docker-compose.yml | grep -E "5432|6379" | grep -v "127.0.0.1"')
if code == 0 and out.strip() and not out.strip().startswith("#"):
    add_check(
        "docker-expose",
        "Docker",
        "Docker-compose does not expose DB ports globally",
        "warn",
        "high",
        "DB ports might be exposed to 0.0.0.0.",
        "Bind to 127.0.0.1 in docker-compose.yml",
        out[:1000],
    )
else:
    add_check(
        "docker-expose",
        "Docker",
        "Docker-compose does not expose DB ports globally",
        "pass",
        "high",
        "DB ports not globally exposed.",
    )

code, out, err = run_cmd('grep -r "privileged: true" docker-compose.yml 2>/dev/null')
if code == 0 and out.strip():
    add_check(
        "docker-privileged",
        "Docker",
        "Containers do not use privileged mode",
        "fail",
        "high",
        "Found privileged: true.",
        "Remove privileged mode.",
        out[:1000],
    )
else:
    add_check(
        "docker-privileged",
        "Docker",
        "Containers do not use privileged mode",
        "pass",
        "high",
        "No privileged containers.",
    )

critical_fails = sum(1 for check in checks if check["status"] == "fail" and check["severity"] == "critical")
high_fails = sum(1 for check in checks if check["status"] == "fail" and check["severity"] == "high")
fails = sum(1 for check in checks if check["status"] == "fail")
warns = sum(1 for check in checks if check["status"] == "warn")
passes = sum(1 for check in checks if check["status"] == "pass")
skips = sum(1 for check in checks if check["status"] == "skip")

if critical_fails > 0:
    score = "FAIL"
elif STRICT and high_fails > 0:
    score = "FAIL"
elif fails > 0:
    score = "PASS_WITH_WARNINGS"
elif warns > 0:
    score = "PASS_WITH_WARNINGS"
else:
    score = "PASS"

_, branch, _ = run_cmd("git rev-parse --abbrev-ref HEAD")
_, commit, _ = run_cmd("git rev-parse HEAD")

report_data = {
    "generated_at": datetime.datetime.now().isoformat(),
    "version": "1.0",
    "git_branch": branch.strip(),
    "git_commit": commit.strip(),
    "score": score,
    "totals": {
        "pass": passes,
        "warn": warns,
        "fail": fails,
        "skip": skips,
        "critical_failures": critical_fails,
    },
    "checks": checks,
    "artifacts": {
        "report_json": str(report_dir / "security-report.json"),
        "report_md": str(report_dir / "security-report.md"),
    },
}

with open(report_dir / "security-report.json", "w") as fh:
    json.dump(report_data, fh, indent=2)

md_lines = [
    "# Security Report",
    f"**Date:** {report_data['generated_at']}",
    f"**Score:** {score}",
    f"**Branch:** {report_data['git_branch']} ({report_data['git_commit']})",
    "",
    "## Totals",
    f"- Pass: {passes}",
    f"- Warn: {warns}",
    f"- Fail: {fails}",
    f"- Skip: {skips}",
    f"- Critical Fails: {critical_fails}",
    "",
    "## Checks",
    "| ID | Category | Title | Status | Severity | Details |",
    "|---|---|---|---|---|---|",
]
for check in checks:
    md_lines.append(
        f"| {check['id']} | {check['category']} | {check['title']} | {check['status']} | {check['severity']} | {check['details']} |"
    )

with open(report_dir / "security-report.md", "w") as fh:
    fh.write("\n".join(md_lines))

print(f"Security Report Generated: {score}")
if critical_fails > 0 or fails > 0 or warns > 0:
    print("Top warnings/fails:")
    for check in checks:
        if check["status"] in {"fail", "warn"}:
            print(f" - [{check['status'].upper()}] {check['title']}: {check['details']}")
print(f"JSON Output: {report_dir / 'security-report.json'}")
print(f"MD Output: {report_dir / 'security-report.md'}")

if score == "FAIL":
    sys.exit(1)
EOF
