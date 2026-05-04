#!/bin/bash
# scripts/test-llama-cpp-params.sh

echo "Testing llama.cpp behavior with max_tokens vs n_predict..."

# Direct call to data-plane (llama.cpp)
# We'll use max_tokens in the payload
echo "Data-plane with max_tokens=3..."
curl -s -X POST http://localhost:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma",
    "messages": [{"role": "user", "content": "Diga Olá!"}],
    "max_tokens": 3
  }' | python3 -c "import sys, json; data=json.load(sys.stdin); print('Tokens:', data['usage']['completion_tokens'], 'Reason:', data['choices'][0]['finish_reason'])"

echo "Data-plane with n_predict=3..."
curl -s -X POST http://localhost:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma",
    "messages": [{"role": "user", "content": "Diga Olá!"}],
    "n_predict": 3
  }' | python3 -c "import sys, json; data=json.load(sys.stdin); print('Tokens:', data['usage']['completion_tokens'], 'Reason:', data['choices'][0]['finish_reason'])"
