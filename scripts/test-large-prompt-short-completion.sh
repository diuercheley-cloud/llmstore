#!/bin/bash
# scripts/test-large-prompt-short-completion.sh

set -e

BASE_URL="${BASE_URL:-http://localhost:18080}"
API_KEY="${API_KEY:-sk-local-mU7fr1Yqna-jdwA624WTvGk40yj9abAa}"

# Generate a large prompt (~2000 tokens)
LARGE_PROMPT=$(python3 -c "print('Este é um teste de prompt longo. ' * 500)")

echo "Testing large prompt with short completion request..."
RESPONSE=$(curl -s -X POST "$BASE_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d "{
    \"model\": \"gemma\",
    \"messages\": [{\"role\": \"user\", \"content\": \"$LARGE_PROMPT\n\nResponda apenas com a palavra OK.\"}],
    \"temperature\": 0.0
  }")

echo "Response usage: $(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['usage'])")"
echo "Response content: $(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['choices'][0]['message']['content'])")"
