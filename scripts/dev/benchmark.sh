#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"

init_stack_env

QUICK=false
APPLY=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --quick)
      QUICK=true
      shift
      ;;
    --apply)
      APPLY=true
      shift
      ;;
    -h|--help)
      cat <<'EOF'
Uso: ./scripts/dev/benchmark.sh [--quick] [--apply]

Opcoes:
  --quick   Roda uma unica configuracao smoke para validar o benchmark.
  --apply   Aplica a recomendacao gerada ao .env.local.
EOF
      exit 0
      ;;
    *)
      printf '[benchmark][error] opcao invalida: %s\n' "$1" >&2
      exit 2
      ;;
  esac
done

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="${ROOT_DIR}/artifacts/benchmarks/${TIMESTAMP}"
mkdir -p "${OUTPUT_DIR}"
RESULTS_FILE="${OUTPUT_DIR}/results.jsonl"

echo "--- Iniciando Benchmark para RTX 4050 ---"
echo "Resultados serão salvos em: ${OUTPUT_DIR}"

# Combinações de teste
if [[ "${QUICK}" == "true" ]]; then
  CTX_SIZES=("${LLAMA_CTX_SIZE:-1024}")
  LAYERS=("${LLAMA_N_GPU_LAYERS:-12}")
  BATCH_SIZES=("${LLAMA_BATCH_SIZE:-128}")
  UBATCH_SIZES=("${LLAMA_UBATCH_SIZE:-64}")
else
  CTX_SIZES=(1024 2048 3072)
  LAYERS=(12 16 20 24)
  BATCH_SIZES=(128 512)
  UBATCH_SIZES=(64 128)
fi

# Garantir que o stack está parado antes de começar
echo "Limpando ambiente..."
dc down

for ctx in "${CTX_SIZES[@]}"; do
  for layers in "${LAYERS[@]}"; do
    for batch in "${BATCH_SIZES[@]}"; do
      for ubatch in "${UBATCH_SIZES[@]}"; do
        # Pular se ubatch > batch (não faz sentido para llama.cpp)
        if [ "$ubatch" -gt "$batch" ]; then continue; fi

        echo "Testando: CTX=$ctx, LAYERS=$layers, BATCH=$batch, UBATCH=$ubatch"
        
        export LLAMA_CTX_SIZE=$ctx
        export LLAMA_N_GPU_LAYERS=$layers
        export LLAMA_BATCH_SIZE=$batch
        export LLAMA_UBATCH_SIZE=$ubatch
        
        # Iniciar data-plane
        dc up -d data-plane-gemma
        
        # Rodar benchmark runner
        CONFIG_JSON="{\"ctx\":$ctx, \"layers\":$layers, \"batch\":$batch, \"ubatch\":$ubatch}"
        python3 "${ROOT_DIR}/scripts/dev/benchmark_runner.py" "${CONFIG_JSON}" "${RESULTS_FILE}"
        
        # Parar data-plane para o próximo teste
        dc stop data-plane-gemma
      done
    done
  done
done

echo "Benchmark finalizado."

# Gerar Recomendação
echo "Analisando resultados..."
python3 -c "
import json
import sys

results = []
with open('${RESULTS_FILE}', 'r') as f:
    for line in f:
        results.append(json.loads(line))

if not results:
    print('Nenhum resultado encontrado.')
    sys.exit(1)

# Filtrar resultados estáveis (VRAM < 5500MB para RTX 4050 de 6GB)
stable_results = [r for r in results if float(r['metrics']['vram_used_mb'].replace(',', '')) < 5500]

if not stable_results:
    print('Nenhuma configuração estável encontrada (VRAM > 5500MB).')
    best = max(results, key=lambda x: x['metrics']['tokens_per_s'] or 0)
else:
    # Escolher a melhor performance entre as estáveis
    best = max(stable_results, key=lambda x: x['metrics']['tokens_per_s'] or 0)

print('\n--- Recomendação Automática ---')
print(f'Melhor Config: CTX={best[\"config\"][\"ctx\"]}, LAYERS={best[\"config\"][\"layers\"]}, BATCH={best[\"config\"][\"batch\"]}, UBATCH={best[\"config\"][\"ubatch\"]}')
print(f'Performance: {best[\"metrics\"][\"tokens_per_s\"]} tokens/s')
print(f'VRAM Estimada: {best[\"metrics\"][\"vram_used_mb\"]} MB')

with open('${OUTPUT_DIR}/recommendation.json', 'w') as f:
    json.dump(best, f, indent=2)
"

echo "Para aplicar esta config no .env.local, rode: scripts/dev/benchmark.sh --apply"

if [[ "${APPLY}" == "true" ]]; then
    RECOMMENDATION_FILE="${OUTPUT_DIR}/recommendation.json"
    if [[ -f "${RECOMMENDATION_FILE}" ]]; then
        CTX=$(jq -r '.config.ctx' "${RECOMMENDATION_FILE}")
        LAYERS=$(jq -r '.config.layers' "${RECOMMENDATION_FILE}")
        BATCH=$(jq -r '.config.batch' "${RECOMMENDATION_FILE}")
        UBATCH=$(jq -r '.config.ubatch' "${RECOMMENDATION_FILE}")
        
        echo "Aplicando configurações ao .env.local..."
        sed -i "s/LLAMA_CTX_SIZE=.*/LLAMA_CTX_SIZE=${CTX}/" "${ROOT_DIR}/.env.local"
        sed -i "s/LLAMA_N_GPU_LAYERS=.*/LLAMA_N_GPU_LAYERS=${LAYERS}/" "${ROOT_DIR}/.env.local"
        sed -i "s/LLAMA_BATCH_SIZE=.*/LLAMA_BATCH_SIZE=${BATCH}/" "${ROOT_DIR}/.env.local"
        sed -i "s/LLAMA_UBATCH_SIZE=.*/LLAMA_UBATCH_SIZE=${UBATCH}/" "${ROOT_DIR}/.env.local"
        echo "Pronto! Reinicie o stack para aplicar."
    fi
fi
