#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"

echo "--- Iniciando Validacao do Benchmark Local ---"

# Limpa benchmarks antigos do teste
rm -rf "${ROOT_DIR}/artifacts/model-benchmarks/test-model-*"

# 1. Roda benchmark curto (mock ou modelo padrao)
echo "[1/4] Rodando benchmark curto (--quick)..."
"${SCRIPT_DIR}/../dev/benchmark-model-local.sh" \
    --model "test-model-mock" \
    --quick \
    --output-dir "${ROOT_DIR}/artifacts/model-benchmarks"

# Encontra a pasta gerada
BENCH_DIR=$(find "${ROOT_DIR}/artifacts/model-benchmarks" -type d -name "test-model-mock" | head -n 1)
LATEST_DIR=$(find "${BENCH_DIR}" -mindepth 1 -maxdepth 1 -type d | sort -r | head -n 1)

if [[ -z "${LATEST_DIR}" ]]; then
    echo "ERRO: Pasta de benchmark nao encontrada!"
    exit 1
fi

echo "Pasta gerada: ${LATEST_DIR}"

# 2. Valida JSON
echo "[2/4] Validando benchmark.json..."
if [[ ! -f "${LATEST_DIR}/benchmark.json" ]]; then
    echo "ERRO: benchmark.json nao encontrado!"
    exit 1
fi

if ! python3 -c "import json, sys; json.load(open(sys.argv[1]))" "${LATEST_DIR}/benchmark.json"; then
    echo "ERRO: benchmark.json invalido!"
    exit 1
fi

# Verifica se algumas chaves estao presentes
python3 -c "
import json, sys
data = json.load(open(sys.argv[1]))
req = ['model_requested', 'model_resolved', 'backend', 'runs', 'concurrency', 'total_tokens', 'tokens_per_second', 'error_rate']
for r in req:
    if r not in data:
        print(f'ERRO: Chave {r} faltando no JSON')
        sys.exit(1)
" "${LATEST_DIR}/benchmark.json"

# 3. Valida MD
echo "[3/4] Validando benchmark.md..."
if [[ ! -f "${LATEST_DIR}/benchmark.md" ]]; then
    echo "ERRO: benchmark.md nao encontrado!"
    exit 1
fi

if ! grep -q "Recommendation" "${LATEST_DIR}/benchmark.md"; then
    echo "ERRO: benchmark.md sem secao de recomendacao!"
    exit 1
fi

# 4. Valida ausencia de API keys nos artefatos
echo "[4/4] Validando ausencia de segredos..."
if grep -qE "(Bearer|sk-[a-zA-Z0-9]{20,})" -r "${LATEST_DIR}"; then
    echo "ERRO: API Key vazada nos artefatos do benchmark!"
    exit 1
fi

# 5. Valida modelo inexistente (deve retornar erro e nao crashar)
echo "[5/5] Testando comportamento com modelo inexistente..."
"${SCRIPT_DIR}/../dev/benchmark-model-local.sh" \
    --model "modelo-que-nao-existe-999" \
    --quick \
    --output-dir "${ROOT_DIR}/artifacts/model-benchmarks" || true # expected to finish but maybe log error

NON_EXISTENT_DIR=$(find "${ROOT_DIR}/artifacts/model-benchmarks" -type d -name "modelo-que-nao-existe-999" | head -n 1)
LATEST_NON_EXISTENT=$(find "${NON_EXISTENT_DIR}" -mindepth 1 -maxdepth 1 -type d | sort -r | head -n 1)

if [[ -f "${LATEST_NON_EXISTENT}/benchmark.json" ]]; then
    ERR_RATE=$(python3 -c "import json, sys; print(json.load(open(sys.argv[1]))['error_rate'])" "${LATEST_NON_EXISTENT}/benchmark.json")
    if (( $(echo "$ERR_RATE < 1.0" | bc -l) )); then
        echo "ERRO: Modelo inexistente nao retornou 100% de erro!"
        exit 1
    fi
fi

echo "Validacao concluida com sucesso!"
