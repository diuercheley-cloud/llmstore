#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}/.."

ALLOW_WARNINGS=false

if [[ "${1:-}" == "--allow-warnings" ]]; then
    ALLOW_WARNINGS=true
fi

export BASE_URL="${BASE_URL:-http://localhost:18080}"
if [[ -z "${API_KEY:-}" ]]; then
    export API_KEY="$(./scripts/create-client.sh "Readiness Validator" | grep api_key= | cut -d= -f2)"
fi

echo "Rodando validadores novos..."
./scripts/diagnose-readiness-warnings-local.sh || true
./scripts/validate-usable-chat-model-local.sh || { echo "validate-usable-chat-model-local.sh falhou"; exit 1; }
./scripts/validate-chat-sse-readiness-local.sh || { echo "validate-chat-sse-readiness-local.sh falhou"; exit 1; }
./scripts/validate-tts-readiness-local.sh || { echo "validate-tts-readiness-local.sh falhou"; exit 1; }
./scripts/validate-rate-limit-readiness-local.sh || { echo "validate-rate-limit-readiness-local.sh falhou"; exit 1; }
./scripts/validate-cors-local-appliance.sh || { echo "validate-cors-local-appliance.sh falhou"; exit 1; }

echo "Rodando production-readiness-local.sh..."
OUTPUT=$(./scripts/production-readiness-local.sh)
echo "$OUTPUT"

REPORT_FILE=$(echo "$OUTPUT" | grep -o "artifacts/production-readiness/[0-9a-zA-Z_]*/report.json" || true)

if [ -z "$REPORT_FILE" ]; then
    REPORT_FILE=$(ls -t artifacts/production-readiness/*/report.json 2>/dev/null | head -1 || true)
fi

if [ ! -f "$REPORT_FILE" ]; then
    echo "Erro: report.json não encontrado"
    exit 1
fi

SCORE=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['score'])" "$REPORT_FILE")
CRITICAL_FAILURES=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['totals'].get('critical_failures', 0))" "$REPORT_FILE")

echo "Score final: $SCORE"
echo "Report: $REPORT_FILE"

if [ "$CRITICAL_FAILURES" -gt 0 ]; then
    echo "Erro: Foram encontradas falhas críticas ($CRITICAL_FAILURES)."
    exit 1
fi

if [ "$SCORE" = "NOT_READY" ]; then
    echo "Erro: Score é NOT_READY"
    exit 1
fi

if [ "$SCORE" = "READY_WITH_WARNINGS" ] && [ "$ALLOW_WARNINGS" = false ]; then
    echo "Erro: Score é READY_WITH_WARNINGS mas --allow-warnings não foi passado."
    exit 1
fi

echo "Validação concluída com sucesso."
exit 0
