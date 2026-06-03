#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Load operator errors library if available
if [[ -f "${SCRIPT_DIR}/lib/operator-errors.sh" ]]; then
  source "${SCRIPT_DIR}/lib/operator-errors.sh"
fi

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
import yaml

BASE_URL = os.environ.get("BASE_URL", "http://localhost:18080")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "artifacts/security-reports")
STRICT = os.environ.get("STRICT") == "true"
SKIP_ARTIFACTS = os.environ.get("SKIP_ARTIFACTS") == "true"

ALLOWLIST_PATH = Path("config/security-warning-allowlist.yaml")
allowlist = []
if ALLOWLIST_PATH.exists():
    try:
        with open(ALLOWLIST_PATH) as f:
            data = yaml.safe_load(f) or {}
            allowlist = data.get("allowlist", []) or []
    except Exception as e:
        print(f"Error loading allowlist: {e}", file=sys.stderr)

def check_allowlist(file_path: str, is_versioned: bool):
    if not file_path:
        return False, ""
    norm_file_path = str(Path(file_path)).replace("\\", "/")
    for entry in allowlist:
        entry_path = str(Path(entry.get("file_path", ""))).replace("\\", "/")
        if entry_path and (norm_file_path == entry_path or norm_file_path.endswith("/" + entry_path)):
            justification = entry.get("justification")
            owner = entry.get("owner")
            exp_date_str = entry.get("expiration_review_date")
            
            if not justification or not owner or not exp_date_str:
                print(f"Allowlist entry invalid (missing fields) for: {file_path}", file=sys.stderr)
                continue
            
            try:
                if isinstance(exp_date_str, datetime.date):
                    exp_date = datetime.datetime.combine(exp_date_str, datetime.time.min)
                else:
                    exp_date = datetime.datetime.strptime(str(exp_date_str), "%Y-%m-%d")
                if exp_date < datetime.datetime.now():
                    print(f"Allowlist entry expired ({exp_date_str}) for: {file_path}", file=sys.stderr)
                    continue
            except Exception as e:
                print(f"Allowlist entry date parsing error for {file_path}: {e}", file=sys.stderr)
                continue
            
            if is_versioned:
                print(f"Allowlist rule violation: file is tracked/staged in git, cannot be allowlisted: {file_path}", file=sys.stderr)
                continue
            
            return True, f"Allowlisted by {owner} until {exp_date_str} (Reason: {justification})"
    return False, ""

CLASSIFICATIONS = [
    "real_secret_suspected",
    "fixture_expected",
    "generated_artifact",
    "obsolete_release_file",
    "needs_review",
    "redacted_safe",
]

# (status, severity, contributes_to_score)
STATUS_MAPPING = {
    "real_secret_suspected": ("fail", "critical", True),
    "fixture_expected": ("skip", "low", False),
    "generated_artifact": ("warn", "high", True),
    "obsolete_release_file": ("warn", "high", True),
    "needs_review": ("warn", "medium", True),
    "redacted_safe": ("pass", "low", False),
}

timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
report_dir = Path(OUTPUT_DIR) / timestamp
report_dir.mkdir(parents=True, exist_ok=True)
(report_dir / "logs").mkdir(parents=True, exist_ok=True)

checks = []


def run_cmd(cmd: str):
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        return res.returncode, res.stdout, res.stderr
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        message = f"Command timed out after 15s: {cmd}"
        if stderr:
            message = f"{message}\n{stderr}"
        return 124, stdout, message
    except Exception as exc:
        return -1, "", str(exc)


def add_check(check_id, category, title, status, severity, details, remediation="", evidence="", meta=None):
    # Default contributes_to_score based on status if not explicitly in meta
    contributes = True
    if status in {"pass", "skip"}:
        contributes = False
    
    m = meta or {}
    if "contributes_to_score" not in m:
        m["contributes_to_score"] = contributes

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
            "meta": m,
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


def get_file_git_info(file_path: str):
    _, tracked, _ = run_cmd(f'git ls-files "{file_path}"')
    _, ignored, _ = run_cmd(f'git check-ignore "{file_path}"')
    _, staged, _ = run_cmd(f'git diff --cached --name-only "{file_path}"')
    return {
        "tracked": bool(tracked.strip()),
        "ignored": bool(ignored.strip()),
        "staged": bool(staged.strip()),
    }


