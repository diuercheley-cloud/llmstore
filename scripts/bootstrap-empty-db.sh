#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

cd "${ROOT_DIR}"

FORCE=false
QUIET=false
for arg in "$@"; do
  case "${arg}" in
    --force)
      FORCE=true
      ;;
    --quiet)
      QUIET=true
      ;;
  esac
done

log() {
  if [[ "${QUIET}" != "true" ]]; then
    printf '%s\n' "$1"
  fi
}

if ! dc ps postgres >/dev/null 2>&1; then
  log "[bootstrap-db] postgres service is not available."
  exit 2
fi

table_count="$(dc exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Atc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null || echo "error")"
if [[ "${table_count}" == "error" ]]; then
  log "[bootstrap-db] failed to inspect database state."
  exit 3
fi

if [[ "${FORCE}" != "true" && "${table_count}" != "0" ]]; then
  log "[bootstrap-db] database is not empty (${table_count} public tables); skipping bootstrap."
  exit 20
fi

head_revision="$(PYTHONPATH=control_plane "${ROOT_DIR}/.venv/bin/python" -m alembic -c control_plane/alembic.ini heads | awk 'NR==1 {print $1}')"
if [[ -z "${head_revision}" ]]; then
  log "[bootstrap-db] failed to resolve alembic head revision."
  exit 4
fi

log "[bootstrap-db] bootstrapping schema directly from current models and stamping revision ${head_revision}."
dc run --rm --no-deps control-plane sh -lc "
  cd /app && /opt/venv/bin/python - <<'PY'
from sqlalchemy import create_engine, text

from app.db.base import Base
import app.models  # noqa: F401

engine = create_engine('${DATABASE_URL/+asyncpg/+psycopg}')
with engine.begin() as conn:
    conn.execute(text('CREATE EXTENSION IF NOT EXISTS pgcrypto'))
Base.metadata.create_all(engine)
with engine.begin() as conn:
    conn.execute(text(\"CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(128) NOT NULL PRIMARY KEY)\")) 
    conn.execute(text(\"DELETE FROM alembic_version\"))
    conn.execute(text(\"INSERT INTO alembic_version (version_num) VALUES ('${head_revision}')\"))
print('BOOTSTRAP_OK')
PY
"

log "[bootstrap-db] schema bootstrap completed."
exit 0
