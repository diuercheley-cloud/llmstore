#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() {
  printf '[install] %s\n' "$*"
}

fail() {
  printf '[install][error] %s\n' "$*" >&2
  exit 1
}

log "detecting platform"
uname -a || true

if [[ ! -x "${ROOT_DIR}/scripts/install-wsl-deps.sh" ]]; then
  fail "missing scripts/install-wsl-deps.sh"
fi

log "installing base dependencies"
"${ROOT_DIR}/scripts/install-wsl-deps.sh"

log "checking docker"
if ! command -v docker >/dev/null 2>&1; then
  fail "docker not found in PATH"
fi
docker --version

if ! docker compose version >/dev/null 2>&1; then
  fail "docker compose plugin not found"
fi
docker compose version

log "ensuring local env file exists"
if [[ ! -f "${ROOT_DIR}/.env.local" ]]; then
  cp "${ROOT_DIR}/.env.example" "${ROOT_DIR}/.env.local"
  chmod 600 "${ROOT_DIR}/.env.local"
  log ".env.local created from .env.example"
else
  chmod 600 "${ROOT_DIR}/.env.local"
  log ".env.local already exists"
fi

log "installation bootstrap complete"
printf '[install] next_step=%s\n' "${ROOT_DIR}/scripts/first-run.sh"
