#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

RESTART=false
BUILD=false

usage() {
  cat <<'EOF'
Uso: ./scripts/backup/clean-compose-local.sh [--restart] [--build]

Opcoes:
  --restart   Sobe a stack novamente depois do cleanup
  --build     Rebuilda as imagens ao reiniciar
  -h, --help  Mostra esta ajuda
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --restart)
      RESTART=true
      ;;
    --build)
      BUILD=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[clean-compose-local][error] argumento inesperado: $1" >&2
      exit 1
      ;;
  esac
  shift
done

echo "[clean-compose-local] docker compose down --remove-orphans"
dc down --remove-orphans

MOCK_IDS="$(docker ps -aq \
  --filter "label=com.docker.compose.project=${COMPOSE_PROJECT_NAME:-llm-inference-stack}" \
  --filter "label=com.docker.compose.service=data-plane-mock")"
if [[ -n "${MOCK_IDS}" ]]; then
  echo "[clean-compose-local] removing lingering data-plane-mock container(s)"
  docker rm -f ${MOCK_IDS} >/dev/null
fi

if [[ "${RESTART}" == "true" ]]; then
  if [[ "${BUILD}" == "true" ]]; then
    echo "[clean-compose-local] docker compose up -d --build"
    dc up -d --build
  else
    echo "[clean-compose-local] docker compose up -d"
    dc up -d
  fi
fi
