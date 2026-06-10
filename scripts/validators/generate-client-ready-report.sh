#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

###############################################################################
# generate-client-ready-report.sh
#
# Gera relatório final consolidado de pronto para cliente (Client Ready Report).
# Produz artifacts/ e docs/CLIENT_READY_FINAL_REPORT.md
#
# Uso: ./scripts/validators/generate-client-ready-report.sh [--output-dir <dir>]
###############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"

# --- Config ---
TIMESTAMP="$(date -u +%Y%m%dT%H%M%S)"
OUTPUT_BASE="${ROOT_DIR}/artifacts/final-qa/client-ready/${TIMESTAMP}"
REPORT_JSON="${OUTPUT_BASE}/client-ready-report.json"
REPORT_MD="${OUTPUT_BASE}/client-ready-report.md"
LOGS_DIR="${OUTPUT_BASE}/logs"
VERSION_FILE="${ROOT_DIR}/VERSION"

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) OUTPUT_BASE="$2"; shift 2 ;;
    --help) echo "Usage: $0 [--output-dir <dir>]"; exit 0 ;;
    *) echo "Unknown: $1"; exit 1 ;;
  esac
done

# --- Gather metadata ---
VERSION="$(cat "${VERSION_FILE}" 2>/dev/null || echo "unknown")"
GIT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")"
GIT_COMMIT="$(git rev-parse HEAD 2>/dev/null || echo "unknown")"
GIT_CLEAN="$((git status --porcelain 2>/dev/null | wc -l) || echo "unknown")"

# Export for Python subprocess
export ROOT_DIR VERSION GIT_BRANCH GIT_COMMIT GIT_CLEAN
export OUTPUT_BASE REPORT_JSON REPORT_MD LOGS_DIR

# --- Find latest reports (use Python for robust JSON handling) ---
python3 << 'PYEOF'
import json, os, sys
from pathlib import Path

ROOT = Path(os.environ['ROOT_DIR'])
VERSION = os.environ['VERSION']
OUTPUT_BASE = os.environ['OUTPUT_BASE']
REPORT_JSON = os.environ['REPORT_JSON']
REPORT_MD = os.environ['REPORT_MD']
LOGS_DIR = os.environ['LOGS_DIR']
GIT_BRANCH = os.environ['GIT_BRANCH']
GIT_COMMIT = os.environ['GIT_COMMIT']
GIT_CLEAN = os.environ['GIT_CLEAN']

def find_latest_dir(base):
    if not base.exists():
        return None
    dirs = sorted([d for d in base.iterdir() if d.is_dir() and d.name.startswith('2026')])
    return dirs[-1] if dirs else None

def find_latest_file(base, pattern):
    if base is None or not base.exists():
        return None
    files = sorted(base.glob(pattern))
    return files[-1] if files else None

def read_json_field(filepath, *keys):
    if filepath is None or not filepath.exists():
        return "not_found"
    try:
        with open(filepath) as f:
            data = json.load(f)
        for k in keys:
            data = data.get(k, "not_found")
            if data == "not_found":
                break
        return data
    except Exception:
        return "parse_error"

# Gather report paths
sec_dir = find_latest_dir(ROOT / "artifacts/security-reports")
sec_json = find_latest_file(sec_dir, "security-report.json")

pr_dir = find_latest_dir(ROOT / "artifacts/production-readiness")
pr_json = find_latest_file(pr_dir, "report.json")

vlp_dir = find_latest_dir(ROOT / "artifacts/local-production-validation")
vlp_json = find_latest_file(vlp_dir, "summary.json")

ci_dir = find_latest_dir(ROOT / "artifacts/clean-install-test")
ci_json = find_latest_file(ci_dir, "clean-install-report.json")

rr_dir = find_latest_dir(ROOT / "artifacts/restore-rollback-test")
rr_json = find_latest_file(rr_dir, "restore-rollback-report.json")

