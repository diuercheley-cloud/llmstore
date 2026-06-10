#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE_PATH="${ENV_FILE:-${ROOT_DIR}/.env.prod}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "run as root on the VPS so docker, firewall and filesystem setup can be completed"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required"
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose plugin is required"
  exit 1
fi

SERVER_NAME="${SERVER_NAME:-}"
LETSENCRYPT_EMAIL="${LETSENCRYPT_EMAIL:-}"
if [[ -z "${SERVER_NAME}" || -z "${LETSENCRYPT_EMAIL}" ]]; then
  echo "export SERVER_NAME and LETSENCRYPT_EMAIL before running deploy-vps.sh"
  exit 1
fi

if [[ ! -f "${ENV_FILE_PATH}" ]]; then
  cp "${ROOT_DIR}/.env.prod" "${ENV_FILE_PATH}"
  chmod 600 "${ENV_FILE_PATH}"
fi

python3 - "${ENV_FILE_PATH}" "${SERVER_NAME}" "${LETSENCRYPT_EMAIL}" <<'PY'
import secrets
import sys
from pathlib import Path

env_path = Path(sys.argv[1])
server_name = sys.argv[2]
email = sys.argv[3]
lines = env_path.read_text(encoding="utf-8").splitlines()
current = {}
for line in lines:
    if "=" in line:
        key, value = line.split("=", 1)
        current[key] = value
updates = {
    "SERVER_NAME": server_name,
    "LETSENCRYPT_EMAIL": email,
    "PUBLIC_BASE_URL": f"https://{server_name}",
    "CORS_ALLOW_ORIGINS": f"https://{server_name}",
    "PUBLIC_EXPOSURE": "true",
    "PUBLIC_SIGNUP_ENABLED": "true",
}

def secure_token(length: int) -> str:
    return secrets.token_urlsafe(length)

generated = {
    "ADMIN_TOKEN": secure_token(32),
    "POSTGRES_PASSWORD": secure_token(24),
}

for line in lines:
    if "=" not in line:
        continue
    key = line.split("=", 1)[0]
    if key in generated and ("replace-with" in line or "change-this" in line):
        updates[key] = generated[key]

postgres_password = updates.get("POSTGRES_PASSWORD", current.get("POSTGRES_PASSWORD", "llm_gateway_dev_password"))
postgres_db = current.get("POSTGRES_DB", "llm_gateway")
postgres_user = current.get("POSTGRES_USER", "llm_gateway")
updates["DATABASE_URL"] = f"postgresql+asyncpg://{postgres_user}:{postgres_password}@postgres:5432/{postgres_db}"

written = []
seen = set()
for line in lines:
    if "=" not in line:
        written.append(line)
        continue
    key, _ = line.split("=", 1)
    if key in updates:
        written.append(f"{key}={updates[key]}")
        seen.add(key)
    else:
        written.append(line)
for key, value in updates.items():
    if key not in seen:
        written.append(f"{key}={value}")

env_path.write_text("\n".join(written) + "\n", encoding="utf-8")
PY

chmod 600 "${ENV_FILE_PATH}"

cd "${ROOT_DIR}"
ENV_FILE="$(basename "${ENV_FILE_PATH}")" STACK_MODE=prod "${ROOT_DIR}/scripts/deploy/up.sh"
docker compose --env-file "$(basename "${ENV_FILE_PATH}")" -f docker-compose.yml -f docker-compose.prod.yml ps

echo "deployment started"
echo "public url: https://${SERVER_NAME}"
echo "health: https://${SERVER_NAME}/health"
echo "pricing: https://${SERVER_NAME}/pricing"
