#!/usr/bin/env bash
set -euo pipefail

# scripts/validators/validate-post-upgrade-smoke-local.sh
# Validates that the post-upgrade smoke test itself works correctly.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

echo "--- Validando Script de Smoke Test ---"

# 1. Run smoke test in JSON mode
# We use || true because the smoke test might fail if the stack is down, 
# but we still want to validate if it produced valid JSON.
SMOKE_OUTPUT=$(./scripts/validators/post-upgrade-smoke-local.sh --json || true)

# Check if output is empty
if [[ -z "${SMOKE_OUTPUT}" ]]; then
    echo "ERRO: Smoke test não produziu saída JSON."
    exit 1
fi

# 2. Validate JSON structure
echo "${SMOKE_OUTPUT}" | python3 -c 'import json, sys; 
try:
    data = json.load(sys.stdin)
    assert "timestamp" in data
    assert "results" in data
    assert isinstance(data["results"], list)
    print("OK: JSON estruturalmente válido.")
except Exception as e:
    print(f"ERRO: JSON inválido ou incompleto: {e}")
    sys.exit(1)
'

# 3. Validate Report files exist
TIMESTAMP=$(echo "${SMOKE_OUTPUT}" | python3 -c 'import json, sys; print(json.load(sys.stdin)["timestamp"])')
REPORT_DIR="artifacts/post-upgrade-smoke/${TIMESTAMP}"

if [[ -f "${REPORT_DIR}/smoke-report.json" ]] && [[ -f "${REPORT_DIR}/smoke-report.md" ]]; then
    echo "OK: Arquivos de relatório encontrados."
else
    echo "ERRO: Arquivos de relatório não encontrados em ${REPORT_DIR}"
    exit 1
fi

# 4. Check for secrets in logs
echo "Verificando se há secrets nos logs..."
if grep -rE "API_KEY|ADMIN_TOKEN|Bearer" "${REPORT_DIR}/logs" 2>/dev/null; then
    echo "ERRO: Secrets encontrados nos logs do smoke test!"
    exit 1
else
    echo "OK: Nenhum secret óbvio encontrado nos logs."
fi

# 5. Validate that skips work
./scripts/validators/post-upgrade-smoke-local.sh --skip-rag --skip-tts --json | python3 -c 'import json, sys;
data = json.load(sys.stdin)
rag_res = next((r for r in data["results"] if r["name"] == "rag_checks"), None)
tts_res = next((r for r in data["results"] if r["name"] == "tts_gen"), None)
if rag_res and rag_res["status"] == "SKIP" and tts_res and tts_res["status"] == "SKIP":
    print("OK: Skips funcionando.")
else:
    print(f"ERRO: Skips não funcionaram. RAG: {rag_res}, TTS: {tts_res}")
    sys.exit(1)
'

echo "--- Validação Concluída com Sucesso ---"
