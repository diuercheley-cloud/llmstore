#!/usr/bin/env bash
# Atalho para ativar/subir o sistema LLM Inference Stack
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/up.sh" "$@"
