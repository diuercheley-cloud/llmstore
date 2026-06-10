#!/usr/bin/env bash
# Owner: agent-platform
# Run agent real provider validation suite with budget, timeout, and safety guards.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../dev/common.sh" 2>/dev/null || true

PYTHON_EXEC="${ROOT_DIR:-.}/.venv/bin/python"
if [[ ! -f "${PYTHON_EXEC}" ]]; then
  PYTHON_EXEC="python3"
fi

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
MODE="dry-run"
PROVIDERS=""
OUTPUT_DIR="artifacts/evals/real-provider-validation/latest"
TIMEOUT=60
BUDGET=1.00
ALLOW_PAID=false

# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------
function usage() {
  cat <<EOF
Usage: $0 [options]

Run agent real provider validation suite.

Options:
  --real              Execute real provider calls (opt-in, may incur cost)
  --providers LIST    Comma-separated providers (default: all)
  --budget BRL        Max budget in BRL (default: 1.00)
  --timeout SECONDS   Per-request timeout (default: 60)
  --allow-paid        Allow paid provider calls (default: false)
  --output-dir DIR    Output directory (default: $OUTPUT_DIR)
  --help              Show this help
EOF
  exit 1
}

# ---------------------------------------------------------------------------
# Parse args
# ---------------------------------------------------------------------------
while [[ "$#" -gt 0 ]]; do
  case $1 in
    --real) MODE="real" ;;
    --providers) PROVIDERS="$2"; shift ;;
    --budget) BUDGET="$2"; shift ;;
    --timeout) TIMEOUT="$2"; shift ;;
    --allow-paid) ALLOW_PAID=true ;;
    --output-dir) OUTPUT_DIR="$2"; shift ;;
    --help) usage ;;
    *) echo "Unknown option: $1"; usage ;;
  esac
  shift
done

# ---------------------------------------------------------------------------
# Safety checks
# ---------------------------------------------------------------------------
echo "========================================="
echo " Agent Real Provider Validation"
echo "========================================="
echo "Mode:      $MODE"
echo "Providers: ${PROVIDERS:-all}"
echo "Budget:    R\$ $BUDGET"
echo "Timeout:   ${TIMEOUT}s"
echo "Allow Paid: $ALLOW_PAID"
echo ""

# Budget guard: never exceed R$ 10.00 regardless of user input
if (( $(echo "$BUDGET > 10.00" | bc -l 2>/dev/null || echo 1) )); then
  echo "[SAFETY] Budget capped at R\$ 10.00 (input was R\$ $BUDGET)"
  BUDGET=10.00
fi

# Paid provider guard
if [[ "$ALLOW_PAID" != "true" ]]; then
  echo "[SAFETY] Paid providers blocked. Set --allow-paid to enable."
fi

# ---------------------------------------------------------------------------
# Set env vars
# ---------------------------------------------------------------------------
export AGENT_REAL_PROVIDER_VALIDATION_ENABLED=true
export AGENT_REAL_PROVIDER_VALIDATION_ALLOW_PAID=$ALLOW_PAID
export AGENT_REAL_PROVIDER_VALIDATION_BUDGET_BRL=$BUDGET
export AGENT_REAL_PROVIDER_VALIDATION_TIMEOUT_SECONDS=$TIMEOUT

if [[ -n "$PROVIDERS" ]]; then
  export AGENT_REAL_PROVIDER_VALIDATION_PROVIDERS="$PROVIDERS"
fi

# ---------------------------------------------------------------------------
# Run validation
# ---------------------------------------------------------------------------
SCRIPT=$(cat << 'PYEOF'
import asyncio
import json
import os
import sys

sys.path.insert(0, "control_plane")
from app.services.agents.provider_validation import (
    RealProviderValidator,
    run_validation_suite,
)

async def main():
    providers_env = os.environ.get("AGENT_REAL_PROVIDER_VALIDATION_PROVIDERS", "")
    providers = [p.strip() for p in providers_env.split(",")] if providers_env else None

    result = await run_validation_suite(providers)

    print("\n=== RESULTS ===")
    print(json.dumps(result, indent=2, default=str))

    summary = result.get("summary", {})
    total = summary.get("total_providers", 0)
    passed = summary.get("passed", 0)
    degraded = summary.get("degraded", 0)
    skipped = summary.get("skipped", 0)
    errors = summary.get("error", 0)
    cost = summary.get("total_cost_brl", 0.0)

    print(f"\n--- Summary ---")
    print(f"Providers tested: {total}")
    print(f"Passed: {passed}  Degraded: {degraded}  Skipped: {skipped}  Errors: {errors}")
    print(f"Total cost: R$ {cost:.6f}")

    if errors > 0:
        sys.exit(1)
    if cost > float(os.environ.get("AGENT_REAL_PROVIDER_VALIDATION_BUDGET_BRL", "1.00")):
        print(f"[BUDGET] Cost R$ {cost:.6f} exceeds budget, but suite completed.")
    sys.exit(0)

asyncio.run(main())
PYEOF
)

export PYTHONPATH="${PYTHONPATH:-}:control_plane"
"$PYTHON_EXEC" -c "$SCRIPT"
