#!/bin/bash
set -euo pipefail

OUTPUT_DIR="artifacts/security-artifact-diagnosis"
TIMESTAMP=""

usage() {
    echo "Usage: $0 [--output-dir DIR] [--timestamp YYYYMMDDTHHMMSS] [--help]"
}

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --output-dir)
            OUTPUT_DIR="$2"
            shift
            ;;
        --timestamp)
            TIMESTAMP="$2"
            shift
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown parameter: $1"
            usage
            exit 1
            ;;
    esac
    shift
done

export OUTPUT_DIR TIMESTAMP

PYTHON_BIN="python3"
if [ -f ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
fi

exec "$PYTHON_BIN" - <<'PY'
import datetime as dt
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path.cwd()
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "artifacts/security-artifact-diagnosis"))
TIMESTAMP = os.environ.get("TIMESTAMP") or dt.datetime.now().strftime("%Y%m%dT%H%M%S")
REPORT_DIR = OUTPUT_DIR / TIMESTAMP
JSON_PATH = REPORT_DIR / "diagnosis.json"
MD_PATH = REPORT_DIR / "diagnosis.md"
CHECK_SECRETS_PATH = ROOT / "scripts" / "check-secrets.sh"
SECURITY_REPORTS_DIR = ROOT / "artifacts" / "security-reports"

SKIP_EXTENSIONS = {
    ".gguf",
    ".bin",
    ".sqlite",
    ".db",
    ".bak",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
}


def run_git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def extract_bash_array(script_text: str, name: str) -> list[str]:
    pattern = re.compile(rf"{re.escape(name)}=\(\n(.*?)\n\)", re.S)
    match = pattern.search(script_text)
    if not match:
        raise SystemExit(f"Unable to parse {name} from {CHECK_SECRETS_PATH}")
    values = []
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if not stripped or not stripped.startswith('"'):
            continue
        values.append(stripped.strip('"'))
    return values


def mask_value(value: str) -> str:
    if len(value) <= 8:
        return "********"
    return f"{value[:4]}****{value[-4:]}"


def is_text_scan_skipped(path: Path) -> bool:
    suffixes = path.suffixes
    if not suffixes:
        return False
    joined = "".join(suffixes[-2:]) if len(suffixes) >= 2 else suffixes[-1]
    if joined in {".tar.gz"}:
        return True
    return suffixes[-1] in SKIP_EXTENSIONS


def classify_origin(rel_path: str) -> str:
    normalized = rel_path.replace("\\", "/")
    name = Path(normalized).name
    if normalized.startswith("releases/"):
        if name in {"summary.json", "summary.md"}:
            return "release_summary"
        if name == "release-manifest.json":
            return "release_manifest"
        if name in {"bundle-manifest.json", "bundle-checksums.sha256"}:
            return "bundle_manifest"
        if "demo" in normalized:
            return "demo_artifact"
        return "obsolete_artifact"
    if normalized.startswith("artifacts/security-reports/"):
        return "security_report_artifact"
    if "local-demo" in normalized or "/demo" in normalized:
        return "demo_artifact"
    if "validate" in normalized or "validation" in normalized:
        return "validation_artifact"
    if "pytest" in normalized or "test-" in name or "test_" in name or "/test" in normalized:
        return "test_artifact"
    return "unknown"


def recommended_action(origin: str, tracked: bool, ignored: bool) -> str:
    if tracked:
        if origin in {"release_summary", "release_manifest", "bundle_manifest"}:
            return "redact_source"
        if origin in {
            "validation_artifact",
            "security_report_artifact",
            "demo_artifact",
            "test_artifact",
            "obsolete_artifact",
        }:
            return "redact_generated_file"
        return "needs_review"
    if ignored:
        if origin in {
            "validation_artifact",
            "security_report_artifact",
            "demo_artifact",
            "test_artifact",
            "obsolete_artifact",
            "unknown",
        }:
            return "remove_untracked_artifact"
        return "keep_with_masking"
    return "add_to_gitignore"


