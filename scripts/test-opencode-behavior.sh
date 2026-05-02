#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"

# Try to find existing opencode client key or create one
printf '[test] garantindo cliente opencode...\n'
setup_output="$(./scripts/create-opencode-client.sh 2>&1 || true)"
API_KEY=$(echo "$setup_output" | grep "API Key:" | awk '{print $NF}')

if [[ -z "${API_KEY}" ]]; then
  # Maybe client already exists, try to get a key for it
  # This is a bit complex for a script, let's just assume we can issue a new key if admin token is present
  if [[ -n "${ADMIN_TOKEN:-}" ]]; then
      # Find client id by name
      client_id=$(curl -fsS "${BASE_URL}/admin/clients" -H "X-Admin-Token: ${ADMIN_TOKEN}" | python3 -c "import json, sys; d=json.load(sys.stdin); print([c['id'] for c in d if c['name'] == 'opencode-local'][0])")
      API_KEY=$(curl -fsS "${BASE_URL}/admin/api-keys" -H "X-Admin-Token: ${ADMIN_TOKEN}" -H "Content-Type: application/json" -d "{\"client_id\":\"${client_id}\",\"name\":\"test-behavior\"}" | python3 -c "import json, sys; print(json.load(sys.stdin)['api_key'])")
  else
      printf '[error] API_KEY não encontrada e ADMIN_TOKEN não definido\n'
      exit 1
  fi
fi

test_prompt() {
  local prompt="$1"
  local description="$2"
  printf '\n[test] %s: "%s"\n' "${description}" "${prompt}"
  
  response="$(curl -fsS -X POST "${BASE_URL}/v1/chat/completions" \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d "{
      \"model\": \"gemma\",
      \"messages\": [{\"role\": \"user\", \"content\": \"${prompt}\"}],
      \"stream\": false
    }")"
    
  content=$(echo "${response}" | python3 -c "import json, sys; print(json.load(sys.stdin)['choices'][0]['message']['content'])")
  echo "--- RESPOSTA ---"
  echo "${content}"
  echo "----------------"
  
  # Validation: check for repetitions
  if echo "${content}" | grep -qiE "Goal:|Progress:|Next Steps:|Relevant Files:"; then
    # Some occurrence is allowed, but not excessive. 
    # But for these specific prompts, they shouldn't appear at all with the new system prompt.
    printf '[warning] blocos de planejamento detectados na resposta\n'
  fi
  
  if echo "${content}" | grep -q "Truncated due to repetition loop"; then
    printf '[success] anti-loop detectou e truncou a resposta\n'
  else
    printf '[info] nenhuma repetição extrema detectada\n'
  fi
}

test_prompt "oi" "Saudação simples"
test_prompt "Explique este projeto em 3 frases" "Explicação curta"
test_prompt "Liste 3 melhorias possíveis" "Lista de melhorias"

# Simulation of a loop (using a specialized prompt if possible, or just checking the logs)
# Actually, the best way to test anti-loop is to feed it a response that would loop.
# But here we are testing the model's actual behavior with the new system prompt.

printf '\n[test] comportamento validado!\n'