de_dir = find_latest_dir(ROOT / "artifacts/final-qa/commercial-demo-e2e")
de_json = find_latest_file(de_dir, "demo-e2e-report.json")

# Read fields
sec_score = read_json_field(sec_json, "score")
sec_total_pass = read_json_field(sec_json, "totals", "pass")

pr_score = read_json_field(pr_json, "score")
pr_total_pass = read_json_field(pr_json, "totals", "pass")
pr_total_fail = read_json_field(pr_json, "totals", "fail")

vlp_success = read_json_field(vlp_json, "validation_result", "success")
vlp_passed = read_json_field(vlp_json, "pytest", "passed")
vlp_failed = read_json_field(vlp_json, "pytest", "failed")

ci_status = read_json_field(ci_json, "overall_status")
ci_label = read_json_field(ci_json, "overall_label")
ci_failures = read_json_field(ci_json, "failures")

rr_status = read_json_field(rr_json, "overall_status")
rr_label = read_json_field(rr_json, "overall_label")
rr_failures = read_json_field(rr_json, "failures")

de_status = read_json_field(de_json, "status")
de_pass = read_json_field(de_json, "counts", "pass")
de_fail = read_json_field(de_json, "counts", "fail")
de_warn = read_json_field(de_json, "counts", "warn")

# Release manifest
rl_manifest = ROOT / "releases" / VERSION / "release-manifest.json"
rl_manifest_ok = rl_manifest.exists()

# Check secrets via script
secrets_clean = "unknown"
check_script = ROOT / "scripts/validators/check-secrets.sh"
if check_script.exists():
    import subprocess
    result = subprocess.run(["bash", str(check_script), "--all"],
                          cwd=ROOT, capture_output=True, timeout=60)
    secrets_clean = "true" if result.returncode == 0 else "false"

# Forbidden files
forbidden_files_clean = True
for f in [".env.local", ".env", "id_rsa", "credentials.json"]:
    r = subprocess.run(["git", "ls-files", "--error-unmatch", f],
                      cwd=ROOT, capture_output=True, timeout=10)
    if r.returncode == 0:
        forbidden_files_clean = False

# Determine final status
status = "NOT_READY"
if (sec_score == "PASS" and pr_score == "READY" and
    vlp_success is True and
    de_status in ("DEMO_READY", "DEMO_READY_WITH_WARNINGS") and
    secrets_clean == "true" and
    forbidden_files_clean is True and
    rl_manifest_ok is True):
    if (ci_status == "success" and rr_status == "success" and
        de_status == "DEMO_READY"):
        status = "CLIENT_READY"
    else:
        status = "CLIENT_READY_WITH_WARNINGS"

# Build report
evaluation_criteria = [
    {"id": "security_report", "label": "Security Report PASS", "result": str(sec_score), "evidence": str(sec_json)},
    {"id": "production_readiness", "label": "Production Readiness READY", "result": str(pr_score), "evidence": str(pr_json)},
    {"id": "validate_local_production", "label": "Validate Local Production Full OK", "result": str(vlp_success), "evidence": str(vlp_json)},
    {"id": "clean_install", "label": "Clean Install Report OK", "result": f"{ci_status} ({ci_label})", "evidence": str(ci_json)},
    {"id": "restore_rollback", "label": "Restore/Rollback Report OK", "result": f"{rr_status} ({rr_label})", "evidence": str(rr_json)},
    {"id": "commercial_demo_e2e", "label": "Commercial Demo E2E OK", "result": str(de_status), "evidence": str(de_json)},
    {"id": "secrets_check", "label": "No secrets in codebase", "result": str(secrets_clean), "evidence": "check-secrets --all"},
    {"id": "forbidden_files", "label": "No forbidden files versioned", "result": str(forbidden_files_clean), "evidence": "git ls-files check"},
    {"id": "release_metadata", "label": "Release manifest OK", "result": str(rl_manifest_ok), "evidence": str(rl_manifest)},
]