def latest_security_report() -> dict:
    if not SECURITY_REPORTS_DIR.exists():
        return {}
    candidates = sorted([p for p in SECURITY_REPORTS_DIR.iterdir() if p.is_dir()])
    if not candidates:
        return {}
    latest = candidates[-1]
    json_path = latest / "security-report.json"
    if not json_path.exists():
        return {"timestamp": latest.name}
    data = json.loads(json_path.read_text())
    return {
        "timestamp": latest.name,
        "score": data.get("score"),
        "report_json": str(json_path.relative_to(ROOT)),
        "report_md": str((latest / "security-report.md").relative_to(ROOT)),
    }


script_text = CHECK_SECRETS_PATH.read_text()
secret_patterns = extract_bash_array(script_text, "SECRET_REGEXES")
safe_patterns = extract_bash_array(script_text, "SAFE_PATTERNS")

compiled_patterns = [
    ("openai_key", re.compile(secret_patterns[0])),
    ("admin_token_assignment", re.compile(secret_patterns[1])),
    ("jwt_secret_assignment", re.compile(secret_patterns[2])),
    ("github_token", re.compile(secret_patterns[3])),
    ("bearer_token", re.compile(secret_patterns[4])),
    ("private_key_block", re.compile(secret_patterns[5])),
    ("basic_auth_url", re.compile(secret_patterns[6])),
]
compiled_safe_patterns = [re.compile(pattern) for pattern in safe_patterns]

REPORT_DIR.mkdir(parents=True, exist_ok=True)

findings = []
findings_by_file: dict[str, list[dict]] = defaultdict(list)

scan_roots = [ROOT / "artifacts", ROOT / "releases"]
for root in scan_roots:
    if not root.exists():
        continue
    for file_path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel_path = str(file_path.relative_to(ROOT))
        origin = classify_origin(rel_path)
        tracked = run_git("ls-files", "--error-unmatch", rel_path).returncode == 0
        ignored = run_git("check-ignore", "-q", rel_path).returncode == 0
        action = recommended_action(origin, tracked, ignored)

        extension_finding = None
        if file_path.suffix in {".pem", ".key"}:
            extension_finding = {
                "finding_type": "private_key_file_extension",
                "line": None,
                "masked_value": None,
            }
        elif file_path.name in {".env", ".env.local"} or file_path.suffix == ".env":
            extension_finding = {
                "finding_type": "environment_file",
                "line": None,
                "masked_value": None,
            }

        if extension_finding:
            record = {
                "file": rel_path,
                "origin": origin,
                "tracked": tracked,
                "ignored": ignored,
                "recommended_action": action,
                **extension_finding,
            }
            findings.append(record)
            findings_by_file[rel_path].append(record)

        if is_text_scan_skipped(file_path):
            continue

        content = file_path.read_text(encoding="utf-8", errors="ignore")
        for line_number, line in enumerate(content.splitlines(), start=1):
            for finding_type, pattern in compiled_patterns:
                for match in pattern.finditer(line):
                    matched_value = match.group(0)
                    if any(safe.search(matched_value) for safe in compiled_safe_patterns):
                        continue
                    record = {
                        "file": rel_path,
                        "origin": origin,
                        "tracked": tracked,
                        "ignored": ignored,
                        "recommended_action": action,
                        "finding_type": finding_type,
                        "line": line_number,
                        "masked_value": mask_value(matched_value),
                    }
                    findings.append(record)
                    findings_by_file[rel_path].append(record)

summary_by_origin = Counter(f["origin"] for f in findings)
summary_by_action = Counter(f["recommended_action"] for f in findings)
summary_tracked = {
    "tracked": sum(1 for f in findings if f["tracked"]),
    "untracked": sum(1 for f in findings if not f["tracked"]),
}