def add_secret_scan_results(check_id_prefix: str, title_context: str, output: str, scope_hint: str):
    grouped = parse_classified_output(output)
    total_findings = sum(len(lines) for lines in grouped.values())

    # Determine worst status for the summary check
    worst_status = "pass"
    worst_severity = "low"
    
    # We'll re-evaluate summary status based on findings
    summary_contributes = False

    summary_details = (
        "No secret findings."
        if total_findings == 0
        else f"Classified {total_findings} finding(s) for {title_context}."
    )
    
    # Initial summary check, will be updated if findings exist
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

        status, severity, contributes = STATUS_MAPPING[classification]
        
        # Override severity based on scope and git info
        for line in lines:
            # Try to extract file path from line "[classification] Label Path -> Masked"
            parts = line.split(" ")
            file_path = ""
            for p in parts:
                if "/" in p or "." in p:
                    file_path = p.split(":")[0]
                    break
            
            git_info = {}
            if file_path and os.path.exists(file_path):
                git_info = get_file_git_info(file_path)
            
            # Policy overrides
            current_status = status
            current_severity = severity
            current_contributes = contributes
            
            if git_info.get("tracked") or git_info.get("staged"):
                if classification in ["generated_artifact", "obsolete_release_file"]:
                    current_status = "warn"
                    current_severity = "high"
                    current_contributes = True
            elif git_info.get("ignored"):
                if classification in ["generated_artifact", "obsolete_release_file"]:
                    # Ignored artifacts are just warnings or info if old
                    current_status = "warn"
                    current_severity = "medium"
                    current_contributes = True
            
            # If redacted marker found, it's safe
            # intentional_redacted = ["***REDACTED***", "***masked***", "sk-***masked***", "Bearer ***masked***", "ADMIN_TOKEN=***masked***"]
            # We check for these specifically. Just checking for "***" is too broad as it matches "****" from masking.
            is_intentional_redaction = any(m in line for m in ["***REDACTED***", "***masked***", "sk-***masked***", "Bearer ***masked***", "ADMIN_TOKEN=***masked***"])
            
            if is_intentional_redaction:
                current_status = "pass"
                current_severity = "low"
                current_contributes = False

            # Allowlist check
            is_versioned = bool(git_info.get("tracked") or git_info.get("staged"))
            is_allowlisted, allowlist_reason = check_allowlist(file_path, is_versioned)
            if is_allowlisted:
                current_status = "skip"
                current_severity = "low"
                current_contributes = False

            details = {
                "real_secret_suspected": f"Found suspected real secrets in {title_context}.",
                "fixture_expected": f"Found authorized fake fixtures in {title_context}.",
                "generated_artifact": f"Found secrets in generated artifacts for {title_context}.",
                "obsolete_release_file": f"Found secrets in release files for {title_context}.",
                "needs_review": f"Found items needing manual review in {title_context}.",
                "redacted_safe": f"Found redacted markers in {title_context}.",
            }.get(classification, f"Findings for {classification}")

            if is_allowlisted:
                details = f"[Allowlisted] {details} ({allowlist_reason})"

            remediation = {
                "real_secret_suspected": "Remove the secret or replace it with runtime-generated test data.",
                "fixture_expected": "No action required if the fixture policy still applies.",
                "generated_artifact": "Purge or redact generated artifacts that contain secrets.",
                "obsolete_release_file": "Clean up or regenerate release files without embedded secrets.",
                "needs_review": "Review the finding manually and tighten the classifier if appropriate.",
                "redacted_safe": "No action required.",
            }.get(classification, "")

            finding_id = f"{check_id_prefix}-{classification}"
            if len(lines) > 1:
                finding_id = f"{finding_id}-{lines.index(line)}"

            add_check(
                finding_id,
                "Secrets",
                f"{classification} ({title_context})",
                current_status,
                current_severity,
                f"{details} (File: {file_path})",
                remediation,
                line[:1000],
                meta={
                    "scope": scope_hint, 
                    "classification": classification, 
                    "git": git_info,
                    "contributes_to_score": current_contributes
                },
            )
            
            # Update summary check if this finding is worse
            # This is a bit simplified, but helps show worst result in summary
            idx = next(i for i, c in enumerate(checks) if c["id"] == check_id_prefix)
            if current_status == "fail":
                checks[idx]["status"] = "fail"
                checks[idx]["severity"] = "critical" if current_severity == "critical" else "high"
            elif current_status == "warn" and checks[idx]["status"] != "fail":
                checks[idx]["status"] = "warn"
                checks[idx]["severity"] = "high"


