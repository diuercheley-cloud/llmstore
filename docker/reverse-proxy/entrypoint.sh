#!/usr/bin/env bash
set -euo pipefail

mkdir -p /etc/nginx/conf.d

template="/templates/nginx-http.conf"
if [[ "${ENABLE_TLS:-false}" == "true" ]]; then
  if [[ -f "${TLS_CERT_PATH:-}" && -f "${TLS_KEY_PATH:-}" ]]; then
    template="/templates/nginx-tls.conf"
  else
    echo "ENABLE_TLS=true but TLS files not found; falling back to HTTP only" >&2
  fi
fi

export SERVER_NAME="${SERVER_NAME:-localhost}"
export CONTROL_PLANE_UPSTREAM="${CONTROL_PLANE_UPSTREAM:-http://control-plane:8080}"
export TLS_CERT_PATH="${TLS_CERT_PATH:-/etc/nginx/tls/tls.crt}"
export TLS_KEY_PATH="${TLS_KEY_PATH:-/etc/nginx/tls/tls.key}"

envsubst '${SERVER_NAME} ${CONTROL_PLANE_UPSTREAM} ${TLS_CERT_PATH} ${TLS_KEY_PATH}' < "${template}" > /etc/nginx/conf.d/default.conf

exec nginx -g 'daemon off;'