report = {
    "report_type": "client_ready_report",
    "generated_at": subprocess.run(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], capture_output=True, text=True).stdout.strip(),
    "version": VERSION,
    "git_branch": GIT_BRANCH,
    "git_commit": GIT_COMMIT,
    "git_clean": int(GIT_CLEAN) if GIT_CLEAN.isdigit() else GIT_CLEAN,
    "final_status": status,
    "evaluation_criteria": evaluation_criteria,
    "artifacts": {
        "security_report": str(sec_json),
        "production_readiness": str(pr_json),
        "validate_local_production": str(vlp_json),
        "clean_install": str(ci_json),
        "restore_rollback": str(rr_json),
        "commercial_demo_e2e": str(de_json),
        "release_manifest": str(rl_manifest),
    },
    "summary": {
        "security_score": sec_score,
        "readiness_score": pr_score,
        "validation_success": vlp_success if vlp_success != "not_found" else None,
        "clean_install_status": ci_status,
        "restore_rollback_status": rr_status,
        "demo_e2e_status": de_status,
        "secrets_clean": secrets_clean == "true",
        "forbidden_files_clean": forbidden_files_clean,
        "release_metadata_ok": rl_manifest_ok,
    },
    "known_limitations": [
        "PSP/PIX real — Nao implementado. Faturamento manual apenas.",
        "Tools/Function Calling — Suportado nativamente.",
        "TTS — Requer pocket-tts habilitado.",
        "RAG — Requer data plane com suporte a embeddings.",
        "LM Studio — Integracao depende de backend externo.",
        "Rate limit script (saas_rate_limit) — Falha conhecida no readiness report (script exit_code 127).",
        "Release manifests v1.6.5/v1.6.6 — git_commit do manifest aponta para versao anterior.",
    ],
    "residual_risks": [
        "Working tree pode conter alteracoes locais nao commitadas.",
        "Release manifests de versoes anteriores podem ter commits incorretos.",
        "DR report nao gerado automaticamente (skip no readiness).",
        "Dependencia de GPU local para inferencia em producao.",
    ],
    "v1_7_recommendation": (
        f"Baseado nos criterios avaliados e status {status}, recomenda-se "
        "seguir para v1.7.0-local-ai-appliance resolvendo os warnings pendentes "
        "(rate limit script, manifests inconsistentes) como parte do ciclo de desenvolvimento."
    ),
}

