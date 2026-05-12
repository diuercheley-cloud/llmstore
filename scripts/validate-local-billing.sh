#!/usr/bin/env bash
set -euo pipefail

# Scripts dir relative to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib/validation-logging.sh"

init_stack_env

# Settings
CONTROL_PLANE_URL="${CONTROL_PLANE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:-change-this-admin-token}"

log_section "Local Billing Mode (Manual) Validation"

log_step "Creating test client"
CLIENT_NAME="Local Billing Test Client $RANDOM"
CLIENT_RESPONSE=$(curl_base_url "$CONTROL_PLANE_URL/admin/clients" -s -X POST \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "X-Admin-Token: $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"$CLIENT_NAME\", \"rate_limit_per_minute\": 100, \"daily_token_quota\": 100000, \"weekly_token_quota\": 500000, \"monthly_token_quota\": 2000000, \"max_output_tokens\": 1000}")
log_curl_mode "$CONTROL_PLANE_URL/admin/clients"

CLIENT_ID=$(echo "$CLIENT_RESPONSE" | grep -o '"id":"[^"]*' | cut -d'"' -f4 | head -n 1)

if [ -z "$CLIENT_ID" ]; then
    log_error "Failed to create client! Response: $CLIENT_RESPONSE"
    exit 1
fi
log_ok "Client created with ID: $CLIENT_ID"

log_step "Generating API key for client"
API_KEY_RESPONSE=$(curl_base_url "$CONTROL_PLANE_URL/admin/api-keys" -s -X POST \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "X-Admin-Token: $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"client_id": "'"$CLIENT_ID"'", "name": "billing-test-key"}')
log_curl_mode "$CONTROL_PLANE_URL/admin/api-keys"

API_KEY=$(echo "$API_KEY_RESPONSE" | grep -o '"api_key":"[^"]*' | cut -d'"' -f4)
if [ -z "$API_KEY" ]; then
    log_error "Failed to create API key! Response: $API_KEY_RESPONSE"
    exit 1
fi
log_ok "API Key created"

log_step "Associating paid plan"
# First, fetch plans
PLANS_RESPONSE=$(curl_base_url "$CONTROL_PLANE_URL/admin/billing/plans" -s -X GET \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "X-Admin-Token: $ADMIN_TOKEN")
log_curl_mode "$CONTROL_PLANE_URL/admin/billing/plans"

PLAN_ID=$(echo "$PLANS_RESPONSE" | grep -o '"id":"[^"]*' | cut -d'"' -f4 | head -n 2 | tail -n 1) # get second plan (likely a paid one)

if [ -z "$PLAN_ID" ]; then
    log_error "Failed to fetch plans!"
    exit 1
fi

curl_base_url "$CONTROL_PLANE_URL/admin/clients/$CLIENT_ID/billing-plan" -s -X PATCH \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "X-Admin-Token: $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"billing_plan_id": "'"$PLAN_ID"'"}' > /dev/null
log_curl_mode "$CONTROL_PLANE_URL/admin/clients/$CLIENT_ID/billing-plan"
log_ok "Plan associated"

log_step "Testing API access (should work)"
HTTP_STATUS=$(curl_base_url "$CONTROL_PLANE_URL/portal/me" -s -o /dev/null -w "%{http_code}" -X GET \
    -H "Authorization: Bearer $API_KEY")
log_curl_mode "$CONTROL_PLANE_URL/portal/me"

if [ "$HTTP_STATUS" != "200" ]; then
    log_error "Expected 200 OK, got $HTTP_STATUS"
    exit 1
fi
log_ok "API access OK."

log_step "Generating manual invoice"
INVOICE_RESPONSE=$(curl_base_url "$CONTROL_PLANE_URL/admin/billing/invoices/generate" -s -X POST \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "X-Admin-Token: $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"client_id": "'"$CLIENT_ID"'", "due_in_days": 5, "payment_method": "manual"}')
log_curl_mode "$CONTROL_PLANE_URL/admin/billing/invoices/generate"

INVOICE_ID=$(echo "$INVOICE_RESPONSE" | grep -o '"id":"[^"]*' | cut -d'"' -f4 | head -n 1)
if [ -z "$INVOICE_ID" ]; then
    log_error "Failed to generate invoice! Response: $INVOICE_RESPONSE"
    exit 1
fi
log_ok "Generated Invoice ID: $INVOICE_ID"

log_step "Verifying invoice is pending"
STATUS=$(echo "$INVOICE_RESPONSE" | grep -o '"status":"[^"]*' | cut -d'"' -f4 | head -n 1)
if [ "$STATUS" != "pending" ]; then
    log_error "Invoice is not pending: $STATUS"
    exit 1
fi
log_ok "Invoice is pending."

log_step "Running billing cycle"
curl_base_url "$CONTROL_PLANE_URL/admin/billing/run-cycle" -s -X POST \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "X-Admin-Token: $ADMIN_TOKEN" > /dev/null
log_curl_mode "$CONTROL_PLANE_URL/admin/billing/run-cycle"
log_ok "Billing cycle executed"

log_step "Simulating invoice overdue with suspension"
curl_base_url "$CONTROL_PLANE_URL/admin/billing/invoices/$INVOICE_ID/mark-overdue?simulate_suspension=true" -s -X PATCH \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "X-Admin-Token: $ADMIN_TOKEN" > /dev/null
log_curl_mode "$CONTROL_PLANE_URL/admin/billing/invoices/$INVOICE_ID/mark-overdue?simulate_suspension=true"
log_ok "Overdue simulation executed"

log_step "Verifying client is suspended"
HTTP_STATUS=$(curl_base_url "$CONTROL_PLANE_URL/portal/me" -s -o /dev/null -w "%{http_code}" -X GET \
    -H "Authorization: Bearer $API_KEY")
log_curl_mode "$CONTROL_PLANE_URL/portal/me"

if [ "$HTTP_STATUS" != "402" ]; then
    log_error "Expected 402 Payment Required for suspended client, got $HTTP_STATUS"
    exit 1
fi
log_ok "Client correctly suspended (402 Payment Required)."

log_step "Marking invoice as paid manually"
curl_base_url "$CONTROL_PLANE_URL/admin/billing/invoices/$INVOICE_ID/mark-paid" -s -X PATCH \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "X-Admin-Token: $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"payment_method": "manual", "payment_reference": "manual-payment-test"}' > /dev/null
log_curl_mode "$CONTROL_PLANE_URL/admin/billing/invoices/$INVOICE_ID/mark-paid"
log_ok "Invoice marked as paid"

log_step "Verifying API access restored"
HTTP_STATUS=$(curl_base_url "$CONTROL_PLANE_URL/portal/me" -s -o /dev/null -w "%{http_code}" -X GET \
    -H "Authorization: Bearer $API_KEY")
log_curl_mode "$CONTROL_PLANE_URL/portal/me"

if [ "$HTTP_STATUS" != "200" ]; then
    log_error "Expected 200 OK after payment, got $HTTP_STATUS"
    exit 1
fi
log_ok "API access successfully restored."

log_step "Cleaning up"
curl_base_url "$CONTROL_PLANE_URL/admin/clients/$CLIENT_ID" -s -X DELETE \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "X-Admin-Token: $ADMIN_TOKEN" > /dev/null || true
log_ok "Cleaned up"

log_ok "Validation completed successfully!"
