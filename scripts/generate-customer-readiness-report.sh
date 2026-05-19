#!/usr/bin/env bash
# scripts/generate-customer-readiness-report.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="$ROOT_DIR/artifacts/enterprise-pack/latest"
mkdir -p "$OUTPUT_DIR"

source "$ROOT_DIR/scripts/common.sh"
init_stack_env

REPORT_FILE="$OUTPUT_DIR/customer-readiness.md"

# Run operational readiness pack
"$ROOT_DIR/scripts/operational-readiness-pack.sh" > /dev/null

VERSION=$(cat "$ROOT_DIR/VERSION")
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Detect Modes
DEPLOYMENT_MODE="${DEPLOYMENT_MODE:-appliance}"
PKI_MODE=$([[ "${PKI_ENABLED:-false}" == "true" ]] && echo "Enabled" || echo "Disabled")
RBAC_MODE=$([[ "${RBAC_ADMIN_ENABLED:-false}" == "true" ]] && echo "Enabled" || echo "Disabled")
ATTESTATION=$([[ "${HARDWARE_TRUST_ENABLED:-false}" == "true" ]] && echo "Real (${HARDWARE_TRUST_PROVIDER})" || echo "Disabled/Advisory")
TOKENIZER_MODE="${TOKENIZER_MODE:-auto}"
HOT_SWAP=$([[ "${MODEL_HOT_SWAP_ENABLED:-false}" == "true" ]] && echo "Enabled" || echo "Disabled")

# Detect Payment Reality
PAYMENT_REAL=$([[ "${PAYMENT_REAL_ENABLED:-false}" == "true" ]] && echo "REAL (External PSP)" || echo "SIMULATED (Manual PIX/Demo only)")

# Find correct python binary
PYTHON_BIN="python3"
if [[ -f "$ROOT_DIR/.venv/bin/python3" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python3"
elif [[ -f "$ROOT_DIR/venv/bin/python3" ]]; then
  PYTHON_BIN="$ROOT_DIR/venv/bin/python3"
fi

cat <<EOF > "$REPORT_FILE"
# Customer Readiness Report
**Version**: $VERSION
**Generated at**: $TIMESTAMP
**Deployment Mode**: $DEPLOYMENT_MODE

## 1. Operational Status
$(cat "$ROOT_DIR/artifacts/operational-readiness/latest/summary.md" | sed '1,4d')

## 2. Platform Configuration
- **PKI Mode**: $PKI_MODE
- **RBAC Mode**: $RBAC_MODE
- **Hardware Attestation**: $ATTESTATION
- **Tokenizer Mode**: $TOKENIZER_MODE
- **Hot Swap Mode**: $HOT_SWAP
- **Payment Processing**: $PAYMENT_REAL

> **Notice**: Payment processing is in $PAYMENT_REAL mode. No real financial transactions are performed unless specifically configured with an external production PSP.

## 3. Model Inventory
EOF

if [[ -f "$ROOT_DIR/list_models.py" ]]; then
  echo "\`\`\`" >> "$REPORT_FILE"
  # Run with DATABASE_URL if available
  if [[ -n "$DATABASE_URL" ]]; then
    $PYTHON_BIN "$ROOT_DIR/list_models.py" >> "$REPORT_FILE" 2>&1
  else
    echo "DATABASE_URL not set. Skipping inventory." >> "$REPORT_FILE"
  fi
  echo "\`\`\`" >> "$REPORT_FILE"
else
  echo "Model inventory script not found." >> "$REPORT_FILE"
fi

cat <<EOF >> "$REPORT_FILE"

## 4. Backend Inventory
EOF

if [[ -f "$ROOT_DIR/list_backends.py" ]]; then
  echo "\`\`\`" >> "$REPORT_FILE"
  if [[ -n "$DATABASE_URL" ]]; then
    $PYTHON_BIN "$ROOT_DIR/list_backends.py" >> "$REPORT_FILE" 2>&1
  else
    echo "DATABASE_URL not set. Skipping inventory." >> "$REPORT_FILE"
  fi
  echo "\`\`\`" >> "$REPORT_FILE"
else
  echo "Backend inventory script not found." >> "$REPORT_FILE"
fi

cat <<EOF >> "$REPORT_FILE"

## 5. Security Summary
- **mTLS**: $([[ "$PKI_MODE" == "Enabled" ]] && echo "Active" || echo "Inactive (Plaintext/Token only)")
- **Hardware Trust**: $([[ "$ATTESTATION" == Real* ]] && echo "Hardware-backed" || echo "Software-defined (Advisory)")

---
*This report is generated automatically by the LLM Inference Stack Enterprise Packager.*
EOF

chmod +x "$REPORT_FILE"
echo "Customer readiness report generated at $REPORT_FILE"
