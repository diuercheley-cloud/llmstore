#!/usr/bin/env bash
set -euo pipefail

MODEL_REPO="${MODEL_REPO:-bartowski/gemma-2-2b-it-GGUF}"
MODEL_FILE="${MODEL_FILE:-gemma-2-2b-it-Q4_K_M.gguf}"
MODEL_ID="${MODEL_ID:-${MODEL_REPO}}"
MODELS_DIR="${MODELS_DIR:-/models}"
DATA_DIR="${QUICKSTART_DATA_DIR:-/data/quickstart}"
DATABASE_PATH="${QUICKSTART_DB_PATH:-${DATA_DIR}/llmstack.db}"

export OPERATIONAL_PROFILE="${OPERATIONAL_PROFILE:-lite}"
export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:////data/quickstart/llmstack.db}"
export REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/0}"
export DATA_PLANE_BASE_URL="${DATA_PLANE_BASE_URL:-http://127.0.0.1:8081}"
export CONTROL_PLANE_HOST="${CONTROL_PLANE_HOST:-0.0.0.0}"
export CONTROL_PLANE_PORT="${CONTROL_PLANE_PORT:-8080}"
export DEPLOYMENT_MODE="${DEPLOYMENT_MODE:-appliance}"
export LOCAL_APPLIANCE_MODE="${LOCAL_APPLIANCE_MODE:-true}"
export LOCALHOST_MODE="${LOCALHOST_MODE:-true}"
export PUBLIC_EXPOSURE="${PUBLIC_EXPOSURE:-false}"
export ADMIN_TOKEN="${ADMIN_TOKEN:-QuickstartAdminToken-ChangeMe-1234}"
export JWT_SECRET="${JWT_SECRET:-quickstart-jwt-secret-change-me}"
export MODEL_ID
export MODEL_REPO
export MODEL_FILE
export MODELS_DIR
export RAG_ENABLED="${RAG_ENABLED:-true}"
export TTS_ENABLED="${TTS_ENABLED:-false}"
export OBSERVABILITY_ENABLED="${OBSERVABILITY_ENABLED:-false}"
export OTLP_EXPORT_ENABLED="${OTLP_EXPORT_ENABLED:-false}"
export PROVIDERS_ENABLED="${PROVIDERS_ENABLED:-local}"
export CLOUD_PROVIDERS_ENABLED="${CLOUD_PROVIDERS_ENABLED:-false}"
export MULTI_TENANT_ENABLED="${MULTI_TENANT_ENABLED:-false}"
export MARKETPLACE_ENABLED="${MARKETPLACE_ENABLED:-false}"
export PLUGIN_MARKETPLACE_ENABLED="${PLUGIN_MARKETPLACE_ENABLED:-false}"
export PLUGIN_RUNTIME_ENABLED="${PLUGIN_RUNTIME_ENABLED:-false}"
export AGENT_RUNTIME_ENABLED="${AGENT_RUNTIME_ENABLED:-false}"
export AGENT_WORKER_ENABLED="${AGENT_WORKER_ENABLED:-false}"
export AGENT_EXECUTION_ENABLED="${AGENT_EXECUTION_ENABLED:-false}"
export AGENT_MEMORY_ENABLED="${AGENT_MEMORY_ENABLED:-false}"
export KUBERNETES_MODE="${KUBERNETES_MODE:-false}"
export PROMETHEUS_ENABLED="${PROMETHEUS_ENABLED:-false}"
export LOKI_ENABLED="${LOKI_ENABLED:-false}"
export TEMPO_ENABLED="${TEMPO_ENABLED:-false}"
export PYTHONPATH="/app:/app/control_plane"
export PATH="/opt/venv/bin:${PATH}"

mkdir -p "${MODELS_DIR}" "${DATA_DIR}" /var/run/redis

MODEL_PATH="${MODELS_DIR}/${MODEL_FILE}"

log() {
  printf '[quickstart] %s\n' "$*"
}

wait_for_url() {
  local url="$1"
  local attempts="$2"
  local sleep_seconds="$3"
  local attempt
  for attempt in $(seq 1 "${attempts}"); do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      return 0
    fi
    sleep "${sleep_seconds}"
  done
  return 1
}

shutdown() {
  local code=$?
  log "shutting down quickstart processes"
  jobs -pr | xargs -r kill >/dev/null 2>&1 || true
  wait || true
  exit "${code}"
}

trap shutdown EXIT INT TERM

log "starting embedded redis"
redis-server \
  --save "" \
  --appendonly no \
  --bind 127.0.0.1 \
  --port 6379 \
  --daemonize yes \
  --dir /var/run/redis

if [[ ! -f "${MODEL_PATH}" ]]; then
  log "downloading quickstart model ${MODEL_REPO}/${MODEL_FILE}"
  python - <<'PY'
import os
from huggingface_hub import hf_hub_download

repo_id = os.environ["MODEL_REPO"]
filename = os.environ["MODEL_FILE"]
token = os.environ.get("HF_TOKEN")
local_dir = os.environ["MODELS_DIR"]

hf_hub_download(
    repo_id=repo_id,
    filename=filename,
    token=token,
    local_dir=local_dir,
    local_dir_use_symlinks=False,
)
PY
else
  log "reusing cached model ${MODEL_PATH}"
fi

log "starting local llama.cpp data plane"
LLAMA_SERVER_PORT=8081 \
MODEL_FILE="${MODEL_FILE}" \
/opt/quickstart/llama-entrypoint.sh &

if ! wait_for_url "http://127.0.0.1:8081/health" 120 2; then
  log "data plane failed to become healthy"
  exit 1
fi

if [[ "${DATABASE_URL}" == sqlite+aiosqlite:* ]]; then
  mkdir -p "$(dirname "${DATABASE_PATH}")"
  touch "${DATABASE_PATH}"
fi

log "running database migrations"
alembic -c /app/control_plane/alembic.ini upgrade heads

log "seeding default data"
python - <<'PY'
import asyncio

from app.db.session import SessionLocal
from app.services.seed import seed_defaults


async def main() -> None:
    async with SessionLocal() as session:
        await seed_defaults(session)
        await session.commit()


asyncio.run(main())
PY

log "starting generation worker"
python -m app.workers.generation_worker &

log "starting rag worker"
python -m app.workers.rag_worker &

log "starting control plane on :${CONTROL_PLANE_PORT}"
exec gunicorn -k uvicorn.workers.UvicornWorker \
     -w "${WEB_CONCURRENCY:-1}" \
     --timeout "${GUNICORN_TIMEOUT:-120}" \
     --keep-alive "${GUNICORN_KEEPALIVE:-5}" \
     --bind "${CONTROL_PLANE_HOST}:${CONTROL_PLANE_PORT}" \
     app.main:app