files = []
for rel_path, file_findings in sorted(findings_by_file.items()):
    files.append(
        {
            "file": rel_path,
            "origin": file_findings[0]["origin"],
            "tracked": file_findings[0]["tracked"],
            "ignored": file_findings[0]["ignored"],
            "recommended_action": file_findings[0]["recommended_action"],
            "finding_count": len(file_findings),
            "finding_types": sorted({f["finding_type"] for f in file_findings}),
            "masked_values": sorted({f["masked_value"] for f in file_findings if f["masked_value"]}),
            "lines": [f["line"] for f in file_findings if f["line"] is not None],
        }
    )

diagnosis = {
    "generated_at": dt.datetime.now().isoformat(),
    "status": "open",
    "scan_scope": ["artifacts/", "releases/"],
    "source_rules": {
        "check_secrets_script": str(CHECK_SECRETS_PATH.relative_to(ROOT)),
        "secret_patterns_count": len(secret_patterns),
        "safe_patterns_count": len(safe_patterns),
    },
    "latest_security_report": latest_security_report(),
    "summary": {
        "findings": len(findings),
        "files": len(files),
        "by_origin": dict(summary_by_origin),
        "by_recommended_action": dict(summary_by_action),
        "tracked_entries": summary_tracked["tracked"],
        "untracked_entries": summary_tracked["untracked"],
    },
    "files": files,
    "findings": findings,
}

JSON_PATH.write_text(json.dumps(diagnosis, indent=2) + "\n")

lines = [
    "# Artifact Secrets Diagnosis",
    f"- Status: {diagnosis['status']}",
    f"- Generated at: {diagnosis['generated_at']}",
    f"- Scope: {', '.join(diagnosis['scan_scope'])}",
]
latest = diagnosis.get("latest_security_report") or {}
if latest:
    lines.append(
        f"- Latest security report: {latest.get('score', 'unknown')} ({latest.get('timestamp', 'unknown')})"
    )
    if latest.get("report_json"):
        lines.append(f"- Report JSON: {latest['report_json']}")
    if latest.get("report_md"):
        lines.append(f"- Report MD: {latest['report_md']}")

lines.extend(
    [
        "",
        "## Summary",
        f"- Findings: {diagnosis['summary']['findings']}",
        f"- Files: {diagnosis['summary']['files']}",
        f"- Tracked entries: {diagnosis['summary']['tracked_entries']}",
        f"- Untracked entries: {diagnosis['summary']['untracked_entries']}",
        "",
        "## Findings By Origin",
    ]
)
for origin, count in sorted(summary_by_origin.items()):
    lines.append(f"- {origin}: {count}")

lines.extend(["", "## Files"])
if not files:
    lines.append("- No findings detected.")
else:
    for item in files:
        masked = ", ".join(item["masked_values"]) if item["masked_values"] else "n/a"
        types = ", ".join(item["finding_types"])
        line_info = ",".join(str(n) for n in item["lines"]) if item["lines"] else "n/a"
        lines.append(
            "- "
            f"{item['file']} | origin={item['origin']} | tracked={str(item['tracked']).lower()} "
            f"| ignored={str(item['ignored']).lower()} | action={item['recommended_action']} "
            f"| findings={item['finding_count']} | types={types} | lines={line_info} | masked={masked}"
        )

lines.extend(["", "## Recommended Actions"])
for action, count in sorted(summary_by_action.items()):
    lines.append(f"- {action}: {count}")

MD_PATH.write_text("\n".join(lines) + "\n")

print(f"Diagnosis findings: {diagnosis['summary']['findings']}")
print(f"Diagnosis files: {diagnosis['summary']['files']}")
print(f"JSON Output: {JSON_PATH}")
print(f"MD Output: {MD_PATH}")
for item in files:
    print(
        f"{item['file']} | tracked={str(item['tracked']).lower()} | "
        f"ignored={str(item['ignored']).lower()} | action={item['recommended_action']} | "
        f"types={','.join(item['finding_types'])}"
    )
PY
