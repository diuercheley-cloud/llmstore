#!/usr/bin/env bash
# scripts/generate-enterprise-pack.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="$ROOT_DIR/artifacts/enterprise-pack/latest"
mkdir -p "$OUTPUT_DIR"

source "$ROOT_DIR/scripts/common.sh"
init_stack_env

echo "Starting Enterprise Packaging Process..."

# 1. Generate Security Report
echo "Running Security Scan..."
"$ROOT_DIR/scripts/security-report-local.sh" --skip-artifacts-scan > /dev/null 2>&1

# Find latest security report
LATEST_SEC_MD=$(ls -t "$ROOT_DIR/artifacts/security-reports"/*/security-report.md | head -n 1)
if [[ -f "$LATEST_SEC_MD" ]]; then
  # Extract summary into enterprise-pack
  cat <<EOF > "$OUTPUT_DIR/security-summary.md"
# Security Summary
*Extracted from latest automated scan*

$(grep -A 5 "## Summary" "$LATEST_SEC_MD" | tail -n +3)

## Findings
$(grep -A 20 "## Blocking Findings" "$LATEST_SEC_MD" | tail -n +3 | head -n 10)

> **Note**: Full security report available in artifacts/security-reports/
EOF
else
  echo "# Security Summary (Draft)" > "$OUTPUT_DIR/security-summary.md"
  echo "Security report not found. Run scripts/security-report-local.sh first." >> "$OUTPUT_DIR/security-summary.md"
fi

# 2. Generate Customer Readiness Report
echo "Generating Customer Readiness Report..."
"$ROOT_DIR/scripts/generate-customer-readiness-report.sh"

# 3. Generate Acceptance Report
echo "Generating Acceptance Report Template..."
"$ROOT_DIR/scripts/generate-acceptance-report.sh"

# 4. Generate Deployment Summary
echo "Generating Deployment Summary..."
cat <<EOF > "$OUTPUT_DIR/deployment-summary.md"
# Deployment Summary
**Project**: LLM Inference Stack
**Version**: $(cat "$ROOT_DIR/VERSION")
**Date**: $(date)

## Package Contents
- **docs/enterprise/**: Operational guides and security docs.
- **commercial/packages/**: Commercial offer definitions.
- **commercial/checklists/**: Step-by-step delivery guides.
- **commercial/templates/**: Legal and compliance templates.

## Targeted Environment
- **Mode**: ${DEPLOYMENT_MODE:-appliance}
- **Status**: $(docker compose ps | grep -q "Up" && echo "Ready" || echo "Infrastructure Down")

## Next Steps
1. Review \`customer-readiness.md\`.
2. Follow \`docs/enterprise/ONBOARDING_GUIDE.md\`.
3. Complete installation using \`commercial/checklists/INSTALLATION.md\`.
4. Execute \`acceptance-report.md\`.
EOF

echo "Enterprise Pack generated at $OUTPUT_DIR"
ls -lh "$OUTPUT_DIR"