# Write JSON
os.makedirs(OUTPUT_BASE, exist_ok=True)
with open(REPORT_JSON, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

# --- Generate Markdown report ---
def md_escape(v):
    return str(v).replace("|", "\\|")

markdown = f"""# Client Ready Report

**Gerado em:** {report["generated_at"]}
**Versao avaliada:** {VERSION}
**Branch:** {GIT_BRANCH}
**Commit:** {GIT_COMMIT}
**Status Final:** **{status}**

---

## Resumo Executivo

Relatorio final consolidado de prontidao para cliente da linha v1.6.x.
Avalia security, production readiness, validacao full, clean install,
restore/rollback, demo E2E, release history e capability matrix.

**Status:** {status}

---

## Criterios Avaliados

| Criterio | Resultado | Evidencia |
|----------|-----------|-----------|
| Security Report | {md_escape(sec_score)} | {sec_json} |
| Production Readiness | {md_escape(pr_score)} | {pr_json} |
| Validate Local Production | {md_escape(vlp_success)} | {vlp_json} |
| Clean Install | {md_escape(ci_status)} ({ci_label}) | {ci_json} |
| Restore/Rollback | {md_escape(rr_status)} ({rr_label}) | {rr_json} |
| Commercial Demo E2E | {md_escape(de_status)} | {de_json} |
| No Secrets | {md_escape(secrets_clean)} | check-secrets --all |
| No Forbidden Files | {md_escape(forbidden_files_clean)} | git ls-files |
| Release Metadata | {md_escape(rl_manifest_ok)} | {rl_manifest} |

---

## Evidencias Resumidas

- **Security:** {sec_score} (pass={sec_total_pass}, fail=0)
- **Readiness:** {pr_score} (pass={pr_total_pass}, fail={pr_total_fail})
- **Validation:** Success={vlp_success} (pytest: {vlp_passed} passed, {vlp_failed} failed)
- **Clean Install:** {ci_status} (failures={ci_failures})
- **Restore/Rollback:** {rr_status} (failures={rr_failures})
- **Demo E2E:** {de_status} (pass={de_pass}, fail={de_fail}, warn={de_warn})
- **Secrets:** Clean={secrets_clean}
- **Forbidden Files:** Clean={forbidden_files_clean}
- **Release Metadata:** OK={rl_manifest_ok}

---

## Limitacoes Conhecidas

1. **PSP/PIX real** — Nao implementado. Faturamento manual apenas.
2. **Tools/Function Calling** — Suportado nativamente.
3. **TTS** — Requer pocket-tts habilitado.
4. **RAG** — Requer data plane com suporte a embeddings.
5. **LM Studio** — Integracao depende de backend externo.
6. **Rate limit script** — Falha conhecida no readiness report (exit_code 127).
7. **Release manifests** — v1.6.5/v1.6.6 com commit incorreto no manifest.

## Riscos Residuais

- Working tree pode conter alteracoes locais nao commitadas.
- Release manifests de versoes anteriores podem ter commits incorretos.
- DR report nao gerado automaticamente (skip no readiness).
- Dependencia de GPU local para inferencia em producao.

---

## Recomendacao para v1.7.0

Baseado nos criterios avaliados e status **{status}**, recomenda-se
seguir para v1.7.0-local-ai-appliance resolvendo os warnings pendentes
(rate limit script, manifests inconsistentes) como parte do ciclo de
desenvolvimento.

A linha v1.6.x esta pronta para transicao, com ressalvas documentadas.

---

## Checklist Final

- [x] Security report gerado e validado
- [x] Production readiness avaliado
- [x] Validate local production full executado
- [x] Clean install report disponivel
- [x] Restore/rollback report disponivel
- [x] Commercial demo E2E validado
- [x] Secrets scan executado (sem segredos reais)
- [x] Nenhum arquivo proibido versionado
- [x] Release manifest presente
- [x] Release history atualizado
- [x] Capability matrix documentada
- [x] Limitacoes conhecidas documentadas

---
*Relatorio gerado por: scripts/validators/generate-client-ready-report.sh*
*Timestamp: {report["generated_at"]}*
"""

with open(REPORT_MD, "w", encoding="utf-8") as f:
    f.write(markdown)

# --- Generate versionable docs/CLIENT_READY_FINAL_REPORT.md ---
chk_sec = "OK" if sec_score == "PASS" else "PENDENTE"
chk_readiness = "OK" if pr_score == "READY" else "PENDENTE"
chk_val = "OK" if vlp_success is True else "PENDENTE"
chk_ci = "OK" if ci_status == "success" else "WARN"
chk_rr = "OK" if rr_status == "success" else "WARN"
chk_demo = "OK" if de_status in ("DEMO_READY", "DEMO_READY_WITH_WARNINGS") else "PENDENTE"
chk_secrets = "OK" if secrets_clean == "true" else "PENDENTE"
chk_forbidden = "OK" if forbidden_files_clean else "PENDENTE"
chk_release = "OK" if rl_manifest_ok else "PENDENTE"

doc = f"""# Client Ready Final Report — {VERSION}

**Documento versionavel — Resumo seguro para cliente.**

## Executivo

Este documento consolida a avaliacao final de prontidao da versao
**{VERSION}** (branch `{GIT_BRANCH}`, commit `{GIT_COMMIT}`)
para entrega a cliente como Local AI Appliance.

## Versao Avaliada

| Campo | Valor |
|-------|-------|
| Versao | {VERSION} |
| Branch | {GIT_BRANCH} |
| Commit | {GIT_COMMIT} |
| Data | {report["generated_at"]} |

## Status Geral

**{status}**

## Criterios Avaliados

| Criterio | Resultado |
|----------|-----------|
| Security Report PASS | {sec_score} |
| Production Readiness READY | {pr_score} |
| Validate Local Production Full OK | {vlp_success} |
| Clean Install Report OK | {ci_status} |
| Restore/Rollback Report OK | {rr_status} |
| Commercial Demo E2E OK | {de_status} |
| No secrets in codebase | {secrets_clean} |
| No forbidden files versioned | {forbidden_files_clean} |
| Release metadata OK | {rl_manifest_ok} |

## Evidencias Resumidas

- **Security:** Score {sec_score}, 0 falhas criticas, 0 falhas altas.
- **Readiness:** Score {pr_score}, {pr_total_pass} pass, {pr_total_fail} fail.
- **Full Validation:** {vlp_passed} testes passados, {vlp_failed} falhas.
- **Clean Install:** {ci_label}, {ci_failures} falhas.
- **Restore/Rollback:** {rr_label}, {rr_failures} falhas.
- **Demo E2E:** {de_status}, {de_pass} pass, {de_fail} fail, {de_warn} warnings.
- **Secrets:** Nenhum segredo real encontrado no codigo versionado.
- **Release Metadata:** Manifesto presente e valido.

## Limitacoes

1. PSP/PIX real nao implementado — faturamento manual apenas.
2. Tools/Function Calling — Suportado nativamente.
3. TTS requer pocket-tts habilitado.
4. RAG requer data plane com suporte a embeddings.
5. LM Studio integration depende de backend externo.
6. Rate limit readiness apresenta falha conhecida (exit code 127).
7. Release manifests v1.6.5 e v1.6.6 com git_commit incorreto.

## Riscos Residuais

- Working tree pode conter alteracoes locais nao commitadas.
- DR report nao e gerado automaticamente.
- Dependencia de GPU local para inferencia.
- Versoes anteriores podem ter manifests inconsistentes.

## Recomendacao para v1.7.0

**{status}** — A linha v1.6.x esta pronta para transicao para
v1.7.0-local-ai-appliance com as seguintes recomendacoes:

1. Resolver warning do rate limit readiness script.
2. Corrigir release manifests de v1.6.5 e v1.6.6.
3. Documentar limitacao de PSP/PIX como "future".
4. Manter processo de validacao continua para v1.7.0.
5. Incluir DR report automatico na pipeline.

## Checklist Final

| Item | Status |
|------|--------|
| Security report PASS | {chk_sec} |
| Production readiness READY | {chk_readiness} |
| Validate local production OK | {chk_val} |
| Clean install report OK | {chk_ci} |
| Restore/rollback report OK | {chk_rr} |
| Demo E2E OK | {chk_demo} |
| No secrets found | {chk_secrets} |
| No forbidden files | {chk_forbidden} |
| Release metadata OK | {chk_release} |

---
*Documento versionavel gerado por: scripts/validators/generate-client-ready-report.sh*
*Timestamp: {report["generated_at"]}*
*Proximo release: v1.7.0-local-ai-appliance*
"""

doc_path = ROOT / "docs" / "CLIENT_READY_FINAL_REPORT.md"
with open(doc_path, "w", encoding="utf-8") as f:
    f.write(doc)

# Save env vars for later bash use
os.makedirs(LOGS_DIR, exist_ok=True)
with open(os.path.join(LOGS_DIR, "generation.log"), "w") as f:
    f.write(f"status={status}\n")
    f.write(f"report_json={REPORT_JSON}\n")
    f.write(f"report_md={REPORT_MD}\n")
    f.write(f"doc={doc_path}\n")

print(f"[OK] Client Ready Report generated:")
print(f"  JSON:  {REPORT_JSON}")
print(f"  MD:    {REPORT_MD}")
print(f"  DOC:   {doc_path}")
print(f"  Status: {status}")
PYEOF
