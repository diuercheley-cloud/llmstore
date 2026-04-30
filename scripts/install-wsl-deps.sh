#!/usr/bin/env bash
set -euo pipefail

sudo apt-get update
sudo apt-get install -y build-essential cmake git curl wget python3 python3-venv

if command -v docker >/dev/null 2>&1; then
  docker --version
else
  echo "docker not found in PATH" >&2
fi

if command -v docker compose >/dev/null 2>&1; then
  docker compose version
else
  echo "docker compose plugin not found" >&2
fi

if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi
else
  echo "nvidia-smi not found; verify WSL2 GPU drivers" >&2
fi