# Scans by category
# 1. Versionable files (tracked) - also mapped to sec-secrets-all for compatibility
code, out, err = run_cmd("./scripts/check-secrets.sh --all --verbose")
add_secret_scan_results("sec-secrets-versionable", "versionable files", out, "versionable_files")
add_secret_scan_results("sec-secrets-all", "all files (legacy)", out, "repository")

# 2. Staged files
code, out, err = run_cmd("./scripts/check-secrets.sh --staged --verbose")
add_secret_scan_results("sec-secrets-staged", "staged files", out, "staged_files")

# 3. Releases (versioned)
_, out_rel_t, _ = run_cmd("git ls-files releases/ | xargs ./scripts/check-secrets.sh --verbose --path")
add_secret_scan_results("sec-secrets-releases-versioned", "versioned releases", out_rel_t, "releases_versioned")

# 4. Releases (untracked)
_, out_rel_u, _ = run_cmd("git ls-files -o releases/ | xargs ./scripts/check-secrets.sh --verbose --path")
add_secret_scan_results("sec-secrets-releases-untracked", "untracked releases", out_rel_u, "releases_untracked")

if not SKIP_ARTIFACTS:
    # 5. Artifacts (ignored)
    _, out_art_i, _ = run_cmd("git ls-files -o -i --exclude-standard artifacts/ | xargs ./scripts/check-secrets.sh --verbose --path")
    add_secret_scan_results("sec-secrets-artifacts-ignored", "ignored artifacts", out_art_i, "artifacts_ignored")
    
    # 6. Artifacts (recent - last 24h)
    _, out_art_r, _ = run_cmd("find artifacts/ -type f -mmin -1440 | xargs ./scripts/check-secrets.sh --verbose --path")
    add_secret_scan_results("sec-secrets-artifacts-recent", "recent artifacts", out_art_r, "artifacts_recent")
    
    # Legacy artifacts scan for compatibility (includes all releases and artifacts)
    add_secret_scan_results("sec-secrets-artifacts", "artifacts/releases (legacy)", "\n".join([out_art_i, out_art_r, out_rel_u, out_rel_t]), "artifacts_and_releases")
