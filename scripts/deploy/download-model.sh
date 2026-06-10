#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

MODEL_DIR="${ROOT_DIR}/models"

MODEL_REPO="${MODEL_REPO:-unsloth/gemma-4-E4B-it-GGUF}"
MODEL_FILE="${MODEL_FILE:-gemma-4-E4B-it-Q4_0.gguf}"

mkdir -p "${MODEL_DIR}"

if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "HF_TOKEN is required to download from Hugging Face if the repo enforces gated or authenticated access." >&2
fi

python3 -m venv "${ROOT_DIR}/.venv-download"
source "${ROOT_DIR}/.venv-download/bin/activate"
pip install --quiet --upgrade pip huggingface_hub
python - <<PY
import os
from huggingface_hub import hf_hub_download
hf_hub_download(
    repo_id="${MODEL_REPO}",
    filename="${MODEL_FILE}",
    token=os.environ.get("HF_TOKEN"),
    local_dir="${MODEL_DIR}",
    local_dir_use_symlinks=False,
)
print("Downloaded ${MODEL_FILE} to ${MODEL_DIR}")
PY
