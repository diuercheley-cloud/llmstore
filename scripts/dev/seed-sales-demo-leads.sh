#!/usr/bin/env bash

set -e

# Load common environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"
source "${SCRIPT_DIR}/../dev/common.sh"

init_stack_env

BASE_URL="$(default_base_url)"
ADMIN_TOKEN="${ADMIN_TOKEN:-super-secret-admin-token}"

echo "Seeding Sales Demo Leads..."

create_lead() {
  local name="$1"
  local contact="$2"
  local email="$3"
  local segment="$4"
  local value="$5"
  local status="$6"
  
  curl -fsS -X POST "${BASE_URL}/admin/sales/leads" \
    -H "X-Admin-Token: ${ADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
      \"company_name\": \"${name}\",
      \"contact_name\": \"${contact}\",
      \"contact_email\": \"${email}\",
      \"segment\": \"${segment}\",
      \"estimated_value\": ${value},
      \"status\": \"${status}\",
      \"source\": \"Demo Pack\",
      \"is_demo\": true,
      \"notes\": \"Lead gerado automaticamente para demonstração comercial.\"
    }" > /dev/null
}

# Clínica Horizonte Demo
create_lead "Clínica Horizonte Demo" "Dr. Ricardo Silva" "ricardo@clinica-horizonte.example.local" "Health" 15000 "new"

# Jurídico Atlas Demo
create_lead "Jurídico Atlas Demo" "Dra. Helena Costa" "helena@atlas-juridico.demo.local" "Legal" 25000 "contacted"

# Suporte Orion Demo
create_lead "Suporte Orion Demo" "Marcos Oliveira" "marcos@orion-suporte.example.local" "Tech" 8000 "demo_scheduled"

# Escola Prisma Demo
create_lead "Escola Prisma Demo" "Ana Beatriz" "ana@escola-prisma.demo.local" "Education" 12000 "proposal_sent"

# Provedor API Nebula Demo
create_lead "Provedor API Nebula Demo" "Eng. Fabio" "fabio@nebula-api.example.local" "Infrastructure" 45000 "negotiation"

echo "Sales Demo Leads seeded successfully."
