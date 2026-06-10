#!/usr/bin/env bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"

echo "Validating Client Proposal Local..."

# Ensure we are in the root directory for relative paths in the generator
cd "$ROOT_DIR"

# 1. Generate proposal with dummy data
echo "Generating dummy proposal..."
OUTPUT_DIR="artifacts/test-proposals"
rm -rf "$OUTPUT_DIR"
./scripts/dev/generate-client-proposal.sh \
    --company-name "Validation Corp" \
    --contact-name "Validator" \
    --segment "Compliance" \
    --plan "Enterprise" \
    --setup-fee 9999 \
    --output-dir "$OUTPUT_DIR"

PROPOSAL_PATH=$(find "$OUTPUT_DIR" -name "*.md" | head -n 1)

if [[ -z "$PROPOSAL_PATH" ]]; then
    echo "Error: Proposal MD not generated"
    exit 1
fi

# 2. Check for secrets
echo "Checking for secrets in generated proposal..."
# Basic check for typical secret patterns or the specific admin token used in common.sh
if grep -q "super-secret-admin-token" "$PROPOSAL_PATH"; then
    echo "Error: Found secret in proposal!"
    exit 1
fi

# 3. Check for mandatory mentions
echo "Checking mandatory content..."
grep -q "Local AI Appliance" "$PROPOSAL_PATH" || { echo "Error: Missing mention of Local AI Appliance"; exit 1; }
grep -q "não inclui processamento real de pagamentos (PSP/PIX)" "$PROPOSAL_PATH" || { echo "Error: Missing mention of PSP/PIX disclaimer"; exit 1; }
grep -q "BRL" "$PROPOSAL_PATH" || { echo "Error: Missing BRL currency"; exit 1; }

# 4. Validate metadata
METADATA_PATH=$(find "$OUTPUT_DIR" -name "proposal-metadata.json" | head -n 1)
if [[ ! -f "$METADATA_PATH" ]]; then
    echo "Error: Metadata JSON not generated"
    exit 1
fi

SETUP_FEE_VAL=$(jq -r '.setup_fee' "$METADATA_PATH")
if [[ "$SETUP_FEE_VAL" != "9999" ]]; then
    echo "Error: Metadata setup_fee mismatch (got $SETUP_FEE_VAL)"
    exit 1
fi

# 5. Check if PDF format skip/run works (not failing script if tool missing)
echo "Checking PDF format option..."
./scripts/dev/generate-client-proposal.sh --company-name "PDF Test" --format pdf --output-dir "$OUTPUT_DIR" > /dev/null

# 6. Verify it's not versioned
echo "Verifying it's not tracked by git..."
if git ls-files --error-unmatch "$PROPOSAL_PATH" 2>/dev/null; then
    echo "Error: Generated proposal is tracked by git!"
    exit 1
fi

echo "Client Proposal validation PASSED."
