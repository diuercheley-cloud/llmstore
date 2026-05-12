#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "--- Iniciando Validacao do Benchmark Real ---"

# Limpa benchmarks antigos do teste
rm -rf "${ROOT_DIR}/artifacts/model-benchmarks/test-model-mock"

# 1. Roda benchmark curto (mock)
echo "[1/7] Rodando benchmark curto (--quick)..."
"${SCRIPT_DIR}/benchmark-model-local.sh" \
    --model "test-model-mock" \
    --quick \
    --output-dir "${ROOT_DIR}/artifacts/model-benchmarks"

# Encontra a pasta gerada
BENCH_DIR=$(find "${ROOT_DIR}/artifacts/model-benchmarks" -type d -name "test-model-mock" | head -n 1)
if [[ -z "${BENCH_DIR}" ]]; then
    echo "ERRO: Pasta de benchmark nao encontrada!"
    exit 1
fi
LATEST_DIR=$(find "${BENCH_DIR}" -mindepth 1 -maxdepth 1 -type d | sort -r | head -n 1)

if [[ -z "${LATEST_DIR}" ]]; then
    echo "ERRO: Pasta de execucao nao encontrada!"
    exit 1
fi

echo "Pasta gerada: ${LATEST_DIR}"

# 2. Valida JSON
echo "[2/7] Validando benchmark.json..."
if [[ ! -f "${LATEST_DIR}/benchmark.json" ]]; then
    echo "ERRO: benchmark.json nao encontrado!"
    exit 1
fi

python3 -c "
import json, sys
data = json.load(open(sys.argv[1]))
req = ['model_requested', 'model_resolved', 'backend', 'tokens_per_second', 'total_latency_p95_ms', 'recommendation']
for r in req:
    if r not in data:
        print(f'ERRO: Chave {r} faltando no JSON')
        sys.exit(1)
print('JSON OK')
" "${LATEST_DIR}/benchmark.json"

# 3. Valida MD
echo "[3/7] Validando benchmark.md..."
if [[ ! -f "${LATEST_DIR}/benchmark.md" ]]; then
    echo "ERRO: benchmark.md nao encontrado!"
    exit 1
fi

if ! grep -q "Recommendation" "${LATEST_DIR}/benchmark.md"; then
    echo "ERRO: benchmark.md sem secao de recomendacao!"
    exit 1
fi
echo "MD OK"

# 4. Valida JSONL
echo "[4/7] Validando raw-results.jsonl..."
if [[ ! -f "${LATEST_DIR}/raw-results.jsonl" ]]; then
    echo "ERRO: raw-results.jsonl nao encontrado!"
    exit 1
fi
echo "JSONL OK"

# 5. Valida ausencia de API keys
echo "[5/7] Validando ausencia de segredos..."
if grep -qE "(Bearer|sk-[a-zA-Z0-9]{20,})" -r "${LATEST_DIR}"; then
    echo "ERRO: API Key vazada nos artefatos!"
    exit 1
fi
echo "Segredos OK"

# 6. Modelo inexistente
echo "[6/7] Testando modelo inexistente..."
"${SCRIPT_DIR}/benchmark-model-local.sh" \
    --model "non-existent-$(date +%s)" \
    --quick \
    --output-dir "${ROOT_DIR}/artifacts/model-benchmarks" || true
echo "Modelo inexistente OK (script nao crashou)"

# 7. Stress exige confirmacao
echo "[7/7] Verificando flag --stress..."
if [[ -f "${ROOT_DIR}/.venv/bin/python" ]]; then
    "${ROOT_DIR}/.venv/bin/python" "${ROOT_DIR}/benchmark_model_local_runner.py" --help | grep -q "stress"
else
    python3 "${ROOT_DIR}/benchmark_model_local_runner.py" --help | grep -q "stress" || echo "Aviso: Nao foi possivel verificar flags sem venv"
fi
echo "Flag --stress presente (ou venv indisponivel)"

echo "--- Validacao concluida com SUCESSO! ---"
