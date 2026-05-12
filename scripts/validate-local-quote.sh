#!/usr/bin/env bash
# scripts/validate-local-quote.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "Starting Local Quote Validation..."

# 1. Gera orçamento md/json
echo "Testing quote generation..."
"${SCRIPT_DIR}/generate-local-quote.sh" --company-name "Test Company" --plan Pro --rag --support-hours 10 --discount-percent 10 > /tmp/quote_gen.log

JSON_PATH=$(grep "JSON:" /tmp/quote_gen.log | cut -d' ' -f2)
MD_PATH=$(grep "Markdown:" /tmp/quote_gen.log | cut -d' ' -f2)

if [[ -f "${JSON_PATH}" ]] && [[ -f "${MD_PATH}" ]]; then
  echo "✅ Quote files generated successfully."
else
  echo "❌ Quote files NOT generated."
  exit 1
fi

# 2. Cálculo básico correto
echo "Validating calculations..."
SETUP_VAL=$(jq -r '.totals.setup' "${JSON_PATH}")
RECURRING_VAL=$(jq -r '.totals.recurring' "${JSON_PATH}")
FINAL_VAL=$(jq -r '.totals.first_month_final' "${JSON_PATH}")

# Pro plan setup is 5000, RAG is 2500 -> 7500
if [[ "${SETUP_VAL}" -eq 7500 ]]; then
  echo "✅ Setup calculation correct (7500)."
else
  echo "❌ Setup calculation INCORRECT: ${SETUP_VAL}"
  exit 1
fi

# Pro plan monthly is 2000, 10 hours support @ 250 -> 4500
if [[ "${RECURRING_VAL}" -eq 4500 ]]; then
  echo "✅ Recurring calculation correct (4500)."
else
  echo "❌ Recurring calculation INCORRECT: ${RECURRING_VAL}"
  exit 1
fi

# Total first month: 7500 + 4500 = 12000. 10% discount -> 10800
if [[ "${FINAL_VAL}" -eq 10800 ]]; then
  echo "✅ Discount applied correctly (10800)."
else
  echo "❌ Discount calculation INCORRECT: ${FINAL_VAL}"
  exit 1
fi

# 3. Não contém secrets
echo "Checking for secrets..."
if grep -rE "API_KEY|SECRET|PASSWORD" "${ROOT_DIR}/artifacts/quotes" > /dev/null 2>&1; then
  echo "❌ Secrets found in artifacts!"
  exit 1
else
  echo "✅ No secrets found in artifacts."
fi

# 4. artifacts/quotes não entra no Git
echo "Checking .gitignore for artifacts/quotes..."
if grep -q "^artifacts/" "${ROOT_DIR}/.gitignore" 2>/dev/null; then
  echo "✅ artifacts/ is ignored."
  # Add specifically artifacts/quotes for clarity if desired, but artifacts/ is enough
else
  echo "⚠️ artifacts/ is NOT ignored in .gitignore. Adding it..."
  echo "artifacts/" >> "${ROOT_DIR}/.gitignore"
fi

echo "Local Quote Validation PASSED."