else:
    for cat in ["artifacts-ignored", "artifacts-recent"]:
        add_check(
            f"sec-secrets-{cat}",
            "Secrets",
            f"Secrets scan ({cat.replace('-', ' ')})",
            "skip",
            "low",
            "Artifacts scan skipped by user.",
            meta={"scope": cat.replace("-", "_"), "skipped": True, "contributes_to_score": False},
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

code,out,err = run_cmd(
    'find . -type f \\( -name "*.pem" -o -name "*.key" \\) '
    '-not -path "./.venv/*" '
    '-not -path "./venv/*" '
    '-not -path "./.git/*" '
    '-not -path "./.cache/*" '
    '-not -path "./.tmp-llm-harness-cli-*" '
    '-not -path "./data/pki/*" '
    '-not -path "./control_plane/data/pki/*" | sort'
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
        
        git_info = get_file_git_info(file_path)
        is_versioned = bool(git_info.get("tracked") or git_info.get("staged"))
        is_allowlisted, allowlist_reason = check_allowlist(normalized, is_versioned)

        if (in_allowed_path and allowed_name and marker_ok and not blocked_area) or is_allowlisted:
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

code, out, err = run_cmd(f'curl -fsS --connect-timeout 3 --max-time 10 -o /dev/null -w "%{{http_code}}" {BASE_URL}/admin/clients')
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

critical_fails = sum(1 for check in checks if check["status"] == "fail" and check["severity"] == "critical" and check["meta"].get("contributes_to_score", True))
high_fails = sum(1 for check in checks if check["status"] == "fail" and check["severity"] == "high" and check["meta"].get("contributes_to_score", True))
fails = sum(1 for check in checks if check["status"] == "fail" and check["meta"].get("contributes_to_score", True))
warns = sum(1 for check in checks if check["status"] == "warn" and check["meta"].get("contributes_to_score", True))
passes = sum(1 for check in checks if check["status"] == "pass")
skips = sum(1 for check in checks if check["status"] == "skip")

if critical_fails > 0:
    score = "FAIL"
elif STRICT and (high_fails > 0 or fails > 0):
    score = "FAIL"
elif fails > 0 or warns > 0:
    score = "PASS_WITH_WARNINGS"
else:
    score = "PASS"

_, branch, _ = run_cmd("git rev-parse --abbrev-ref HEAD")
_, commit, _ = run_cmd("git rev-parse HEAD")

report_data = {
    "generated_at": datetime.datetime.now().isoformat(),
    "version": "1.1",
    "git_branch": branch.strip(),
    "git_commit": commit.strip(),
    "score": score,
    "totals": {
        "pass": passes,
        "warn": warns,
        "fail": fails,
        "skip": skips,
        "critical_failures": critical_fails,
        "high_failures": high_fails,
    },
    "checks": checks,
    "artifacts": {
        "report_json": str(report_dir / "security-report.json"),
        "report_md": str(report_dir / "security-report.md"),
    },
}

with open(report_dir / "security-report.json", "w") as fh:
    json.dump(report_data, fh, indent=2)

def get_table(checks_list):
    if not checks_list:
        return "_No findings in this category._\n"
    table = "| ID | Category | Title | Status | Severity | Details |\n"
    table += "|---|---|---|---|---|---|\n"
    for check in checks_list:
        table += f"| {check['id']} | {check['category']} | {check['title']} | {check['status']} | {check['severity']} | {check['details']} |\n"
    return table

blocking = [c for c in checks if c["status"] == "fail" and c["meta"].get("contributes_to_score", True)]
warnings = [c for c in checks if c["status"] == "warn" and c["meta"].get("contributes_to_score", True)]
informational = [c for c in checks if not c["meta"].get("contributes_to_score", True) and c["status"] != "pass"]
passed_checks = [c for c in checks if c["status"] == "pass"]

md_lines = [
    "# Security Report",
    f"**Date:** {report_data['generated_at']}",
    f"**Score:** {score}",
    f"**Branch:** {report_data['git_branch']} ({report_data['git_commit']})",
    "",
    "## Summary",
    f"- **Blocking Findings:** {len(blocking)}",
    f"- **Warnings:** {len(warnings)}",
    f"- **Informational/Redacted:** {len(informational)}",
    f"- **Passed Checks:** {len(passed_checks)}",
    "",
    "## Blocking Findings (Action Required)",
    get_table(blocking),
    "",
    "## Warnings",
    get_table(warnings),
    "",
    "## Informational & Redacted Artifacts",
    get_table(informational),
    "",
    "## All Passed Checks",
    get_table(passed_checks),
]

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

# Redact the report directory
echo "Redacting security report artifacts..."
./scripts/redact-local-sensitive-artifacts.sh --path "${OUTPUT_DIR}" --in-place

# Friendly output
if [[ $? -eq 0 ]]; then
    if python3 -c "import json, sys, glob; f = glob.glob('${OUTPUT_DIR}/*/security-report.json')[-1]; data = json.load(open(f)); sys.exit(0 if data['score'] == 'PASS' else 1)"; then
        operator_success "Relatório de segurança gerado com sucesso! Nenhum problema crítico encontrado."
    else
        operator_warning "SECURITY_FAILED" "O relatório de segurança identificou vulnerabilidades ou riscos." "Revise o relatório em ${OUTPUT_DIR} e corrija as falhas apontadas."
    fi
else
    operator_error "SECURITY_FAILED" "Falha ao gerar o relatório de segurança." "Verifique se todas as dependências estão instaladas e se o sistema está acessível."
fi

REPORT_MD=$(ls -t "${OUTPUT_DIR}"/*/security-report.md | head -n 1)
add_next_step "Revise o relatório completo em: ${REPORT_MD}"
add_next_step "Execute ./scripts/redact-local-sensitive-artifacts.sh se houver segredos expostos."
print_next_steps
