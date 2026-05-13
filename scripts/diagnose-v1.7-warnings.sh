#!/usr/bin/env bash
# diagnose-v1.7-warnings.sh
# Localiza relatórios v1.7, extrai warnings e classifica-os.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"
TIMESTAMP=$(date +%Y%m%dT%H%M%S)
OUTPUT_DIR="${ROOT_DIR}/artifacts/v1.7-warning-cleanup/${TIMESTAMP}"
mkdir -p "${OUTPUT_DIR}"

JSON_OUT="${OUTPUT_DIR}/warnings.json"
MD_OUT="${OUTPUT_DIR}/warnings.md"

log() { echo "[INFO] $1"; }

log "Iniciando diagnóstico de warnings v1.7..."

# Localizar relatórios mais recentes
LATEST_CHECKLIST=$(ls -dt "${ROOT_DIR}/artifacts/v1.7-release-checklist"/* 2>/dev/null | head -n 1 || echo "")
LATEST_FINAL_VAL=$(ls -dt "${ROOT_DIR}/artifacts/v1.7-final-validation"/* 2>/dev/null | head -n 1 || echo "")
LATEST_DEMO_E2E=$(ls -dt "${ROOT_DIR}/artifacts/final-qa/commercial-demo-e2e"/* 2>/dev/null | head -n 1 || echo "")
LATEST_CHECKLIST_STATUS=$(ls -dt "${ROOT_DIR}/artifacts/final-qa/v1.7-checklist"/* 2>/dev/null | head -n 1 || echo "")

python3 << EOF
import json, os, glob
from pathlib import Path

ROOT = Path("${ROOT_DIR}")
OUTPUT_DIR = Path("${OUTPUT_DIR}")

def find_warnings():
    warnings = []
    
    # 1. Checklist Status
    cs_dir = Path("${LATEST_CHECKLIST_STATUS}")
    if cs_dir.exists():
        cs_json = cs_dir / "checklist-status.json"
        if cs_json.exists():
            data = json.loads(cs_json.read_text())
            for item in data.get("items", []):
                if item.get("auto_status") in ("warn", "todo"):
                    warnings.append({
                        "source": "checklist-status",
                        "id": item["id"],
                        "item": item["item"],
                        "status": item["auto_status"],
                        "note": item.get("note", ""),
                        "classification": "needs_review"
                    })
            
            # Go/No-Go Criteria
            for k, v in data.get("go_criteria", {}).items():
                if v.get("result") == "PENDENTE":
                    warnings.append({
                        "source": "go-criteria",
                        "id": k,
                        "item": v["desc"],
                        "status": "PENDENTE",
                        "classification": "needs_review"
                    })

    # 2. Demo E2E
    demo_dir = Path("${LATEST_DEMO_E2E}")
    if demo_dir.exists():
        demo_json = demo_dir / "demo-e2e-report.json"
        if demo_json.exists():
            data = json.loads(demo_json.read_text())
            for res in data.get("results", []):
                if res.startswith("warn:"):
                    msg = res[5:]
                    warnings.append({
                        "source": "demo-e2e",
                        "item": msg,
                        "status": "warn",
                        "classification": "needs_review"
                    })

    # Classification logic
    for w in warnings:
        item = w.get("item", "").lower()
        note = w.get("note", "").lower()
        
        if "psp" in item or "pix" in item:
            w["classification"] = "accepted_non_blocking"
            w["remediation"] = "Manual billing is the current standard. PSP/PIX is future scope."
        elif "version" in item and "v1.7.0" in note:
            w["classification"] = "fixable"
            w["remediation"] = "Update checklist status script to accept v1.7.x pattern."
        elif "branch" in item:
            w["classification"] = "fixable"
            w["remediation"] = "Update checklist status script to accept feature/* branches post-release."
        elif "release manifest" in item:
            w["classification"] = "fixable"
            w["remediation"] = "Implement real check for release-manifest.json."
        elif "chat completions" in item and "405" in item:
            w["classification"] = "fixable"
            w["remediation"] = "Change curl method to POST in demo validation script."
        elif "responses" in item and "405" in item:
            w["classification"] = "fixable"
            w["remediation"] = "Change curl method to POST in demo validation script."
        elif "embeddings" in item and "405" in item:
            w["classification"] = "fixable"
            w["remediation"] = "Change curl method to POST in demo validation script."
        elif "rag" in item and "404" in item:
            w["classification"] = "environment_specific"
            w["remediation"] = "Verify if RAG service is enabled in the current environment."
        elif "tts" in item and "404" in item:
            w["classification"] = "optional_dependency"
            w["remediation"] = "TTS requires pocket-tts service. Mark as accepted if not present."
        elif "fake data" in item:
            w["classification"] = "fixable"
            w["remediation"] = "Ensure fake data seed is complete and consistent."
        elif "commercial demo pack" in item:
            w["classification"] = "fixable"
            w["remediation"] = "Ensure commercial demo pack seed is complete."

    return warnings

warnings = find_warnings()

# Write JSON
with open("${JSON_OUT}", "w") as f:
    json.dump({"warnings": warnings, "timestamp": "${TIMESTAMP}"}, f, indent=2)

# Write MD
with open("${MD_OUT}", "w") as f:
    f.write("# Diagnóstico de Warnings v1.7\n\n")
    f.write(f"**Timestamp:** ${TIMESTAMP}\n\n")
    f.write("| Fonte | Item | Status | Classificação | Remediação |\n")
    f.write("|-------|------|--------|---------------|------------|\n")
    for w in warnings:
        source = w.get("source", "")
        item = w.get("item", "")
        status = w.get("status", "")
        cls = w.get("classification", "")
        rem = w.get("remediation", "TBD")
        f.write(f"| {source} | {item} | {status} | {cls} | {rem} |\n")

EOF

log "Diagnóstico concluído: ${JSON_OUT}"
log "Relatório MD: ${MD_OUT}"
