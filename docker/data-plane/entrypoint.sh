#!/usr/bin/env bash
set -euo pipefail

MODEL_PATH="/models/${MODEL_FILE}"
export LD_LIBRARY_PATH="/opt/llama/bin:${LD_LIBRARY_PATH:-}"

if [[ ! -f "${MODEL_PATH}" ]]; then
  echo "Model file not found: ${MODEL_PATH}" >&2
  exit 1
fi

LLAMA_ARG_CONT_BATCHING=""
if [[ "${LLAMA_CONT_BATCHING:-true}" == "true" ]]; then
  LLAMA_ARG_CONT_BATCHING="--cont-batching"
fi

LLAMA_ARG_FLASH_ATTN=""
if [[ "${LLAMA_FLASH_ATTN:-false}" == "true" || "${LLAMA_FLASH_ATTN:-false}" == "on" ]]; then
  LLAMA_ARG_FLASH_ATTN="--flash-attn on"
else
  LLAMA_ARG_FLASH_ATTN="--flash-attn off"
fi

exec /opt/llama/bin/llama-server \
  --host 0.0.0.0 \
  --port 8081 \
  --model "${MODEL_PATH}" \
  -fit off \
  --ctx-size "${LLAMA_CTX_SIZE:-4096}" \
  --batch-size "${LLAMA_BATCH_SIZE:-256}" \
  --ubatch-size "${LLAMA_UBATCH_SIZE:-128}" \
  --threads "${LLAMA_THREADS:-8}" \
  --parallel "${LLAMA_PARALLEL:-1}" \
  --n-gpu-layers "${LLAMA_N_GPU_LAYERS:-20}" \
  ${LLAMA_ARG_CONT_BATCHING} \
  ${LLAMA_ARG_FLASH_ATTN}
