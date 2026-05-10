#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:?set ADMIN_TOKEN in environment or env file}"

create_or_update_plan() {
  local payload=$1
  local code=$(echo "$payload" | python3 -c "import sys, json; print(json.load(sys.stdin)['code'])")
  
  echo "Processing plan: ${code}..."
  
  local response=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/admin/billing/plans" \
    -H "X-Admin-Token: ${ADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$payload")
    
  if [ "$response" == "201" ] || [ "$response" == "200" ]; then
    echo "Plan ${code} created successfully."
  elif [ "$response" == "409" ]; then
    echo "Plan ${code} already exists, updating..."
    # Get ID for PATCH
    local plan_id=$(curl -s "${BASE_URL}/admin/billing/plans" -H "X-Admin-Token: ${ADMIN_TOKEN}" | python3 -c "import sys, json; print([p['id'] for p in json.load(sys.stdin) if p['code'] == '${code}'][0])")
    curl -s -X PATCH "${BASE_URL}/admin/billing/plans/${plan_id}" \
      -H "X-Admin-Token: ${ADMIN_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "$payload" > /dev/null
    echo "Plan ${code} updated successfully."
  else
    echo "Error processing plan ${code}: HTTP ${response}"
    exit 1
  fi
}

# 1. FREE PLAN
FREE_PLAN='{
  "code": "free",
  "name": "Free",
  "description": "Starter plan for sandbox usage. Local/Manual billing.",
  "rate_limit_per_minute": 10,
  "daily_token_quota": 50000,
  "weekly_token_quota": 250000,
  "monthly_token_quota": 50000,
  "requests_per_day": 100,
  "max_context_tokens": 4096,
  "max_output_tokens": 1024,
  "allow_streaming": true,
  "rag_enabled": false,
  "rag_max_documents": 0,
  "rag_max_storage_mb": 0,
  "tts_enabled": false,
  "tts_chars_per_month": 0,
  "embeddings_enabled": false,
  "embeddings_requests_per_month": 0,
  "responses_enabled": true,
  "tools_enabled": false,
  "export_enabled": false,
  "support_level": "Community",
  "allowed_models": ["gemma-2b"]
}'

# 2. BASIC PLAN
BASIC_PLAN='{
  "code": "basic",
  "name": "Basic",
  "description": "Production starter for small projects. Local/Manual billing.",
  "rate_limit_per_minute": 30,
  "daily_token_quota": 75000,
  "weekly_token_quota": 350000,
  "monthly_token_quota": 500000,
  "requests_per_day": 1000,
  "max_context_tokens": 8192,
  "max_output_tokens": 2048,
  "allow_streaming": true,
  "rag_enabled": true,
  "rag_max_documents": 5,
  "rag_max_storage_mb": 100,
  "tts_enabled": true,
  "tts_chars_per_month": 10000,
  "embeddings_enabled": true,
  "embeddings_requests_per_month": 1000,
  "responses_enabled": true,
  "tools_enabled": false,
  "export_enabled": false,
  "support_level": "Email",
  "allowed_models": ["gemma-2b", "gemma-7b"]
}'

# 3. PRO PLAN
PRO_PLAN='{
  "code": "pro",
  "name": "Pro",
  "description": "Growth plan with higher limits. Local/Manual billing.",
  "rate_limit_per_minute": 60,
  "daily_token_quota": 300000,
  "weekly_token_quota": 1500000,
  "monthly_token_quota": 5000000,
  "requests_per_day": 5000,
  "max_context_tokens": 16384,
  "max_output_tokens": 4096,
  "allow_streaming": true,
  "rag_enabled": true,
  "rag_max_documents": 50,
  "rag_max_storage_mb": 1024,
  "tts_enabled": true,
  "tts_chars_per_month": 100000,
  "embeddings_enabled": true,
  "embeddings_requests_per_month": 10000,
  "responses_enabled": true,
  "tools_enabled": false,
  "export_enabled": true,
  "support_level": "Priority Email"
}'

# 4. ENTERPRISE LOCAL PLAN
ENTERPRISE_PLAN='{
  "code": "enterprise-local",
  "name": "Enterprise Local",
  "description": "Dedicated high-volume local rollout. Local/Manual billing.",
  "rate_limit_per_minute": 300,
  "daily_token_quota": 1500000,
  "weekly_token_quota": 7000000,
  "monthly_token_quota": 50000000,
  "requests_per_day": 999999,
  "max_context_tokens": 131072,
  "max_output_tokens": 32768,
  "allow_streaming": true,
  "rag_enabled": true,
  "rag_max_documents": 1000,
  "rag_max_storage_mb": 10240,
  "tts_enabled": true,
  "tts_chars_per_month": 1000000,
  "embeddings_enabled": true,
  "embeddings_requests_per_month": 100000,
  "responses_enabled": true,
  "tools_enabled": false,
  "export_enabled": true,
  "support_level": "24/7 Dedicated"
}'

create_or_update_plan "$FREE_PLAN"
create_or_update_plan "$BASIC_PLAN"
create_or_update_plan "$PRO_PLAN"
create_or_update_plan "$ENTERPRISE_PLAN"

echo "All commercial plans seeded successfully."
