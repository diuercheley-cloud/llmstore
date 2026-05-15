#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[commercial-ha] validating leader election, failover, fencing and singleton jobs"
if [[ -x "./venv/bin/pytest" ]]; then
  ./venv/bin/pytest -q tests/test_commercial_leader_election.py
else
  pytest -q tests/test_commercial_leader_election.py
fi
echo "[commercial-ha] validation finished"
